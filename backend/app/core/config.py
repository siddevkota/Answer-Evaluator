import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    def __init__(self) -> None:
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.OPENAI_EMBEDDING_MODEL = os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        # NEW: reference textbook path
        self.REFERENCE_TEXTBOOK_PATH = os.getenv(
            "REFERENCE_TEXTBOOK_PATH", "data/Introduction-to-Engineering-Thermodynamics-1662608237.pdf"
        )
        self.REFERENCE_TEXTBOOK_NAME = os.getenv(
            "REFERENCE_TEXTBOOK_NAME", "Introduction to Engineering Thermodynamics"
        )

        if not self.OPENAI_API_KEY:
            print(
                "[WARN] OPENAI_API_KEY is not set. "
                "LLM features will not work until you export it."
            )

@lru_cache
def get_settings() -> Settings:
    return Settings()
