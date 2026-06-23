# moly-llm

moly 음성 대화의 LLM 레이어. 텍스트 대화 → 스트리밍 응답.
페르소나 + 장기기억(Mem0) + 대화 히스토리를 합쳐 Groq LLM 응답을 SSE로 흘려보낸다.

## API Contract

Request:

```json
{
  "user_id": "string",
  "messages": [
    { "role": "user", "content": "string" },
    { "role": "assistant", "content": "string" },
  ]
}
```

Response:

```txt
data: {"type":"delta","delta":"..."}
data: {"type":"delta","delta":"..."}
data: {"type":"done","reply":"...","usage":{...}}
```

Error response:

```txt
data: {"type":"error","code":"...","message":"..."}
```

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic
- Mem0 SDK
- Supabase Postgres/pgvector via vecs for memory storage

## Folder Structure

```
app/
  main.py
  config.py
  api/
    chat.py
    health.py
  schemas/
    chat.py
    sse.py
  chat/
    service.py
    prompt_builder.py
    prompts.py
  llm/
    base.py
    groq.py
    factory.py
  memory/
    service.py
    mem0_client.py
    mem0_store.py
    cache.py
    models.py
    formatter.py
```

## Run With Docker

Build the image:

```bash
docker build -t moly-llm:local .
```

Run the container:

```bash
docker run -d \
  --name moly-llm \
  -p 8000:8000 \
  --env-file .env \
  moly-llm:local
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

View logs:

```bash
docker logs -f moly-llm
```

Stop and remove the container:

```bash
docker stop moly-llm
docker rm moly-llm
```
