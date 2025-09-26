import os
import json
import httpx
from ..settings import settings

ANTHROPIC_API_KEY = settings.claude_api_key
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "x-api-key": ANTHROPIC_API_KEY,
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
}

async def call_claude_json(prompt: str, model: str = "claude-3-haiku-20240307", max_tokens: int = 1000) -> dict:
    if not ANTHROPIC_API_KEY:
        return {"error": "Claude API key not set"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(ANTHROPIC_URL, headers=HEADERS, json=payload)
            r.raise_for_status()
            data = r.json()
            if isinstance(data.get("content"), list) and data["content"]:
                text = data["content"][0].get("text", "")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"error": "Failed to parse JSON", "raw": text}
            return {"error": "Unexpected response", "raw": data}
        except Exception as e:
            return {"error": str(e)}
