FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make sure uvicorn is installed and in PATH
RUN pip install --no-cache-dir "uvicorn[standard]>=0.22.0"

# More explicit command (specifying the full path)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]