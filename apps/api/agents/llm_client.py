import json
import os
from typing import TypeVar

from groq import Groq
from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


def _make_groq_strict_schema(schema: dict) -> dict:
    """Adapt a Pydantic JSON schema to Groq strict-mode requirements."""

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


class LLMClient:
    """Boundary around the Groq LLM client.

    The LLM can propose/evaluate.
    Deterministic backend code remains authoritative for
    pricing, policy, authorization, and payment.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")

        if not self.model:
            raise ValueError("GROQ_MODEL is not configured")

        self.client = Groq(api_key=self.api_key)

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        """Request a strict structured response and validate it locally."""

        schema = _make_groq_strict_schema(response_model.model_json_schema())

        response = self.client.chat.completions.create(
            model=self.model,
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
            raise ValueError("Groq returned an empty structured response")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Groq returned invalid JSON") from exc

        try:
            return response_model.model_validate(payload)
        except Exception as exc:
            raise ValueError("Groq returned a schema-invalid response") from exc
