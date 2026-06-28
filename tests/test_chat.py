import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.chat.prompt_builder import PromptBuilder
from app.chat.service import ChatService
from app.config import settings
from app.main import app
from app.memory.mem0_store import Mem0MemoryStore, memory_from_result
from app.memory.models import Memory
from app.memory.service import MemoryService, create_memory_store
from app.schemas.chat import ChatMessage, ChatRequest

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)


class FakeLLMProvider:
    model = "test-model"

    def __init__(self):
        self.messages = []

    async def stream_chat(self, messages):
        self.messages = messages
        yield "안녕하세요. "
        yield "저는 Moly예요."


class FakeMemoryStore:
    """새 포트(get_all/add) 스텁 — DB 없이."""

    def __init__(self, memories=None):
        self._memories = memories or []
        self.add_calls = []

    async def get_all(self, user_id, limit):
        return self._memories

    async def add(self, user_id, messages):
        self.add_calls.append((user_id, messages))


class FakeMem0Client:
    def __init__(self, get_all_result=None):
        self._get_all_result = get_all_result or {"results": []}
        self.add_args = []

    async def get_all(self, filters, top_k):
        return self._get_all_result

    async def add(self, memory, user_id):
        self.add_args.append((memory, user_id))


async def collect_stream(stream):
    return [event async for event in stream]


async def post_chat(body_dict) -> tuple[dict[str, str], str]:
    body = json.dumps(body_dict).encode()
    messages = [{"type": "http.request", "body": body, "more_body": False}]
    sent = []

    async def receive():
        if messages:
            return messages.pop(0)
        await asyncio.Event().wait()

    async def send(message):
        sent.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/chat",
            "raw_path": b"/chat",
            "query_string": b"",
            "headers": [
                (b"host", b"testserver"),
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
            "client": ("127.0.0.1", 123),
            "server": ("testserver", 80),
        },
        receive,
        send,
    )

    response_start = next(m for m in sent if m["type"] == "http.response.start")
    headers = {k.decode().lower(): v.decode() for k, v in response_start["headers"]}
    response_body = b"".join(
        m.get("body", b"") for m in sent if m["type"] == "http.response.body"
    ).decode()
    return headers, response_body


class ChatSseTests(unittest.TestCase):
    def test_chat_streams_sse_and_forwards_memory(self):
        fake_llm = FakeLLMProvider()
        with patch("app.api.chat.create_llm_provider", return_value=fake_llm):
            headers, body = asyncio.run(
                post_chat(
                    {
                        "user_id": "user-1",
                        "messages": [{"role": "user", "content": "hello"}],
                        "memory": "- likes coffee",
                    }
                )
            )

        self.assertEqual(headers["content-type"], "text/event-stream")
        self.assertIn('data: {"type":"delta","delta":"안녕하세요. "}\n\n', body)
        self.assertIn(
            'data: {"type":"done","reply":"안녕하세요. 저는 Moly예요.","usage":{"model":"test-model"}}\n\n',
            body,
        )
        # 요청의 memory가 system 블록으로 들어갔는지 (mem0 호출 없이)
        roles = [m["role"] for m in fake_llm.messages]
        self.assertEqual(roles, ["system", "system", "user"])
        self.assertIn("likes coffee", fake_llm.messages[1]["content"])


class ChatServiceTests(unittest.TestCase):
    def test_uses_request_memory_no_mem0_call(self):
        fake_llm = FakeLLMProvider()
        service = ChatService(
            llm_provider=fake_llm,
            prompt_builder=PromptBuilder(system_prompt="You are Moly."),
        )
        request = ChatRequest(
            user_id="user-1",
            messages=[ChatMessage(role="user", content="hi")],
            memory="- from Busan",
        )
        asyncio.run(collect_stream(service.stream_chat(request)))

        self.assertEqual(
            fake_llm.messages[1],
            {"role": "system", "content": "Relevant user memory:\n- from Busan"},
        )

    def test_empty_memory_omits_memory_block(self):
        fake_llm = FakeLLMProvider()
        service = ChatService(
            llm_provider=fake_llm,
            prompt_builder=PromptBuilder(system_prompt="You are Moly."),
        )
        request = ChatRequest(
            user_id="user-1", messages=[ChatMessage(role="user", content="hi")]
        )
        asyncio.run(collect_stream(service.stream_chat(request)))

        # memory 비면 system 1개 + user 1개뿐
        self.assertEqual([m["role"] for m in fake_llm.messages], ["system", "user"])


