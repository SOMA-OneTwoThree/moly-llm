import asyncio
import json
import unittest
from unittest.mock import patch

from app.main import app


class FakeLLMProvider:
    model = "test-model"

    async def stream_chat(self, messages):
        yield "안녕하세요. "
        yield "저는 Moly예요."


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
        with patch("app.api.chat.create_llm_provider", return_value=FakeLLMProvider()):
            headers, body = asyncio.run(post_chat())

        self.assertEqual(headers["content-type"], "text/event-stream")
        self.assertIn('data: {"type":"delta","delta":"안녕하세요. "}\n\n', body)
        self.assertIn('data: {"type":"delta","delta":"저는 Moly예요."}\n\n', body)
        self.assertIn(
            'data: {"type":"done","reply":"안녕하세요. 저는 Moly예요.","usage":{"model":"test-model"}}\n\n',
            body,
        )
