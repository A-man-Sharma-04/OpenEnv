"""
LLM Integration Module
Supports pluggable LLM providers with caching and error handling.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import asyncio
import hashlib
import json


class LLMProvider(ABC):
    """Base LLM provider interface"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from prompt"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get model identifier"""
        pass


class GroqProvider(LLMProvider):
    """Groq API provider"""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant", **kwargs):
        try:
            from groq import Groq

            self.client = Groq(api_key=api_key)
        except ImportError:
            raise ImportError("groq package required for Groq provider")

        self.model = model
        self.kwargs = kwargs

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate with Groq"""
        try:
            def _call() -> Any:
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=kwargs.get("temperature", 0.0),
                    max_tokens=kwargs.get("max_tokens", 1000),
                    **self.kwargs,
                )

            response = await asyncio.to_thread(_call)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")

    def get_model_name(self) -> str:
        return f"groq-{self.model}"


class MockProvider(LLMProvider):
    """Mock provider for testing"""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> str:
        """Return mock response"""
        self.call_count += 1

        # Hash prompt for consistent responses
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]

        if prompt_hash in self.responses:
            return self.responses[prompt_hash]

        # Default mock response
        return '{"score": 0.75, "reasoning": "Mock evaluation response", "confidence": 0.8}'

    def get_model_name(self) -> str:
        return "mock-provider"


class LLMManager:
    """Manages LLM providers with caching and fallback"""

    def __init__(self, providers: List[LLMProvider], cache_enabled: bool = True):
        self.providers = providers
        self.primary_provider = providers[0] if providers else None
        self.cache_enabled = cache_enabled
        self.cache: Dict[str, str] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate with caching and fallback"""
        cache_key = self._get_cache_key(prompt, kwargs)

        # Check cache
        if self.cache_enabled and cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]

        self.cache_misses += 1

        # Try providers in order
        last_error = None
        for provider in self.providers:
            try:
                response = await provider.generate(prompt, **kwargs)
                # Cache successful response
                if self.cache_enabled:
                    self.cache[cache_key] = response
                return response
            except Exception as e:
                last_error = e
                continue

        raise Exception(f"All LLM providers failed. Last error: {last_error}")

    def _get_cache_key(self, prompt: str, kwargs: Dict[str, Any]) -> str:
        """Generate cache key"""
        key_data = {
            "prompt": prompt,
            "kwargs": sorted(kwargs.items()),
            "model": self.primary_provider.get_model_name() if self.primary_provider else "unknown"
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        total_calls = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_calls if total_calls > 0 else 0

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
            "providers": [p.get_model_name() for p in self.providers]
        }

    def clear_cache(self):
        """Clear response cache"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0


class PromptTemplate:
    """Template for LLM prompts"""

    def __init__(self, template: str, variables: Optional[Dict[str, str]] = None):
        self.template = template
        self.variables = variables or {}

    def format(self, **kwargs) -> str:
        """Format template with variables"""
        format_vars = {**self.variables, **kwargs}
        return self.template.format(**format_vars)

    @classmethod
    def for_code_review(cls) -> 'PromptTemplate':
        """Template for code review evaluation"""
        template = """
Evaluate this code review action:

Code: {code}
Action: {action}
Review Type: {review_type}

Rate the quality from 0.0 to 1.0 considering:
- Technical accuracy
- Clarity of explanation
- Appropriateness of suggestion

Return JSON: {{"score": 0.85, "reasoning": "Detailed reasoning here", "confidence": 0.9}}
"""
        return cls(template)

    @classmethod
    def for_decision_making(cls) -> 'PromptTemplate':
        """Template for decision evaluation"""
        template = """
Evaluate this decision:

Scenario: {scenario}
Decision: {decision}
Reasoning: {reasoning}

Rate the decision quality from 0.0 to 1.0 considering:
- Logical consistency
- Completeness of reasoning
- Appropriateness for context

Return JSON: {{"score": 0.75, "reasoning": "Analysis here", "confidence": 0.8}}
"""
        return cls(template)