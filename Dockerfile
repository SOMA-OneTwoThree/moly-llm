FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# 컨테이너(항상 켜짐). SSE 스트리밍 OK.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
