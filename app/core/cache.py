"""
Response caching to save LLM costs.
Uses Supabase for persistent caching with TTL.
"""
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class ResponseCache:
    """
    Cache for LLM responses to save costs.

    Caching strategy:
    - RAG responses: Cache (teaching methods don't change often)
    - Admin templates: Cache
    - Student-specific queries: Don't cache (too dynamic)
    """

    # Agents whose responses should be cached
    CACHEABLE_AGENTS = ["RAG_AGENT", "ADMIN_AGENT", "PREDICT_AGENT"]

    # Default TTL in hours
    DEFAULT_TTL_HOURS = 24

    @staticmethod
    def get_hours_until_midnight() -> int:
        """Calculate hours until midnight for date-based cache expiration."""
        now = datetime.now()
        midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        hours = (midnight - now).seconds // 3600
        return max(1, hours)  # At least 1 hour

    def __init__(self, supabase_client=None):
        """
        Initialize cache with optional Supabase client.
        Falls back to in-memory cache if no client provided.
        """
        self.supabase = supabase_client
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _generate_cache_key(prompt: str, agent_type: str) -> str:
        """Generate a unique cache key from prompt and agent."""
        content = f"{agent_type}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """Generate a hash of the prompt for storage."""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def should_cache(self, agent_type: str) -> bool:
        """Check if responses from this agent should be cached."""
        return agent_type in self.CACHEABLE_AGENTS

    async def get(
        self,
        prompt: str,
        agent_type: str
    ) -> Optional[str]:
        """
        Get cached response if available and not expired.

        Args:
            prompt: The original prompt
            agent_type: The agent that would handle this

        Returns:
            Cached response string or None if not found/expired
        """
        if not self.should_cache(agent_type):
            return None

        cache_key = self._generate_cache_key(prompt, agent_type)

        # Try Supabase first if available
        if self.supabase:
            try:
                result = await self.supabase.get_cache(cache_key)
                if result:
                    # Update hit count
                    await self.supabase.increment_cache_hit(cache_key)
                    return result["response"]
            except Exception:
                pass  # Fall through to memory cache

        # Fall back to memory cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if datetime.now() < entry["expires_at"]:
                return entry["response"]
            else:
                # Expired, remove it
                del self._memory_cache[cache_key]

        return None

    async def set(
        self,
        prompt: str,
        response: str,
        agent_type: str,
        ttl_hours: int = None
    ) -> bool:
        """
        Cache a response.

        Args:
            prompt: The original prompt
            response: The response to cache
            agent_type: The agent that generated this response
            ttl_hours: Time to live in hours (default: 24)

        Returns:
            True if cached successfully
        """
        if not self.should_cache(agent_type):
            return False

        ttl_hours = ttl_hours or self.DEFAULT_TTL_HOURS
        cache_key = self._generate_cache_key(prompt, agent_type)
        prompt_hash = self._hash_prompt(prompt)
        expires_at = datetime.now() + timedelta(hours=ttl_hours)

        # Try Supabase first if available
        if self.supabase:
            try:
                await self.supabase.set_cache(
                    cache_key=cache_key,
                    prompt_hash=prompt_hash,
                    response=response,
                    agent_type=agent_type,
                    expires_at=expires_at
                )
                return True
            except Exception:
                pass  # Fall through to memory cache

        # Fall back to memory cache
        self._memory_cache[cache_key] = {
            "response": response,
            "agent_type": agent_type,
            "expires_at": expires_at,
            "hit_count": 1
        }
        return True

    async def invalidate(self, prompt: str, agent_type: str) -> bool:
        """Remove a specific cache entry."""
        cache_key = self._generate_cache_key(prompt, agent_type)

        if self.supabase:
            try:
                await self.supabase.delete_cache(cache_key)
            except Exception:
                pass

        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]

        return True

    async def clear_expired(self) -> int:
        """Clear all expired cache entries. Returns count of cleared entries."""
        cleared = 0

        # Clear from Supabase
        if self.supabase:
            try:
                cleared += await self.supabase.clear_expired_cache()
            except Exception:
                pass

        # Clear from memory cache
        now = datetime.now()
        expired_keys = [
            k for k, v in self._memory_cache.items()
            if v["expires_at"] < now
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            cleared += 1

        return cleared

    def clear_memory_cache(self) -> None:
        """Clear the in-memory cache."""
        self._memory_cache.clear()


# Singleton instance
_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get or create the cache singleton."""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache


def init_cache(supabase_client) -> ResponseCache:
    """Initialize cache with Supabase client."""
    global _cache
    _cache = ResponseCache(supabase_client)
    return _cache
