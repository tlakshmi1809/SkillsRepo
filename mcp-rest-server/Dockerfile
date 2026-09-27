FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set default environment variables
ENV API_BASE_URL="https://httpbin.org"
ENV LOG_LEVEL="INFO"

# Run FastMCP server over stdio transport
CMD ["python3", "server.py"]
