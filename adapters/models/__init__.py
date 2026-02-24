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
    async def send_prompt(
        self,
        prompt: str,
        system_prompt: str = None,
        images: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """Send a prompt and return the response text.

        Args:
            prompt: The user prompt text.
            system_prompt: Optional system instruction.
            images: Optional list of base64-encoded images (PNG/JPEG).
        """
        ...

    @abstractmethod
    async def send_messages(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Send a conversation and return the response text."""
        ...

    async def send_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        """Send messages with tool/function definitions.

        Returns:
            {"content": str, "tool_calls": [{"name": str, "arguments": dict}]}

        Default: falls back to send_messages() with tools described in system prompt.
        """
        tool_descriptions = []
        for t in tools:
            desc = f"- {t['name']}: {t.get('description', '')}"
            if t.get("parameters", {}).get("properties"):
                params = ", ".join(t["parameters"]["properties"].keys())
                desc += f" (params: {params})"
            tool_descriptions.append(desc)

        tool_text = "Available tools:\n" + "\n".join(tool_descriptions)
        tool_text += '\n\nTo call a tool, respond with JSON: {"tool_call": {"name": "tool_name", "arguments": {...}}}'

        augmented = [{"role": "system", "content": tool_text}] + list(messages)
        content = await self.send_messages(augmented, **kwargs)

        # Try to parse tool calls from the response
        tool_calls = _extract_tool_calls(content)
        return {"content": content, "tool_calls": tool_calls}

    async def check_health(self) -> bool:
        """Check if the provider is reachable."""
        try:
            await self.send_prompt("Hello")
            return True
        except Exception:
            return False


def _extract_tool_calls(content: str) -> List[Dict[str, Any]]:
    """Extract tool calls from free-text LLM response (fallback parser)."""
    import json
    import re

    calls = []
    # Look for JSON blocks with tool_call pattern
    patterns = [
        r'\{"tool_call"\s*:\s*(\{[^}]+\})\}',
        r'\{"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\}',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content, re.DOTALL):
            try:
                if match.lastindex == 1:
                    obj = json.loads(match.group(1))
                    calls.append(
                        {
                            "name": obj.get("name", ""),
                            "arguments": obj.get("arguments", {}),
                        }
                    )
                elif match.lastindex == 2:
                    calls.append(
                        {
                            "name": match.group(1),
                            "arguments": json.loads(match.group(2)),
                        }
                    )
            except (json.JSONDecodeError, KeyError):
                continue
    return calls


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI / Azure OpenAI adapter."""

    provider = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4", base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"

    async def send_prompt(
        self,
        prompt: str,
        system_prompt: str = None,
        images: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        messages: List[Dict[str, Any]] = []
        if safe_system:
            messages.append({"role": "system", "content": safe_system})

        if images:
            content: List[Dict[str, Any]] = [{"type": "text", "text": safe_prompt}]
            for img in images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img}"},
                    }
                )
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": safe_prompt})

        return await self.send_messages(messages, **kwargs)

    async def send_messages(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        import httpx

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

    async def send_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        import httpx
        import json

        safe_messages = redact_messages(messages)
        # Convert to OpenAI function calling format
        openai_tools = []
        for t in tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )

        async with httpx.AsyncClient(timeout=60) as client:
            body: Dict[str, Any] = {
                "model": self.model,
                "messages": safe_messages,
                "tools": openai_tools,
            }
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        tool_calls = []
        for tc in msg.get("tool_calls", []):
            try:
                args = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, KeyError):
                args = {}
            tool_calls.append({"name": tc["function"]["name"], "arguments": args})
        return {"content": content, "tool_calls": tool_calls}


