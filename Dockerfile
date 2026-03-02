FROM python:3.12-slim

WORKDIR /app

COPY app.py index.html ./

EXPOSE 8080

CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8080"]
