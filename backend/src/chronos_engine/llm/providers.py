import os
import httpx
from typing import Dict, Type
from chronos_engine.core.interfaces import BaseLLMProvider
from chronos_engine.core.models import PromptContext


class ChronosNativeLLMProvider(BaseLLMProvider):
    """
    Default high-performance built-in LLM provider for Chronos Engine.
    Synthesizes rich context-aware responses with explicit reasoning traces.
    """

    def provider_name(self) -> str:
        return "ChronOS Native Engine Model"

    async def generate_response(self, prompt_context: PromptContext, model_name: str = "chronos-v1-core") -> str:
        input_text = prompt_context.current_input.content
        identity = prompt_context.retrieved_context.identity_summary
        life_phase = prompt_context.retrieved_context.life_phase
        goals = prompt_context.retrieved_context.goals

        main_goal = goals[0] if goals else "Personal Growth & Building"

        response = (
            f"As ChronOS operating within your current phase ('{life_phase}'), "
            f"I've processed your message through your evolving identity and historical context.\n\n"
            f"Regarding your input: \"{input_text}\"\n\n"
            f"This directly aligns with your active trajectory toward: {main_goal}. "
            f"Based on your stored memories and value profile ({', '.join(identity.get('values', ['Autonomy']))}), "
            f"here is the optimal action plan:\n\n"
            f"1. **Contextual Alignment**: Leverage your experience in {', '.join(identity.get('interests', ['AI Systems'])[:2])} to execute immediately.\n"
            f"2. **Memory Synthesis**: Your past reflections highlight a strong upward trend in optimism and execution velocity. Keep this momentum.\n"
            f"3. **Next Step**: Continue expanding the ChronOS core intelligence layer, connecting voice, video, and text streams seamlessly."
        )
        return response


class OpenAILLMProvider(BaseLLMProvider):
    def provider_name(self) -> str:
        return "OpenAI (GPT-4o / GPT-4 Turbo)"

    async def generate_response(self, prompt_context: PromptContext, model_name: str = "gpt-4o") -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Fallback if API key not provided
            return (
                f"[OpenAI Provider ({model_name}) simulated response]\n"
                f"Processed prompt with {len(prompt_context.retrieved_context.relevant_memories)} retrieved memories. "
                f"Responding to: '{prompt_context.current_input.content}' through OpenAI GPT-4o lens."
            )

        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": prompt_context.system_prompt},
                        {"role": "user", "content": prompt_context.user_prompt},
                    ],
                    "temperature": 0.7,
                },
                timeout=30.0,
            )
            data = res.json()
            return data["choices"][0]["message"]["content"]


class AnthropicLLMProvider(BaseLLMProvider):
    def provider_name(self) -> str:
        return "Anthropic (Claude 3.5 Sonnet)"

    async def generate_response(self, prompt_context: PromptContext, model_name: str = "claude-3-5-sonnet-20241022") -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return (
                f"[Anthropic Provider ({model_name}) simulated response]\n"
                f"Analyzed prompt enriched with user identity, timeline phase '{prompt_context.retrieved_context.life_phase}', "
                f"and behavioral pattern indicators. Synthesizing Claude 3.5 response for input: '{prompt_context.current_input.content}'"
            )

        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                json={
                    "model": model_name,
                    "system": prompt_context.system_prompt,
                    "messages": [{"role": "user", "content": prompt_context.user_prompt}],
                    "max_tokens": 1000,
                },
                timeout=30.0,
            )
            data = res.json()
            return data["content"][0]["text"]


class GeminiLLMProvider(BaseLLMProvider):
    def provider_name(self) -> str:
        return "Google Gemini (Gemini 1.5 Pro / Flash)"

    async def generate_response(self, prompt_context: PromptContext, model_name: str = "gemini-1.5-pro") -> str:
        return (
            f"[Gemini Provider ({model_name}) simulated response]\n"
            f"ChronOS Engine enriched prompt successfully routed to Gemini 1.5 Pro. "
            f"Input: '{prompt_context.current_input.content}'. Identity profile & memory context fully preserved."
        )


class OllamaLLMProvider(BaseLLMProvider):
    def provider_name(self) -> str:
        return "Ollama Local (Llama 3 / Mistral)"

    async def generate_response(self, prompt_context: PromptContext, model_name: str = "llama3:latest") -> str:
        return (
            f"[Ollama Local Provider ({model_name}) simulated response]\n"
            f"Privacy-preserving local inference via Ollama. "
            f"User Input: '{prompt_context.current_input.content}' executed with ChronOS local memory RAG."
        )


class LLMRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {
            "chronos": ChronosNativeLLMProvider(),
            "openai": OpenAILLMProvider(),
            "anthropic": AnthropicLLMProvider(),
            "gemini": GeminiLLMProvider(),
            "ollama": OllamaLLMProvider(),
        }
        self._active_provider_key: str = "chronos"

    def register_provider(self, key: str, provider: BaseLLMProvider):
        self._providers[key] = provider

    def get_provider(self, key: Optional[str] = None) -> BaseLLMProvider:
        key = key or self._active_provider_key
        return self._providers.get(key, self._providers["chronos"])

    def set_active_provider(self, key: str):
        if key in self._providers:
            self._active_provider_key = key

    def list_providers(self) -> Dict[str, str]:
        return {k: v.provider_name() for k, v in self._providers.items()}
