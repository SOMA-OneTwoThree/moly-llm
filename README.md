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

- FastAPI
- Pydantic
- Groq Llama-3.3-70b
- Mem0 SDK
- Supabase Postgres/pgvector for memory storage
- SSE for streaming `/chat`

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
    formatter.py
  observability/
    logger.py
    metrics.py
```

## Run

```bash
uv sync
uv uvicorn app.main:app --reload --port 8000
curl localhost:8000/health
```
