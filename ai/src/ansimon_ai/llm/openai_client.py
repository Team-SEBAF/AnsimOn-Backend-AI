import json
import os
from typing import Optional

from .base import LLMClient

class OpenAILLMClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        try:
            from dotenv import load_dotenv
        except ModuleNotFoundError:
            load_dotenv = None

        if load_dotenv is not None:
            load_dotenv()

        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise ValueError("OPENAI_API_KEY is required.")

        from openai import OpenAI

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.client = OpenAI(
            api_key=resolved_api_key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )

    def generate(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned empty content.")

        json.loads(content)
        return content