"""
SentinelForge Model Adapters
Provider-agnostic interface for interacting with LLMs.

SECURITY: All prompts are scrubbed through the redaction layer
before being sent to any external AI provider.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("sentinelforge.adapters")

# ---------- Redaction integration ----------
try:
    from services.redaction import redact_text, redact_messages
except ImportError:
    # Fallback if running outside the API service context
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))
    try:
        from services.redaction import redact_text, redact_messages
    except ImportError:
        logger.warning("Redaction module not available — prompts will NOT be scrubbed!")
        def redact_text(text: str) -> str:
            return text
        def redact_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
            return messages


class BaseModelAdapter(ABC):
    """Base class for LLM provider adapters.
    
    All adapters automatically redact sensitive data from prompts
    before sending them to external providers.
    """

    provider: str = "unknown"

    @abstractmethod
    async def send_prompt(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Send a prompt and return the response text."""
        ...

    @abstractmethod
    async def send_messages(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Send a conversation and return the response text."""
        ...

    async def check_health(self) -> bool:
        """Check if the provider is reachable."""
        try:
            await self.send_prompt("Hello")
            return True
        except Exception:
            return False


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI / Azure OpenAI adapter."""

    provider = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4", base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"

    async def send_prompt(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        import httpx

        # Redact sensitive data before sending to external API
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        messages = []
        if safe_system:
            messages.append({"role": "system", "content": safe_system})
        messages.append({"role": "user", "content": safe_prompt})
        return await self.send_messages(messages, **kwargs)

    async def send_messages(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import httpx

        # Redact all message contents
        safe_messages = redact_messages(messages)
        logger.info(f"OpenAI request: {len(safe_messages)} messages → {self.model}")

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": safe_messages, **kwargs},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


class AnthropicAdapter(BaseModelAdapter):
    """Anthropic Claude adapter."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    async def send_prompt(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        # Redact before sending
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        messages = [{"role": "user", "content": safe_prompt}]
        return await self.send_messages(messages, system_prompt=safe_system, **kwargs)

    async def send_messages(self, messages: List[Dict[str, str]], system_prompt: str = None, **kwargs) -> str:
        import httpx

        # Redact all message contents
        safe_messages = redact_messages(messages)
        logger.info(f"Anthropic request: {len(safe_messages)} messages → {self.model}")

        body = {"model": self.model, "messages": safe_messages, "max_tokens": kwargs.get("max_tokens", 4096)}
        if system_prompt:
            body["system"] = redact_text(system_prompt)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]


class AzureOpenAIAdapter(BaseModelAdapter):
    """Azure OpenAI adapter."""

    provider = "azure_openai"

    def __init__(self, api_key: str, endpoint: str, deployment: str, api_version: str = "2024-02-01"):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.deployment = deployment
        self.api_version = api_version

    async def send_prompt(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        # Redact before sending
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        messages = []
        if safe_system:
            messages.append({"role": "system", "content": safe_system})
        messages.append({"role": "user", "content": safe_prompt})
        return await self.send_messages(messages, **kwargs)

    async def send_messages(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import httpx

        # Redact all message contents
        safe_messages = redact_messages(messages)
        logger.info(f"Azure OpenAI request: {len(safe_messages)} messages → {self.deployment}")

        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers={"api-key": self.api_key},
                json={"messages": safe_messages, **kwargs},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


class BedrockAdapter(BaseModelAdapter):
    """AWS Bedrock adapter using boto3."""

    provider = "bedrock"

    def __init__(
        self,
        access_key_id: str = "",
        secret_access_key: str = "",
        region: str = "us-east-1",
        model: str = "anthropic.claude-3-sonnet-20240229-v1:0",
    ):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.model = model

    async def send_prompt(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None
        messages = [{"role": "user", "content": safe_prompt}]
        return await self.send_messages(messages, system_prompt=safe_system, **kwargs)

    async def send_messages(self, messages: List[Dict[str, str]], system_prompt: str = None, **kwargs) -> str:
        import asyncio
        import json

        safe_messages = redact_messages(messages)
        logger.info(f"Bedrock request: {len(safe_messages)} messages → {self.model}")

        def _invoke():
            import boto3

            client = boto3.client(
                "bedrock-runtime",
                aws_access_key_id=self.access_key_id or None,
                aws_secret_access_key=self.secret_access_key or None,
                region_name=self.region,
            )

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get("max_tokens", 4096),
                "messages": safe_messages,
            }
            if system_prompt:
                body["system"] = redact_text(system_prompt)

            response = client.invoke_model(
                modelId=self.model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        return await asyncio.to_thread(_invoke)


def get_adapter(provider: str, **kwargs) -> BaseModelAdapter:
    """Factory function to get the right adapter by provider name."""
    adapters = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "azure_openai": AzureOpenAIAdapter,
        "bedrock": BedrockAdapter,
    }
    adapter_class = adapters.get(provider)
    if not adapter_class:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(adapters.keys())}")
    return adapter_class(**kwargs)

