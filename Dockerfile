FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr for
# real-time log visibility on Railway.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer between builds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the data directory (holding the bundled questions DB and the
# generated app-state DB) exists and is writable.
RUN mkdir -p /app/data

CMD ["python", "bot.py"]