class AnthropicAdapter(BaseModelAdapter):
    """Anthropic Claude adapter."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    async def send_prompt(
        self,
        prompt: str,
        system_prompt: str = None,
        images: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        if images:
            content: List[Dict[str, Any]] = [{"type": "text", "text": safe_prompt}]
            for img in images:
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img,
                        },
                    }
                )
            messages: List[Dict[str, Any]] = [{"role": "user", "content": content}]
        else:
            messages = [{"role": "user", "content": safe_prompt}]

        return await self.send_messages(messages, system_prompt=safe_system, **kwargs)

    async def send_messages(
        self, messages: List[Dict[str, Any]], system_prompt: str = None, **kwargs
    ) -> str:
        import httpx

        safe_messages = redact_messages(messages)
        logger.info(f"Anthropic request: {len(safe_messages)} messages → {self.model}")

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": safe_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
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

    async def send_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        import httpx

        safe_messages = redact_messages(messages)
        anthropic_tools = []
        for t in tools:
            anthropic_tools.append(
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
            )

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": safe_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "tools": anthropic_tools,
        }
        if kwargs.get("system_prompt"):
            body["system"] = redact_text(kwargs["system_prompt"])

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
            data = response.json()

        content = ""
        tool_calls = []
        for block in data.get("content", []):
            if block["type"] == "text":
                content += block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(
                    {"name": block["name"], "arguments": block.get("input", {})}
                )
        return {"content": content, "tool_calls": tool_calls}


class AzureOpenAIAdapter(BaseModelAdapter):
    """Azure OpenAI adapter."""

    provider = "azure_openai"

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-02-01",
    ):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.deployment = deployment
        self.api_version = api_version

    async def send_prompt(
        self,
        prompt: str,
        system_prompt: str = None,
        images: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        messages: List[Dict[str, Any]] = []
        if safe_system:
            messages.append({"role": "system", "content": safe_system})

        if images:
            content: List[Dict[str, Any]] = [{"type": "text", "text": safe_prompt}]
            for img in images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img}"},
                    }
                )
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": safe_prompt})

        return await self.send_messages(messages, **kwargs)

    async def send_messages(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        import httpx

        safe_messages = redact_messages(messages)
        logger.info(
            f"Azure OpenAI request: {len(safe_messages)} messages → {self.deployment}"
        )

        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers={"api-key": self.api_key},
                json={"messages": safe_messages, **kwargs},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def send_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        import httpx
        import json

        safe_messages = redact_messages(messages)
        openai_tools = []
        for t in tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )

        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers={"api-key": self.api_key},
                json={"messages": safe_messages, "tools": openai_tools},
            )
            response.raise_for_status()
            data = response.json()

        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        tool_calls = []
        for tc in msg.get("tool_calls", []):
            try:
                args = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, KeyError):
                args = {}
            tool_calls.append({"name": tc["function"]["name"], "arguments": args})
        return {"content": content, "tool_calls": tool_calls}


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

    async def send_prompt(
        self,
        prompt: str,
        system_prompt: str = None,
        images: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        if images:
            content: List[Dict[str, Any]] = [{"type": "text", "text": safe_prompt}]
            for img in images:
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img,
                        },
                    }
                )
            messages: List[Dict[str, Any]] = [{"role": "user", "content": content}]
        else:
            messages = [{"role": "user", "content": safe_prompt}]

        return await self.send_messages(messages, system_prompt=safe_system, **kwargs)

    async def send_messages(
        self, messages: List[Dict[str, Any]], system_prompt: str = None, **kwargs
    ) -> str:
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

            body: Dict[str, Any] = {
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


class CustomGatewayAdapter(BaseModelAdapter):
    """Universal adapter for custom LLM gateways and non-standard APIs.

    Supports preset request templates (openai, anthropic, cohere, google, raw)
    and configurable response extraction via dot-notation paths.
    """

    provider = "custom"

    # Preset URL suffixes per template
    _URL_SUFFIXES = {
        "openai": "/chat/completions",
        "anthropic": "/messages",
        "cohere": "/chat",
        "google": "",
        "raw": "",
    }

    # Default dot-notation paths to extract response text
    _DEFAULT_RESPONSE_PATHS = {
        "openai": "choices.0.message.content",
        "anthropic": "content.0.text",
        "cohere": "text",
        "google": "candidates.0.content.parts.0.text",
        "raw": "",  # tries multiple fallbacks
    }

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        model: str = "",
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        request_template: str = "openai",
        response_path: str = "",
        extra_headers: Optional[Dict[str, str]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.request_template = (
            request_template if request_template in self._URL_SUFFIXES else "openai"
        )
        self.response_path = response_path or self._DEFAULT_RESPONSE_PATHS.get(
            self.request_template, ""
        )
        self.extra_headers = extra_headers or {}
        self.extra_body = extra_body or {}

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            if self.auth_prefix:
                headers[self.auth_header] = f"{self.auth_prefix} {self.api_key}"
            else:
                headers[self.auth_header] = self.api_key
        if self.request_template == "anthropic":
            headers.setdefault("anthropic-version", "2023-06-01")
        headers.update(self.extra_headers)
        return headers

    def _build_url(self) -> str:
        suffix = self._URL_SUFFIXES.get(self.request_template, "")
        if suffix and not self.base_url.endswith(suffix):
            return self.base_url + suffix
        return self.base_url

    def _build_request_body(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        t = self.request_template

        if t == "openai":
            msgs = messages if messages else []
            if not msgs:
                if system_prompt:
                    msgs.append({"role": "system", "content": system_prompt})
                msgs.append({"role": "user", "content": prompt})
            body: Dict[str, Any] = {"model": self.model, "messages": msgs}

        elif t == "anthropic":
            msgs = messages if messages else [{"role": "user", "content": prompt}]
            body = {"model": self.model, "messages": msgs, "max_tokens": 4096}
            if system_prompt:
                body["system"] = system_prompt

        elif t == "cohere":
            body = {"model": self.model, "message": prompt}
            if system_prompt:
                body["preamble"] = system_prompt

        elif t == "google":
            parts: List[Dict[str, str]] = []
            if system_prompt:
                parts.append({"text": f"System: {system_prompt}\n\n{prompt}"})
            else:
                parts.append({"text": prompt})
            body = {"contents": [{"parts": parts}]}
            if self.model:
                body["model"] = self.model

        else:  # raw
            body = {"prompt": prompt, "model": self.model}
            if system_prompt:
                body["system"] = system_prompt

        body.update(self.extra_body)
        return body

    def _extract_response(self, data: Any) -> str:
        if self.response_path:
            return self._walk_path(data, self.response_path)

        # raw template: try common response field names
        for key in (
            "response",
            "text",
            "output",
            "generated_text",
            "content",
            "result",
        ):
            if isinstance(data, dict) and key in data:
                val = data[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, list) and val:
                    first = val[0]
                    if isinstance(first, str):
                        return first
                    if isinstance(first, dict):
                        return first.get("text", str(first))

        return str(data)

    @staticmethod
    def _walk_path(data: Any, path: str) -> str:
        for segment in path.split("."):
            if isinstance(data, dict):
                data = data.get(segment)
            elif isinstance(data, list):
                try:
                    data = data[int(segment)]
                except (ValueError, IndexError):
                    return ""
            else:
                return ""
            if data is None:
                return ""
        return str(data) if data is not None else ""

    async def send_prompt(
        self,
        prompt: str,
        system_prompt: str = None,
        images: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        import httpx

        safe_prompt = redact_text(prompt)
        safe_system = redact_text(system_prompt) if system_prompt else None

        body = self._build_request_body(safe_prompt, safe_system)
        url = self._build_url()
        headers = self._build_headers()

        logger.info(f"Custom gateway request: {self.request_template} template → {url}")

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        return self._extract_response(data)

    async def send_messages(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        import httpx

        safe_messages = redact_messages(messages)

        system_prompt = kwargs.get("system_prompt")
        if not system_prompt:
            # Extract system message from messages list if present
            non_system = []
            for m in safe_messages:
                if m.get("role") == "system":
                    system_prompt = m.get("content", "")
                else:
                    non_system.append(m)
            if system_prompt:
                safe_messages = non_system

        safe_system = redact_text(system_prompt) if system_prompt else None

        # For templates that support multi-message, pass messages directly
        if self.request_template in ("openai", "anthropic"):
            body = self._build_request_body("", safe_system, messages=safe_messages)
        else:
            # Flatten messages to single prompt for simple templates
            parts = []
            for m in safe_messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                parts.append(f"{role}: {content}")
            flat_prompt = "\n".join(parts)
            body = self._build_request_body(flat_prompt, safe_system)

        url = self._build_url()
        headers = self._build_headers()

        logger.info(
            f"Custom gateway messages: {self.request_template} template, {len(safe_messages)} msgs → {url}"
        )

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        return self._extract_response(data)


def get_adapter(provider: str, **kwargs) -> BaseModelAdapter:
    """Factory function to get the right adapter by provider name."""
    adapters = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "azure_openai": AzureOpenAIAdapter,
        "bedrock": BedrockAdapter,
        "custom": CustomGatewayAdapter,
    }
    adapter_class = adapters.get(provider)
    if not adapter_class:
        raise ValueError(
            f"Unknown provider: {provider}. Available: {list(adapters.keys())}"
        )
    return adapter_class(**kwargs)
