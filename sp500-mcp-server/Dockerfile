FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source (no .venv, .git, .env)
COPY server.py .
COPY src/ src/

# Config
ENV PORT=8001

EXPOSE 8001

CMD ["python", "server.py"]
