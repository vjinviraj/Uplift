import json
from dataclasses import dataclass
from typing import TypeVar

from groq import Groq
from openai import OpenAI
from pydantic import BaseModel

from apps.api.config import get_setting


ModelT = TypeVar("ModelT", bound=BaseModel)


def _make_groq_strict_schema(schema: dict) -> dict:
    """Adapt a Pydantic JSON schema to strict-mode requirements."""

    if "$defs" in schema:
        for definition in schema["$defs"].values():
            _make_groq_strict_schema(definition)
    if "properties" in schema:
        for property_schema in schema["properties"].values():
            _make_groq_strict_schema(property_schema)
        schema["required"] = list(schema["properties"].keys())
        schema["additionalProperties"] = False
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            _make_groq_strict_schema(option)
    if "items" in schema and isinstance(schema["items"], dict):
        _make_groq_strict_schema(schema["items"])
    return schema


@dataclass
class _Provider:
    name: str
    model: str
    client: object


class LLMClient:
    """Structured LLM boundary with Groq first and OpenRouter fallback."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        explicit_configuration = api_key is not None or model is not None
        groq_key = api_key or get_setting("GROQ_API_KEY")
        groq_model = model or get_setting("GROQ_MODEL")
        openrouter_key = get_setting("OPENROUTER_API_KEY")
        openrouter_model = get_setting("OPENROUTER_MODEL")

        self.providers: list[_Provider] = []
        if groq_key and groq_model:
            self.providers.append(_Provider("Groq", groq_model, Groq(api_key=groq_key)))
        if not explicit_configuration and openrouter_key and openrouter_model:
            self.providers.append(
                _Provider(
                    "OpenRouter",
                    openrouter_model,
                    OpenAI(
                        api_key=openrouter_key,
                        base_url="https://openrouter.ai/api/v1",
                    ),
                )
            )

        if not self.providers:
            if not groq_key and not openrouter_key:
                raise ValueError("GROQ_API_KEY or OPENROUTER_API_KEY is not configured")
            raise ValueError("A model must be configured for each available LLM provider")

        # Kept for compatibility with callers/tests that replace the primary client.
        self.client = self.providers[0].client
        self.api_key = groq_key
        self.model = self.providers[0].model

    def generate_structured(
        self, *, system_prompt: str, user_prompt: str, response_model: type[ModelT]
    ) -> ModelT:
        schema = _make_groq_strict_schema(response_model.model_json_schema())
        failures: list[str] = []

        for index, provider in enumerate(self.providers):
            client = self.client if index == 0 else provider.client
            try:
                response = client.chat.completions.create(
                    model=provider.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": response_model.__name__,
                            "strict": True,
                            "schema": schema,
                        },
                    },
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("empty structured response")
                try:
                    payload = json.loads(content)
                except json.JSONDecodeError as exc:
                    raise ValueError("invalid JSON") from exc
                try:
                    return response_model.model_validate(payload)
                except Exception as exc:
                    raise ValueError("schema-invalid response") from exc
            except Exception as exc:
                failures.append(f"{provider.name}: {exc}")

        if len(failures) == 1:
            raise ValueError(failures[0].split(": ", 1)[1])
        raise ValueError("All configured LLM providers failed: " + " | ".join(failures))
