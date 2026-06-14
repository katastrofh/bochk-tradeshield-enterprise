"""Real local LLM client for TradeShield V8.

Default provider: Ollama on the host machine.
The Docker backend reaches it through host.docker.internal:11434.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class LLMUnavailable(RuntimeError):
    pass


def ollama_chat(messages: list[dict], temperature: float = 0.2) -> dict:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 900,
        },
    }

    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise LLMUnavailable(f"Ollama unavailable at {base_url}: {exc}") from exc

    content = data.get("message", {}).get("content", "").strip()
    if not content:
        raise LLMUnavailable("Ollama returned an empty response.")

    return {
        "provider": "ollama",
        "model": model,
        "content": content,
        "raw": {
            "done": data.get("done"),
            "total_duration": data.get("total_duration"),
            "eval_count": data.get("eval_count"),
        },
    }


def build_trade_finance_system_prompt() -> str:
    return """You are TradeShield Copilot, a BOCHK trade-finance assistant.

Rules:
- You are decision support only. Never claim final lending authority.
- Use only the supplied case context.
- If evidence is missing, say what is missing.
- Be specific: refer to supplier, buyer, amount, route, risk score, and controls.
- Separate facts, risk interpretation, recommended actions, and banker questions.
- Do not invent documents, approvals, repayment history, sanctions results, or BOCHK internal policy.
- Keep the answer banker-grade, concise, and auditable.
"""


def build_case_prompt(case_pack: dict, question: str) -> str:
    return f"""Case context JSON:
{json.dumps(case_pack, indent=2, default=str)}

User question:
{question}

Return:
1. Direct answer
2. Evidence used
3. Risk interpretation
4. Recommended banker action
5. Questions or conditions for the SME
6. Human-review caveat
"""
