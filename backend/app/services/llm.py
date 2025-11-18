from typing import List
from openai import OpenAI
from ..core.config import get_settings

settings = get_settings()

# Initialize OpenAI client (v1.0+)
client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

class LLMError(Exception):
    pass

def _ensure_key():
    if not settings.OPENAI_API_KEY or client is None:
        raise LLMError("OPENAI_API_KEY is missing. Set it in environment variables.")

def chat_completion(system_prompt: str, user_prompt: str, max_tokens: int = 512) -> str:
    _ensure_key()
    try:
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        # Minimal guardrail: don't leak internals, just raise clean error
        raise LLMError(f"LLM call failed: {e}")

def embed_texts(texts: List[str]) -> List[List[float]]:
    _ensure_key()
    try:
        resp = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in resp.data]
    except Exception as e:
        raise LLMError(f"Embedding failed: {e}")
