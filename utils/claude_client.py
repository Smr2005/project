import os
import json
import re
import logging
import httpx
from utils.config import Config

ANTHROPIC_API_KEY = Config.CLAUDE_API_KEY

logger = logging.getLogger(__name__)

# Default Anthropic public API endpoint (adjust if you use Bedrock or different proxy)
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "x-api-key": ANTHROPIC_API_KEY,
    "Content-Type": "application/json",
    # Required header for Messages API
    "anthropic-version": "2023-06-01",
}

def _extract_json_from_text(text: str):
    """Try extracting a JSON object/array from a text blob."""
    if not text:
        raise ValueError("Empty text")

    # Balanced-brace extraction first
    start = None
    depth = 0
    for i, ch in enumerate(text):
        if ch == "{" and start is None:
            start = i
            depth = 1
        elif ch == "{":
            depth += 1
        elif ch == "}" and start is not None:
            depth -= 1
            if depth == 0:
                candidate = text[start:i+1]
                try:
                    return json.loads(candidate)
                except Exception:
                    break

    # Try array
    m = re.search(r'(\[.*\])', text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # Loose fallback for {...}
    m2 = re.search(r'(\{.*\})', text, flags=re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass

    # Last resort parse whole text
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Could not parse JSON from text: {e}")

def call_claude_raw(prompt: str, model: str = "claude-3-5-sonnet-20240620", max_tokens: int = 800):
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not set in environment."}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(ANTHROPIC_URL, headers=HEADERS, json=payload)
            r.raise_for_status()
            data = r.json()
            # Messages API shape: content is a list of blocks; pick first text block
            if isinstance(data, dict) and isinstance(data.get("content"), list):
                for block in data["content"]:
                    if isinstance(block, dict) and block.get("type") == "text" and "text" in block:
                        return {"text": block["text"], "raw": data}
            # Fallbacks
            if isinstance(data, dict) and isinstance(data.get("content"), list) and data["content"]:
                c0 = data["content"][0]
                if isinstance(c0, dict) and "text" in c0:
                    return {"text": c0["text"], "raw": data}
            if isinstance(data, dict) and isinstance(data.get("completion"), str):
                return {"text": data["completion"], "raw": data}
            return {"text": json.dumps(data), "raw": data}
    except Exception as e:
        logger.exception("Error calling Claude: %s", e)
        return {"error": str(e)}

def call_claude_json(prompt: str, model: str = "claude-3-5-sonnet-20240620", max_tokens: int = 1200):
    raw = call_claude_raw(prompt, model=model, max_tokens=max_tokens)
    if "error" in raw:
        return {"error": raw["error"], "raw": raw.get("raw")}
    text = raw.get("text", "")
    try:
        parsed = _extract_json_from_text(text)
        return parsed
    except Exception as e:
        logger.warning("Failed to parse JSON from Claude output: %s", e)
        return {"error": "Failed to parse JSON", "raw_text": text}
