import json
import re

import anthropic

from . import config

_client = anthropic.Anthropic()


def ask(system: str, user: str, max_tokens: int = 4000) -> str:
    msg = _client.messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def ask_json(system: str, user: str, max_tokens: int = 4000):
    raw = ask(system + "\nReply with valid JSON only, no prose.", user, max_tokens)
    m = re.search(r"[\[{].*[\]}]", raw, re.S)
    return json.loads(m.group(0)) if m else []