class MemoryServiceTests(unittest.TestCase):
    def test_requires_store(self):
        with self.assertRaisesRegex(ValueError, "MemoryService requires a MemoryStore"):
            MemoryService()

    def test_create_memory_store_requires_supabase(self):
        with (
            patch.object(settings, "supabase_db_connection_string", ""),
            self.assertRaisesRegex(ValueError, "SUPABASE_DB_CONNECTION_STRING"),
        ):
            create_memory_store()

    def test_load_for_session_renders_active_and_passive(self):
        store = FakeMemoryStore(
            memories=[
                Memory(content="took an exam", created_at=NOW - timedelta(days=1)),
                Memory(content="from Busan", created_at=NOW - timedelta(days=40)),
            ]
        )
        service = MemoryService(store=store)

        text = asyncio.run(service.load_for_session("user-1", now=NOW))

        self.assertIn("[Recent", text)
        self.assertIn("- yesterday: took an exam", text)
        self.assertIn("[Background", text)
        self.assertIn("- from Busan", text)

    def test_commit_session_calls_store_add(self):
        store = FakeMemoryStore()
        service = MemoryService(store=store)
        msgs = [ChatMessage(role="user", content="hi")]

        asyncio.run(service.commit_session("user-1", msgs))

        self.assertEqual(store.add_calls, [("user-1", msgs)])


class Mem0StoreTests(unittest.TestCase):
    def test_get_all_maps_timestamps_and_id(self):
        client = FakeMem0Client(
            get_all_result={
                "results": [
                    {
                        "id": "m1",
                        "memory": "likes coffee",
                        "created_at": "2026-06-20T00:00:00+00:00",
                        "updated_at": "2026-06-24T00:00:00+00:00",
                    }
                ]
            }
        )
        memories = asyncio.run(Mem0MemoryStore(client).get_all("user-1", limit=500))

        self.assertEqual(len(memories), 1)
        m = memories[0]
        self.assertEqual(m.content, "likes coffee")
        self.assertEqual(m.id, "m1")
        self.assertEqual(m.updated_at, datetime(2026, 6, 24, tzinfo=timezone.utc))

    def test_add_passes_conversation(self):
        client = FakeMem0Client()
        asyncio.run(
            Mem0MemoryStore(client).add(
                "user-1", [ChatMessage(role="user", content="hello")]
            )
        )
        self.assertEqual(
            client.add_args, [([{"role": "user", "content": "hello"}], "user-1")]
        )

    def test_memory_from_result_accepts_plain_and_dict(self):
        self.assertEqual(memory_from_result("hi"), Memory(content="hi"))
        self.assertEqual(
            memory_from_result({"memory": "hello", "score": 0.9}),
            Memory(content="hello", score=0.9),
        )


class PromptBuilderTests(unittest.TestCase):
    def test_build_returns_system_memory_and_messages(self):
        builder = PromptBuilder(system_prompt="You are Moly.")
        messages = builder.build(
            messages=[ChatMessage(role="user", content="hello")],
            memory="likes coffee",
        )
        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "You are Moly."},
                {"role": "system", "content": "Relevant user memory:\nlikes coffee"},
                {"role": "user", "content": "hello"},
            ],
        )


class AnthropicConvoTests(unittest.TestCase):
    """_split_system_and_convo: system 분리 + 첫 메시지 user 보장(선발화/재연결 대비)."""

    def setUp(self):
        from app.llm.anthropic import _split_system_and_convo
        self.split = _split_system_and_convo

    def test_splits_system_and_keeps_convo(self):
        system, convo = self.split([
            {"role": "system", "content": "You are Moly."},
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ])
        self.assertEqual(system, "You are Moly.")
        self.assertEqual(convo, [{"role": "user", "content": "a"},
                                 {"role": "assistant", "content": "b"}])

    def test_drops_leading_assistant(self):
        # 선발화로 history가 assistant 인사로 시작 → Anthropic 거부 방지 위해 절단.
        _, convo = self.split([
            {"role": "assistant", "content": "hey there"},
            {"role": "user", "content": "hi"},
        ])
        self.assertEqual(convo, [{"role": "user", "content": "hi"}])

    def test_all_assistant_yields_empty_convo(self):
        _, convo = self.split([{"role": "assistant", "content": "x"}])
        self.assertEqual(convo, [])


class PromptMemoryHeaderSyncTests(unittest.TestCase):
    """시스템 프롬프트 [What You Remember]가 참조하는 ACTIVE/PASSIVE 헤더가 renderer 상수와
    정확히 일치하는지 — 한쪽만 바뀌면 프롬프트의 메모리 사용 지침이 조용히 깨지므로 불변식으로 고정."""

    def test_prompt_references_renderer_headers(self):
        from app.chat.prompts import DEFAULT_SYSTEM_PROMPT
        from app.memory.renderer import _ACTIVE_HEADER, _PASSIVE_HEADER

        self.assertIn(_ACTIVE_HEADER, DEFAULT_SYSTEM_PROMPT)
        self.assertIn(_PASSIVE_HEADER, DEFAULT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
