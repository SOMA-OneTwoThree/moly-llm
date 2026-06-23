import asyncio
import json
import unittest
from unittest.mock import patch

from app.chat.service import ChatService
from app.chat.prompt_builder import PromptBuilder
from app.config import settings
from app.main import app
from app.memory.mem0_store import Mem0MemoryStore, memory_from_result
from app.memory.models import Memory
from app.memory.service import MemoryService, create_memory_store
from app.schemas.chat import ChatMessage, ChatRequest


class FakeLLMProvider:
    model = "test-model"

    def __init__(self):
        self.messages = []

    async def stream_chat(self, messages):
        self.messages = messages
        yield "안녕하세요. "
        yield "저는 Moly예요."


class FakeMemoryStore:
    def __init__(self):
        self.search_calls = 0

    async def search(self, user_id, query, limit):
        self.search_calls += 1
        return [Memory(content="User likes concise answers.", score=0.9)]

    async def save_conversation(self, user_id, messages, assistant_reply):
        return None


class FakeMemoryService:
    def __init__(self):
        self.remember_calls = []

    async def search(self, user_id, query):
        return [Memory(content="User likes concise answers.")]

    async def remember_from_conversation(self, user_id, messages, assistant_reply):
        self.remember_calls.append((user_id, messages, assistant_reply))
        return None


class FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


class FakeMem0Client:
    def __init__(self):
        self.search_args = None
        self.add_args = []

    async def search(self, query, filters, top_k):
        self.search_args = (query, filters, top_k)
        return [{"memory": "User likes concise answers.", "score": 0.9}]

    async def add(self, memory, user_id):
        self.add_args.append((memory, user_id))


async def collect_stream(stream):
    return [event async for event in stream]


async def post_chat() -> tuple[dict[str, str], str]:
    body = json.dumps(
        {
            "user_id": "user-1",
            "messages": [{"role": "user", "content": "hello"}],
        }
    ).encode()
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

    response_start = next(
        message for message in sent if message["type"] == "http.response.start"
    )
    headers = {
        key.decode().lower(): value.decode()
        for key, value in response_start["headers"]
    }
    response_body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    ).decode()
    return headers, response_body


class ChatSseTests(unittest.TestCase):
    def test_chat_streams_llm_sse_events(self):
        fake_llm_provider = FakeLLMProvider()

        with (
            patch("app.api.chat.create_llm_provider", return_value=fake_llm_provider),
            patch("app.api.chat.get_memory_service", return_value=FakeMemoryService()),
        ):
            headers, body = asyncio.run(post_chat())

        self.assertEqual(headers["content-type"], "text/event-stream")
        self.assertIn('data: {"type":"delta","delta":"안녕하세요. "}\n\n', body)
        self.assertIn('data: {"type":"delta","delta":"저는 Moly예요."}\n\n', body)
        self.assertIn(
            'data: {"type":"done","reply":"안녕하세요. 저는 Moly예요.","usage":{"model":"test-model"}}\n\n',
            body,
        )
        self.assertEqual(fake_llm_provider.messages[0]["role"], "system")
        self.assertEqual(fake_llm_provider.messages[1]["role"], "system")
        self.assertEqual(fake_llm_provider.messages[2]["role"], "user")

    def test_chat_service_adds_memory_to_prompt(self):
        fake_llm_provider = FakeLLMProvider()
        service = ChatService(
            llm_provider=fake_llm_provider,
            memory_service=FakeMemoryService(),
            prompt_builder=PromptBuilder(system_prompt="You are Molly."),
        )
        request = ChatRequest(
            user_id="user-1",
            messages=[ChatMessage(role="user", content="hello")],
        )

        asyncio.run(collect_stream(service.stream_chat(request)))

        self.assertEqual(
            fake_llm_provider.messages[1],
            {
                "role": "system",
                "content": "Relevant user memory:\n- User likes concise answers.",
            },
        )
        self.assertEqual(fake_llm_provider.messages[2]["role"], "user")

    def test_chat_service_saves_memory_every_n_user_turns(self):
        fake_llm_provider = FakeLLMProvider()
        fake_memory_service = FakeMemoryService()
        background_tasks = FakeBackgroundTasks()
        service = ChatService(
            llm_provider=fake_llm_provider,
            memory_service=fake_memory_service,
            prompt_builder=PromptBuilder(system_prompt="You are Molly."),
            memory_save_every_n_turns=2,
        )
        request = ChatRequest(
            user_id="user-1",
            messages=[
                ChatMessage(role="user", content="hello"),
                ChatMessage(role="assistant", content="hi"),
                ChatMessage(role="user", content="remember this"),
            ],
        )

        asyncio.run(collect_stream(service.stream_chat(request, background_tasks)))

        self.assertEqual(len(background_tasks.tasks), 1)
        _, _, kwargs = background_tasks.tasks[0]
        self.assertEqual(kwargs["user_id"], "user-1")
        self.assertEqual(
            kwargs["messages"],
            [
                ChatMessage(role="user", content="hello"),
                ChatMessage(role="assistant", content="hi"),
                ChatMessage(role="user", content="remember this"),
            ],
        )
        self.assertEqual(kwargs["assistant_reply"], "안녕하세요. 저는 Moly예요.")

    def test_chat_service_skips_memory_save_between_intervals(self):
        fake_llm_provider = FakeLLMProvider()
        fake_memory_service = FakeMemoryService()
        background_tasks = FakeBackgroundTasks()
        service = ChatService(
            llm_provider=fake_llm_provider,
            memory_service=fake_memory_service,
            prompt_builder=PromptBuilder(system_prompt="You are Molly."),
            memory_save_every_n_turns=2,
        )
        request = ChatRequest(
            user_id="user-1",
            messages=[ChatMessage(role="user", content="hello")],
        )

        asyncio.run(collect_stream(service.stream_chat(request, background_tasks)))

        self.assertEqual(background_tasks.tasks, [])

    def test_chat_service_saves_only_recent_n_user_turns(self):
        fake_llm_provider = FakeLLMProvider()
        background_tasks = FakeBackgroundTasks()
        service = ChatService(
            llm_provider=fake_llm_provider,
            memory_service=FakeMemoryService(),
            prompt_builder=PromptBuilder(system_prompt="You are Molly."),
            memory_save_every_n_turns=2,
        )
        request = ChatRequest(
            user_id="user-1",
            messages=[
                ChatMessage(role="user", content="old user"),
                ChatMessage(role="assistant", content="old assistant"),
                ChatMessage(role="user", content="new user"),
                ChatMessage(role="assistant", content="new assistant"),
                ChatMessage(role="user", content="latest user"),
                ChatMessage(role="assistant", content="latest assistant"),
                ChatMessage(role="user", content="final user"),
            ],
        )

        asyncio.run(collect_stream(service.stream_chat(request, background_tasks)))

        _, _, kwargs = background_tasks.tasks[0]
        self.assertEqual(
            kwargs["messages"],
            [
                ChatMessage(role="user", content="latest user"),
                ChatMessage(role="assistant", content="latest assistant"),
                ChatMessage(role="user", content="final user"),
            ],
        )


