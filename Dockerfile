FROM python:3.12-slim

WORKDIR /app

COPY app.py index.html calendar_data.json ./

EXPOSE 5001

CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "5001"]
