import json

import pytest

from apps.api.agents.llm_client import LLMClient
from apps.api.agents.schemas import MerchantAgentProposal


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"choices": [FakeChoice(self.content)]})()


class FakeGroq:
    def __init__(self, content):
        self.completions = FakeCompletions(content)
        self.chat = type("Chat", (), {"completions": self.completions})()


def make_client(content):
    client = LLMClient(api_key="test-key", model="openai/gpt-oss-20b")
    fake = FakeGroq(content)
    client.client = fake
    return client, fake


def test_generate_structured_validates_model_response():
    content = json.dumps({"product_id": "GAME-001", "upsell": None})
    client, _ = make_client(content)

    result = client.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=MerchantAgentProposal,
    )

    assert isinstance(result, MerchantAgentProposal)
    assert result.product_id == "GAME-001"
    assert result.upsell is None


def test_generate_structured_uses_strict_json_schema():
    content = json.dumps({"product_id": "GAME-001", "upsell": None})
    client, fake = make_client(content)

    client.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=MerchantAgentProposal,
    )

    response_format = fake.completions.kwargs["response_format"]
    schema = response_format["json_schema"]

    assert response_format["type"] == "json_schema"
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert set(schema["schema"]["required"]) == {"product_id", "upsell"}


def test_generate_structured_rejects_empty_response():
    client, _ = make_client("")

    with pytest.raises(ValueError, match="empty structured response"):
        client.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=MerchantAgentProposal,
        )


def test_generate_structured_rejects_invalid_json():
    client, _ = make_client("not-json")

    with pytest.raises(ValueError, match="invalid JSON"):
        client.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=MerchantAgentProposal,
        )
