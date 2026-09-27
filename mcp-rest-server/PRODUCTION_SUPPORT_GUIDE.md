# Production Support & Operational Runbook: FastMCP REST API Server

**Target Audience**: L2/L3 Production Support, SRE, and DevOps Engineering Teams  
**Document Owner**: AI Platform & Integration Operations  
**Version**: 1.1.0  
**Last Updated**: 2026-09-27  

---

## 1. System Overview & Component Topology

The **FastMCP REST API Integration Server** acts as an operational bridge between AI Agent runtimes (e.g., Antigravity, Claude Desktop, custom MCP orchestrators) and backend HTTPS REST services. It also includes a standalone **Swagger UI & OpenAPI Specification service (`swagger_server.py`)** for interactive endpoint testing and API schema validation.

```
+---------------------+           +------------------------+           +-----------------------+
|  MCP Agent Runtime  |  stdio /  |  FastMCP Server        |  HTTPS    |  Target REST API      |
|  (Antigravity Client)| --------> |  (Python fastmcp)      | --------> |  (api.yourdomain.com) |
|                     | JSON-RPC  |  - Auth Injector       |  TLS 1.3  |                       |
|                     | <-------- |  - Tenacity Retries    | <-------- |                       |
+---------------------+           +------------------------+           +-----------------------+
                                              |
                                              +-----> [Swagger UI Service (FastAPI / uvicorn)]
                                              |       http://localhost:8000/docs
                                              v
                                  +------------------------+
                                  |  Cloud Logging / Syslog|
                                  |  (Stderr Logs Only)    |
                                  +------------------------+
```

---

## 2. Configuration & Secrets Reference

All server operations are governed by environment variables loaded at startup via `.env` or process environment:

| Environment Variable | Required | Default Value | Description / Operational Impact |
| :--- | :--- | :--- | :--- |
| `API_BASE_URL` | **Yes** | `https://httpbin.org` | Target REST API root URL. Must be HTTPS in prod. |
| `API_USER_TOKEN` | **Yes** | `""` | User credential / API key. Keep secret! |
| `AUTH_SCHEME` | No | `"Bearer"` | Auth type: `Bearer`, `Basic`, `Header`, or `Query`. |
| `AUTH_HEADER_NAME` | No | `"Authorization"` | Custom header name when `AUTH_SCHEME=Header`. |
| `AUTH_QUERY_PARAM_NAME`| No | `"api_key"` | Parameter name when `AUTH_SCHEME=Query`. |
| `HTTP_TIMEOUT` | No | `30.0` | HTTP request timeout budget (seconds). |
| `MAX_RETRIES` | No | `3` | Retry attempts for transient 5xx/network errors. |
| `MAX_RESPONSE_CHAR_LIMIT`| No | `10000` | Max response characters before payload truncation. |
| `LOG_LEVEL` | No | `"INFO"` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

> [!CAUTION]
> **Secrets Security**: `API_USER_TOKEN` must never be hardcoded into `server.py` or committed to source repositories. Always inject via Secret Manager or process environment variables.

---

## 3. Operational Playbooks & Troubleshooting

### Incident 1: HTTP 401 Unauthorized / 403 Forbidden
- **Symptom**: MCP tools return `HTTP Error 401: Unauthorized` or `HTTP Error 403: Forbidden`.
- **Root Cause**: Expired `API_USER_TOKEN`, invalid `AUTH_SCHEME`, or IP firewall blocking the outgoing request.
- **Remediation Steps**:
  1. Test credential validity manually via `curl` or Swagger UI (`http://localhost:8000/docs`):
     ```bash
     curl -v -H "Authorization: Bearer <API_USER_TOKEN>" https://api.yourdomain.com/v1/resources
     ```
  2. Verify `AUTH_SCHEME` setting in `.env`.
  3. Rotate `API_USER_TOKEN` in Secret Manager / `.env` and restart the FastMCP process.

---

### Incident 2: HTTP 502 / 503 / 504 Downstream Outages & Retries
- **Symptom**: MCP tool response includes `Network Error` or `HTTP Error 503`.
- **Root Cause**: Target REST API is experiencing an outage or throttling rate limits.
- **Behavior**: The server automatically retries transient status codes (`502`, `503`, `504`, `429`) up to `MAX_RETRIES=3` using exponential backoff ($0.5\text{s} \rightarrow 1.0\text{s} \rightarrow 2.0\text{s}$).
- **Remediation Steps**:
  1. Check target REST API status page / health endpoint:
     ```bash
     curl -i https://api.yourdomain.com/v1/health
     ```
  2. If target API is rate-limiting (`429`), temporarily increase `RETRY_BACKOFF_FACTOR` in `config.py`.

---

### Incident 3: Stdio Transport Protocol Corruption
- **Symptom**: MCP Client reports `JSON-RPC parse error` or fails to discover tools.
- **Root Cause**: `print()` statements or non-MCP log output were written to `sys.stdout`.
- **Architecture Requirement**: Stdio stdout is **strictly reserved** for JSON-RPC MCP messages.
- **Remediation**:
  1. Ensure all custom logs use `logging.getLogger()` which writes strictly to `sys.stderr`.
  2. Verify no plain `print()` statements exist in codebase.

---

### Incident 4: Payload Truncation Notice
- **Symptom**: MCP tool returns data ending with `... [Output truncated at 10000 characters]`.
- **Root Cause**: REST API endpoint returned a payload exceeding `MAX_RESPONSE_CHAR_LIMIT`.
- **Remediation**:
  1. This is an intentional safeguard to prevent LLM context window depletion.
  2. If additional details are required, instruct the agent to use paginated parameters (`limit=5` or `page=2`).
  3. Alternatively, increase `MAX_RESPONSE_CHAR_LIMIT=20000` in `.env` if model token budget permits.

---

## 4. Deployment & Maintenance Procedures

### 4.1 Local / VM Deployment Verification
1. Run automated unit test suite (All 15 tests must pass):
   ```bash
   cd mcp-rest-server
   PYTHONPATH=. .venv/bin/pytest tests/ -v
   ```
2. Launch Swagger UI Server & test `/docs`:
   ```bash
   .venv/bin/python3 swagger_server.py
   ```
   Open `http://localhost:8000/docs` in your browser.

### 4.2 Docker Deployment Verification
1. Build & execute container test:
   ```bash
   ./deploy.sh
   ```
2. Check running container health:
   ```bash
   docker ps --filter "name=mcp-rest-server"
   ```

### 4.3 Google Cloud Run Operations
1. View deployment status:
   ```bash
   gcloud run services describe mcp-rest-server --region=us-central1
   ```
2. Stream live container logs:
   ```bash
   gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=mcp-rest-server"
   ```

---

## 5. Escalation Contacts & SLA

| Severity Level | Response Time SLA | Escalation Target |
| :--- | :--- | :--- |
| **P1 - Critical** (All MCP tools failing / Authentication outage) | $< 15$ minutes | AI Platform On-Call (`#ai-platform-oncall`) |
| **P2 - High** (Downstream target API elevated latency $> 5\text{s}$) | $< 1$ hour | Backend API Integration Team |
| **P3 - Low** (Minor formatting / non-critical tool update) | $< 24$ hours | Production Support Ticket Queue |
