import os
import sys
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logging strictly to sys.stderr so stdio transport (JSON-RPC) is not corrupted
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)

logger = logging.getLogger("mcp-rest-server")

class Settings(BaseSettings):
    """Configuration settings for the FastMCP REST API Server."""
    
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://httpbin.org")
    API_USER_TOKEN: str = os.getenv("API_USER_TOKEN", "")
    AUTH_SCHEME: str = os.getenv("AUTH_SCHEME", "Bearer")  # Bearer, Basic, Header, or Query
    AUTH_HEADER_NAME: str = os.getenv("AUTH_HEADER_NAME", "Authorization")
    AUTH_QUERY_PARAM_NAME: str = os.getenv("AUTH_QUERY_PARAM_NAME", "api_key")
    
    HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "30.0"))
    MAX_RESPONSE_CHAR_LIMIT: int = int(os.getenv("MAX_RESPONSE_CHAR_LIMIT", "10000"))
    
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv("RETRY_BACKOFF_FACTOR", "0.5"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
