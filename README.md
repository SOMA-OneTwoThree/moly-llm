# moly-llm — Molly의 뇌 (LLM 서비스)

Molly 음성 대화의 **LLM 레이어**. 텍스트 대화 → 스트리밍 응답.
페르소나 + 장기기억(Mem0) + 대화 히스토리를 합쳐 Groq LLM 응답을 SSE로 흘려보낸다.

> 프로덕션 3레포 중 **② LLM**. 전체 구조는 `moly-pipeline-test/docs/production-architecture.md` 참고.

## 역할
- 입력: `POST /chat {messages:[{role,content}], user_id?}` (OpenAI/Anthropic 컨벤션, 하위호환 `{text}`)
- 출력: SSE — `data:{delta}` × N → `data:{done, usage}`
- system(페르소나 + Mem0 기억)은 **서버 소유**. 클라(게이트웨이)는 user/assistant 턴만 전송.

## 스택
- **Python FastAPI** (컨테이너, 항상 켜짐 — 콜드스타트 회피, SSE 스트리밍)
- LLM: **Groq Llama-3.3-70b** (provider 추상화: openai SDK base_url 교체로 OpenAI/DeepSeek 등 호환)
- 메모리: **Mem0 managed** — search 캐시(첫 턴만 네트워크) + 응답 후 async add

## 구조
```
app/
├── main.py        # FastAPI: /health, /chat(SSE)
├── llm/           # provider 추상화 (openai_compat: groq/openai/deepseek)
├── chat/          # service: 페르소나 + 프롬프트 조립 + 기억 주입
└── memory/        # mem0: search 캐시(getCached/refresh) + async add
```

## 로컬 실행
```bash
cp .env.example .env          # GROQ_API_KEY, MEM0_API_KEY 주입
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl localhost:8000/health
```

## env
| 키 | 설명 |
|---|---|
| `GROQ_API_KEY` | Groq |
| `LLM_PROVIDER` / `LLM_MODEL` | `groq` / `llama-3.3-70b-versatile` |
| `MEM0_API_KEY` | Mem0 managed (장기기억) |
| `SYSTEM_PROMPT` | 비우면 코드 기본 페르소나(alien-Molly) |

## 배포
Dockerfile → **Railway/Fly (항상 켜짐, min 1 인스턴스)**. 콜드스타트 금지.

## 포팅 메모
`moly-pipeline-test`의 `src/lib/llm`·`src/lib/chat/service.ts`·`src/lib/memory/mem0.ts`(Node) 를
Python으로 옮긴다. 핵심: search 캐시는 인스턴스 RAM(컨테이너라 OK), add는 BackgroundTasks.
