FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    IMAGE_SPLITTER_MAX_UPLOAD_BYTES=12582912 \
    IMAGE_SPLITTER_MAX_REQUEST_BYTES=18874368 \
    IMAGE_SPLITTER_MAX_STORED_DOWNLOADS=24

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8008

CMD ["python", "web_app.py", "--host", "0.0.0.0", "--port", "8008"]
