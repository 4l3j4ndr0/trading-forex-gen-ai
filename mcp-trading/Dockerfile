FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY src/ src/

RUN mkdir -p data

ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

CMD ["python", "server.py"]