class MemoryServiceTests(unittest.TestCase):
    def test_memory_service_requires_store(self):
        with self.assertRaisesRegex(ValueError, "MemoryService requires a MemoryStore"):
            MemoryService()

    def test_create_memory_store_requires_supabase(self):
        with (
            patch.object(settings, "supabase_db_connection_string", ""),
            self.assertRaisesRegex(ValueError, "SUPABASE_DB_CONNECTION_STRING"),
        ):
            create_memory_store()

    def test_search_uses_cache(self):
        store = FakeMemoryStore()
        service = MemoryService(store=store, top_k=5, cache_ttl_seconds=60)

        first = asyncio.run(service.search("user-1", "hello"))
        second = asyncio.run(service.search("user-1", "hello"))

        self.assertEqual(first, second)
        self.assertEqual(store.search_calls, 1)

    def test_mem0_store_searches_memories(self):
        client = FakeMem0Client()
        store = Mem0MemoryStore(client)

        memories = asyncio.run(store.search("user-1", "hello", limit=5))

        self.assertEqual(
            memories,
            [Memory(content="User likes concise answers.", score=0.9)],
        )
        self.assertEqual(client.search_args, ("hello", {"user_id": "user-1"}, 5))

    def test_mem0_store_saves_conversation_once(self):
        client = FakeMem0Client()
        store = Mem0MemoryStore(client)

        asyncio.run(
            store.save_conversation(
                "user-1",
                [ChatMessage(role="user", content="hello")],
                "hi",
            )
        )

        self.assertEqual(
            client.add_args,
            [
                (
                    [
                        {"role": "user", "content": "hello"},
                        {"role": "assistant", "content": "hi"},
                    ],
                    "user-1",
                )
            ],
        )

    def test_memory_from_result_accepts_mem0_shapes(self):
        self.assertEqual(
            memory_from_result({"memory": "hello", "score": 0.9}),
            Memory(content="hello", score=0.9),
        )


class PromptBuilderTests(unittest.TestCase):
    def test_build_returns_system_memory_and_recent_messages(self):
        builder = PromptBuilder(system_prompt="You are Molly.")

        messages = builder.build(
            messages=[
                ChatMessage(role="user", content="hello"),
                ChatMessage(role="assistant", content="hi"),
            ],
            memory="User likes concise answers.",
        )

        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "You are Molly."},
                {
                    "role": "system",
                    "content": "Relevant user memory:\nUser likes concise answers.",
                },
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
        )
