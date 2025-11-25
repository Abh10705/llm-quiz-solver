FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 10000

# Start command
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
