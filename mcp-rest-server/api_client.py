import json
import base64
from typing import Any, Dict, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, retry_if_exception_type
from config import settings, logger

def _is_transient_error(exception: Exception) -> bool:
    """Identify transient network or server errors eligible for retry."""
    if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in {502, 503, 504, 429}
    return False

class RESTApiClient:
    """Production-grade Async HTTP REST client for making credential-authenticated API calls."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        auth_scheme: Optional[str] = None,
        header_name: Optional[str] = None,
        query_param_name: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.API_BASE_URL).rstrip("/")
        self.token = token or settings.API_USER_TOKEN
        self.auth_scheme = (auth_scheme or settings.AUTH_SCHEME).lower()
        self.header_name = header_name or settings.AUTH_HEADER_NAME
        self.query_param_name = query_param_name or settings.AUTH_QUERY_PARAM_NAME
        self.timeout = timeout or settings.HTTP_TIMEOUT

    def _build_auth(self, headers: Dict[str, str], params: Dict[str, Any]) -> None:
        """Inject authentication credentials into headers or query parameters."""
        if not self.token:
            return

        if self.auth_scheme == "bearer":
            headers[self.header_name] = f"Bearer {self.token}"
        elif self.auth_scheme == "basic":
            if ":" in self.token:
                encoded = base64.b64encode(self.token.encode("utf-8")).decode("utf-8")
                headers[self.header_name] = f"Basic {encoded}"
            else:
                headers[self.header_name] = f"Basic {self.token}"
        elif self.auth_scheme == "query":
            params[self.query_param_name] = self.token
        else:
            # Custom header or raw key injection (e.g., X-API-Key)
            headers[self.header_name] = self.token

    def _format_response(self, response: httpx.Response) -> str:
        """Format and sanitize HTTP response payload for MCP tool output."""
        try:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                payload = response.json()
                formatted = json.dumps(payload, indent=2)
            else:
                formatted = response.text

            if len(formatted) > settings.MAX_RESPONSE_CHAR_LIMIT:
                formatted = (
                    formatted[:settings.MAX_RESPONSE_CHAR_LIMIT]
                    + f"\n\n... [Output truncated at {settings.MAX_RESPONSE_CHAR_LIMIT} characters]"
                )

            return formatted
        except Exception as err:
            logger.warning(f"Failed to parse response JSON: {err}")
            return f"Raw Response ({response.status_code}): {response.text[:1000]}"

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> str:
        """Execute HTTP request with retry logic and credential authentication."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        headers = {
            "User-Agent": "FastMCP-REST-Client/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if custom_headers:
            headers.update(custom_headers)

        queryParams = dict(params or {})
        self._build_auth(headers, queryParams)

        @retry(
            stop=stop_after_attempt(settings.MAX_RETRIES),
            wait=wait_exponential(multiplier=settings.RETRY_BACKOFF_FACTOR, min=0.5, max=5.0),
            retry=retry_if_exception(_is_transient_error),
            reraise=True
        )
        async def _execute():
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                logger.debug(f"Sending {method.upper()} request to {url}")
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=queryParams,
                    json=json_data
                )
                response.raise_for_status()
                return response

        try:
            res = await _execute()
            return self._format_response(res)
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP {exc.response.status_code} Error calling {url}: {exc.response.text}")
            return f"HTTP Error {exc.response.status_code}: {exc.response.text}"
        except httpx.RequestError as exc:
            logger.error(f"Network Connection Error calling {url}: {str(exc)}")
            return f"Network Error: Unable to connect to {url}. Details: {str(exc)}"
        except Exception as exc:
            logger.error(f"Unexpected error executing {method} {url}: {str(exc)}")
            return f"Execution Error: {str(exc)}"

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        return await self.request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> str:
        return await self.request("POST", endpoint, json_data=json_data)

    async def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> str:
        return await self.request("PUT", endpoint, json_data=json_data)

    async def patch(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> str:
        return await self.request("PATCH", endpoint, json_data=json_data)

    async def delete(self, endpoint: str) -> str:
        return await self.request("DELETE", endpoint)
