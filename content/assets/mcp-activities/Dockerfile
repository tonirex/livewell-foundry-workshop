# LiveWell activities MCP server + profile API (Lab 3). Synthetic workshop tool, no authentication.
# Built remotely in ACR by `azd deploy mcp-activities`; the azd prepackage hook copies
# content/data/activities.json and citizens.json next to server.py first (single source of truth).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=80

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py activities.json citizens.json ./

EXPOSE 80
CMD ["python", "server.py"]
