import json
import os
import re
from typing import Any

import requests


def get_provider():
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider()
    if os.getenv("SERVER_URL") and os.getenv("SERVER_TOKEN"):
        return GraniteProvider()
    raise RuntimeError(
        "No LLM provider configured. Set OPENAI_API_KEY or SERVER_URL+SERVER_TOKEN."
    )


class OpenAIProvider:
    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        if msg.tool_calls:
            return {
                "type": "tool_calls",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in msg.tool_calls
                ],
            }

        return {"type": "text", "content": msg.content or ""}


class GraniteProvider:
    def __init__(self):
        self.server_url = os.getenv("SERVER_URL", "").rstrip("/")
        self.server_token = os.getenv("SERVER_TOKEN", "")

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        if tools:
            tool_descriptions = self._format_tools_for_prompt(tools)
            system_msg = next(
                (m for m in messages if m["role"] == "system"), None
            )
            tool_instruction = (
                "\n\nDu hast folgende Werkzeuge zur Verfügung. "
                "Um ein Werkzeug zu nutzen, antworte NUR mit einem JSON-Block in diesem Format:\n"
                '<tool_call>{"name": "werkzeug_name", "arguments": {"param": "wert"}}</tool_call>\n'
                "Du kannst mehrere Werkzeuge nacheinander aufrufen.\n"
                "Wenn du KEIN Werkzeug brauchst, antworte direkt.\n\n"
                f"Verfügbare Werkzeuge:\n{tool_descriptions}"
            )
            if system_msg:
                system_msg["content"] += tool_instruction
            else:
                messages = [{"role": "system", "content": tool_instruction}] + messages

        payload = {"messages": messages}
        r = requests.post(
            f"{self.server_url}/api/llm/chat",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.server_token}",
            },
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        text = data.get("response", "")

        tool_calls = self._parse_tool_calls(text)
        if tool_calls:
            return {"type": "tool_calls", "tool_calls": tool_calls}

        return {"type": "text", "content": text}

    def _format_tools_for_prompt(self, tools: list[dict]) -> str:
        lines = []
        for tool in tools:
            fn = tool["function"]
            params = json.dumps(fn.get("parameters", {}), ensure_ascii=False)
            lines.append(f"- {fn['name']}: {fn['description']}\n  Parameter: {params}")
        return "\n".join(lines)

    def _parse_tool_calls(self, text: str) -> list[dict]:
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)
        calls = []
        for i, match in enumerate(matches):
            try:
                parsed = json.loads(match.strip())
                calls.append({
                    "id": f"granite_{i}",
                    "name": parsed["name"],
                    "arguments": parsed.get("arguments", {}),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return calls
