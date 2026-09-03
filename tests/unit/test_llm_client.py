import pytest

from apps.api.agents.llm_client import LLMClient


def test_llm_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        LLMClient()


def test_llm_client_requires_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    with pytest.raises(ValueError, match="GROQ_MODEL"):
        LLMClient()


def test_llm_client_reads_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")

    client = LLMClient()

    assert client.api_key == "test-key"
    assert client.model == "openai/gpt-oss-20b"


def test_llm_client_accepts_explicit_configuration(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    client = LLMClient(
        api_key="explicit-key",
        model="openai/gpt-oss-20b",
    )

    assert client.api_key == "explicit-key"
    assert client.model == "openai/gpt-oss-20b"