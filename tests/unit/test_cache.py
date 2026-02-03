"""
Unit tests for ResponseCache.
Tests caching logic to save LLM costs.
"""
import pytest
from datetime import datetime, timedelta
from app.core.cache import ResponseCache, get_cache, init_cache


class TestResponseCache:
    """Tests for the ResponseCache class."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance for each test."""
        return ResponseCache()

    def test_should_cache_rag_agent(self, cache):
        """RAG_AGENT responses should be cached."""
        assert cache.should_cache("RAG_AGENT") is True

    def test_should_cache_admin_agent(self, cache):
        """ADMIN_AGENT responses should be cached."""
        assert cache.should_cache("ADMIN_AGENT") is True

    def test_should_not_cache_student_agent(self, cache):
        """STUDENT_AGENT responses should NOT be cached (too dynamic)."""
        assert cache.should_cache("STUDENT_AGENT") is False

    def test_should_not_cache_orchestrator(self, cache):
        """ORCHESTRATOR responses should NOT be cached."""
        assert cache.should_cache("ORCHESTRATOR") is False

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """Can set and retrieve cached response."""
        prompt = "Suggest strategies for teaching reading to visual learners"
        response = "Use graphic organizers and color coding..."

        # Set cache
        result = await cache.set(prompt, response, "RAG_AGENT")
        assert result is True

        # Get cache
        cached = await cache.get(prompt, "RAG_AGENT")
        assert cached == response

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache):
        """Cache miss returns None."""
        result = await cache.get("Never seen this prompt", "RAG_AGENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_non_cacheable_agent_returns_none(self, cache):
        """Queries for non-cacheable agents return None."""
        prompt = "Check Alex's profile"

        # Try to set (should fail/skip)
        await cache.set(prompt, "Some response", "STUDENT_AGENT")

        # Get should return None
        result = await cache.get(prompt, "STUDENT_AGENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_different_agents_different_keys(self, cache):
        """Same prompt for different agents creates different cache keys."""
        prompt = "Some shared prompt"

        await cache.set(prompt, "RAG response", "RAG_AGENT")
        await cache.set(prompt, "Admin response", "ADMIN_AGENT")

        rag_cached = await cache.get(prompt, "RAG_AGENT")
        admin_cached = await cache.get(prompt, "ADMIN_AGENT")

        assert rag_cached == "RAG response"
        assert admin_cached == "Admin response"

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache):
        """Can invalidate specific cache entry."""
        prompt = "Test prompt"
        await cache.set(prompt, "Test response", "RAG_AGENT")

        # Verify it's cached
        assert await cache.get(prompt, "RAG_AGENT") == "Test response"

        # Invalidate
        await cache.invalidate(prompt, "RAG_AGENT")

        # Should be gone
        assert await cache.get(prompt, "RAG_AGENT") is None

    def test_clear_memory_cache(self, cache):
        """Can clear in-memory cache."""
        cache._memory_cache["key1"] = {"response": "value1", "expires_at": datetime.now() + timedelta(hours=1)}
        cache._memory_cache["key2"] = {"response": "value2", "expires_at": datetime.now() + timedelta(hours=1)}

        assert len(cache._memory_cache) == 2

        cache.clear_memory_cache()

        assert len(cache._memory_cache) == 0

    @pytest.mark.asyncio
    async def test_expired_cache_not_returned(self, cache):
        """Expired cache entries are not returned."""
        prompt = "Test prompt"
        cache_key = cache._generate_cache_key(prompt, "RAG_AGENT")

        # Manually add expired entry
        cache._memory_cache[cache_key] = {
            "response": "Expired response",
            "agent_type": "RAG_AGENT",
            "expires_at": datetime.now() - timedelta(hours=1)  # Already expired
        }

        # Should not return expired entry
        result = await cache.get(prompt, "RAG_AGENT")
        assert result is None

        # Entry should be removed
        assert cache_key not in cache._memory_cache

    def test_generate_cache_key_consistency(self, cache):
        """Same inputs generate same cache key."""
        key1 = cache._generate_cache_key("test prompt", "RAG_AGENT")
        key2 = cache._generate_cache_key("test prompt", "RAG_AGENT")

        assert key1 == key2

    def test_generate_cache_key_uniqueness(self, cache):
        """Different inputs generate different cache keys."""
        key1 = cache._generate_cache_key("prompt 1", "RAG_AGENT")
        key2 = cache._generate_cache_key("prompt 2", "RAG_AGENT")
        key3 = cache._generate_cache_key("prompt 1", "ADMIN_AGENT")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_hash_prompt(self):
        """Prompt hashing is consistent."""
        hash1 = ResponseCache._hash_prompt("test prompt")
        hash2 = ResponseCache._hash_prompt("test prompt")
        hash3 = ResponseCache._hash_prompt("different prompt")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex digest

    @pytest.mark.asyncio
    async def test_clear_expired(self, cache):
        """clear_expired removes only expired entries."""
        # Add expired entry
        cache._memory_cache["expired"] = {
            "response": "old",
            "expires_at": datetime.now() - timedelta(hours=1)
        }

        # Add valid entry
        cache._memory_cache["valid"] = {
            "response": "new",
            "expires_at": datetime.now() + timedelta(hours=1)
        }

        cleared = await cache.clear_expired()

        assert cleared == 1
        assert "expired" not in cache._memory_cache
        assert "valid" in cache._memory_cache


class TestCacheSingleton:
    """Tests for singleton pattern functions."""

    def test_get_cache_returns_instance(self):
        """get_cache returns a ResponseCache instance."""
        cache = get_cache()
        assert isinstance(cache, ResponseCache)

    def test_init_cache_with_supabase(self):
        """init_cache creates cache with Supabase client."""
        mock_supabase = object()  # Mock client
        cache = init_cache(mock_supabase)

        assert isinstance(cache, ResponseCache)
        assert cache.supabase is mock_supabase


class TestCacheKeyGeneration:
    """Tests for cache key generation edge cases."""

    def test_empty_prompt(self):
        """Handles empty prompt."""
        cache = ResponseCache()
        key = cache._generate_cache_key("", "RAG_AGENT")
        assert len(key) == 32

    def test_very_long_prompt(self):
        """Handles very long prompts."""
        cache = ResponseCache()
        long_prompt = "x" * 10000
        key = cache._generate_cache_key(long_prompt, "RAG_AGENT")
        assert len(key) == 32

    def test_unicode_prompt(self):
        """Handles unicode in prompts."""
        cache = ResponseCache()
        unicode_prompt = "Suggest strategies for student with ADHD"
        key = cache._generate_cache_key(unicode_prompt, "RAG_AGENT")
        assert len(key) == 32

    def test_special_characters(self):
        """Handles special characters."""
        cache = ResponseCache()
        special_prompt = "What's the best method? (for students < 10 years)"
        key = cache._generate_cache_key(special_prompt, "RAG_AGENT")
        assert len(key) == 32
