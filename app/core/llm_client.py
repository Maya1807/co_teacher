"""
LLM Client for LLMod.ai API.
Handles chat completions and embeddings with budget tracking.
"""
import asyncio
import httpx
import hashlib
from typing import Dict, Any, Optional, List
from app.config import get_settings


class BudgetExceededError(Exception):
    """Raised when LLM budget is exceeded."""
    pass


class LLMClient:
    """
    Client for LLMod.ai API with built-in budget tracking.
    Uses OpenAI-compatible API format.
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.llmod_base_url
        self.api_key = self.settings.llmod_api_key
        self.chat_model = self.settings.llmod_chat_model
        self.embedding_model = self.settings.llmod_embedding_model

        # Budget tracking (thread-safe with asyncio.Lock)
        self.total_spent = 0.0
        self.budget_limit = self.settings.budget_limit
        self.warning_threshold = self.settings.budget_warning_threshold
        self._budget_lock = asyncio.Lock()

        # Cost per 1K tokens (approximate for gpt-4o-mini equivalent)
        self.cost_per_1k_prompt = 0.00015
        self.cost_per_1k_completion = 0.0006
        self.cost_per_1k_embedding = 0.00002

    def _estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int = 0,
        is_embedding: bool = False
    ) -> float:
        """Estimate cost before making a call."""
        if is_embedding:
            return (prompt_tokens / 1000) * self.cost_per_1k_embedding
        return (
            (prompt_tokens / 1000) * self.cost_per_1k_prompt +
            (completion_tokens / 1000) * self.cost_per_1k_completion
        )

    def _check_budget(self, estimated_cost: float) -> bool:
        """Check if we have enough budget for the call."""
        if self.total_spent + estimated_cost > self.budget_limit:
            raise BudgetExceededError(
                f"Budget exceeded. Spent: ${self.total_spent:.4f}, "
                f"Limit: ${self.budget_limit:.2f}"
            )
        return True

    async def _update_budget(self, cost: float) -> None:
        """Update budget tracking after a call (thread-safe)."""
        async with self._budget_lock:
            self.total_spent += cost
            if self.total_spent >= self.warning_threshold:
                print(f"WARNING: Budget usage at ${self.total_spent:.4f} of ${self.budget_limit:.2f}")

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to LLMod.ai.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            model: Model to use (defaults to chat_model from settings)

        Returns:
            Dict with 'content', 'tokens_used', and 'cost'
        """
        model = model or self.chat_model

        # Estimate tokens (rough: 4 chars = 1 token)
        prompt_text = " ".join(m.get("content", "") for m in messages)
        estimated_prompt_tokens = len(prompt_text) // 4
        estimated_cost = self._estimate_cost(estimated_prompt_tokens, max_tokens // 2)

        self._check_budget(estimated_cost)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # GPT-5 models have special requirements:
            # 1. Only support temperature=1
            # 2. Use reasoning tokens internally, so we need higher max_tokens
            actual_temperature = temperature
            actual_max_tokens = max_tokens
            is_gpt5 = "gpt-5" in model.lower() or "gpt5" in model.lower()

            if is_gpt5:
                actual_temperature = 1.0
                # GPT-5 uses reasoning tokens internally. We need to request
                # more tokens to allow for reasoning + actual output.
                # Multiply by 5 to ensure enough tokens for response.
                actual_max_tokens = max_tokens * 5

            request_body = {
                "model": model,
                "messages": messages,
                "temperature": actual_temperature,
                "max_tokens": actual_max_tokens
            }
            
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            
            # Better error handling - log the actual error
            if response.status_code != 200:
                error_text = response.text
                print(f"LLM API Error ({response.status_code}): {error_text}")
                print(f"Request model: {model}")
                response.raise_for_status()
            
            data = response.json()

        # Extract usage info
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", estimated_prompt_tokens)
        completion_tokens = usage.get("completion_tokens", 0)

        # Calculate actual cost
        actual_cost = self._estimate_cost(prompt_tokens, completion_tokens)
        await self._update_budget(actual_cost)

        # Extract content
        content = data["choices"][0]["message"]["content"]

        return {
            "content": content,
            "tokens_used": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": prompt_tokens + completion_tokens
            },
            "cost": actual_cost,
            "model": model
        }

    async def embed(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """
        Generate embeddings for text using LLMod.ai.

        Args:
            text: Text to embed
            model: Embedding model to use

        Returns:
            List of floats (embedding vector, 1536 dimensions)
        """
        model = model or self.embedding_model

        # Estimate cost
        estimated_tokens = len(text) // 4
        estimated_cost = self._estimate_cost(estimated_tokens, is_embedding=True)

        self._check_budget(estimated_cost)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "input": text
                }
            )
            
            # Raise on embedding API failure to avoid silent degradation
            if response.status_code != 200:
                error_text = response.text
                raise RuntimeError(
                    f"Embedding API error ({response.status_code}): {error_text}. Model: {model}"
                )
            
            data = response.json()

        # Extract usage
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", estimated_tokens)

        # Calculate actual cost
        actual_cost = self._estimate_cost(tokens_used, is_embedding=True)
        await self._update_budget(actual_cost)

        # Extract embedding
        embedding = data["data"][0]["embedding"]

        return embedding

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        return {
            "total_spent": self.total_spent,
            "budget_limit": self.budget_limit,
            "remaining": self.budget_limit - self.total_spent,
            "percentage_used": (self.total_spent / self.budget_limit) * 100,
            "warning_threshold": self.warning_threshold,
            "is_warning": self.total_spent >= self.warning_threshold
        }

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        """Generate a hash for caching purposes."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
