"""
Unit tests for RuleBasedRouter.
Tests keyword and pattern matching for agent routing.
"""
import pytest
from app.core.router import (
    RuleBasedRouter,
    RoutingResult,
    AgentType,
    get_router,
    route_query
)


class TestStudentAgentRouting:
    """Tests for STUDENT_AGENT routing rules."""

    @pytest.fixture
    def router(self):
        """Create a fresh router instance."""
        return RuleBasedRouter()

    def test_routes_profile_query(self, router):
        """Routes profile queries to STUDENT_AGENT."""
        result = router.route("Show me Alex's profile")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_routes_triggers_query(self, router):
        """Routes trigger queries to STUDENT_AGENT."""
        result = router.route("What are Jordan's triggers?")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_routes_history_query(self, router):
        """Routes history queries to STUDENT_AGENT."""
        result = router.route("Tell me about Taylor's history")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_routes_what_works_query(self, router):
        """Routes 'what works' queries to STUDENT_AGENT."""
        result = router.route("What works for Morgan?")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_routes_check_on_query(self, router):
        """Routes 'check on' queries to STUDENT_AGENT."""
        result = router.route("Check on Alex")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_routes_behavior_query(self, router):
        """Routes behavior queries to STUDENT_AGENT."""
        result = router.route("Alex is having a meltdown")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_routes_learning_style_query(self, router):
        """Routes learning style queries to STUDENT_AGENT."""
        result = router.route("What is Jordan's learning style?")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_extracts_student_name(self, router):
        """Extracts student name from query."""
        # The router currently extracts single-word names from possessives
        result = router.route("Show me Alex Johnson's profile")
        # Pattern captures the word before 's, which is "Johnson"
        assert result.extracted_entities.get("name") == "Johnson"

    def test_extracts_single_name(self, router):
        """Extracts single-word student name."""
        result = router.route("What works for Morgan?")
        assert result.extracted_entities.get("name") == "Morgan"

    def test_high_confidence_for_pattern_match(self, router):
        """Pattern matches have high confidence."""
        result = router.route("Show me Alex's profile")
        assert result.confidence >= 0.9


class TestRAGAgentRouting:
    """Tests for RAG_AGENT routing rules."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_routes_strategy_query(self, router):
        """Routes strategy queries to RAG_AGENT."""
        result = router.route("What strategies work for ADHD students?")
        assert AgentType.RAG_AGENT in result.agents

    def test_routes_how_to_teach_query(self, router):
        """Routes 'how to teach' queries to RAG_AGENT."""
        result = router.route("How do I teach reading to visual learners?")
        assert AgentType.RAG_AGENT in result.agents

    def test_routes_method_query(self, router):
        """Routes method queries to RAG_AGENT."""
        result = router.route("Suggest methods for teaching math")
        assert AgentType.RAG_AGENT in result.agents

    def test_routes_best_way_query(self, router):
        """Routes 'best way' queries to RAG_AGENT."""
        result = router.route("What's the best way to engage autistic students?")
        assert AgentType.RAG_AGENT in result.agents

    def test_routes_technique_query(self, router):
        """Routes technique queries to RAG_AGENT."""
        result = router.route("Techniques for reading comprehension?")
        assert AgentType.RAG_AGENT in result.agents

    def test_routes_how_to_handle_query(self, router):
        """Routes 'how to handle' queries to RAG_AGENT."""
        result = router.route("How to handle transitions for ADHD students?")
        assert AgentType.RAG_AGENT in result.agents

    def test_routes_evidence_based_query(self, router):
        """Routes evidence-based queries to RAG_AGENT."""
        result = router.route("What are evidence-based interventions for dyslexia?")
        assert AgentType.RAG_AGENT in result.agents

    def test_routes_accommodate_query(self, router):
        """Routes accommodation queries to RAG_AGENT."""
        result = router.route("How can I accommodate students with autism?")
        assert AgentType.RAG_AGENT in result.agents


class TestAdminAgentRouting:
    """Tests for ADMIN_AGENT routing rules."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_routes_draft_report_query(self, router):
        """Routes draft report queries to ADMIN_AGENT."""
        result = router.route("Draft a progress report for Alex")
        assert AgentType.ADMIN_AGENT in result.agents

    def test_routes_iep_query(self, router):
        """Routes IEP queries to ADMIN_AGENT."""
        result = router.route("Update the IEP goals for Jordan")
        assert AgentType.ADMIN_AGENT in result.agents

    def test_routes_parent_email_query(self, router):
        """Routes parent email queries to ADMIN_AGENT."""
        result = router.route("Write an email to Alex's parent")
        assert AgentType.ADMIN_AGENT in result.agents

    def test_routes_daily_summary_query(self, router):
        """Routes daily summary queries to ADMIN_AGENT."""
        result = router.route("Give me a summary of the day")
        assert AgentType.ADMIN_AGENT in result.agents

    def test_routes_prepare_message_query(self, router):
        """Routes prepare message queries to ADMIN_AGENT."""
        result = router.route("Prepare a message for the parent meeting")
        assert AgentType.ADMIN_AGENT in result.agents

    def test_routes_incident_report_query(self, router):
        """Routes incident report queries to ADMIN_AGENT."""
        result = router.route("Create an incident report")
        assert AgentType.ADMIN_AGENT in result.agents

    def test_routes_weekly_report_query(self, router):
        """Routes weekly report queries to ADMIN_AGENT."""
        result = router.route("Generate a weekly report for my class")
        assert AgentType.ADMIN_AGENT in result.agents

    def test_extracts_doc_type(self, router):
        """Extracts document type from query."""
        result = router.route("Draft a report for Alex")
        assert result.extracted_entities.get("doc_type") == "report"


class TestMultiAgentRouting:
    """Tests for queries requiring multiple agents."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_routes_student_and_rag_query(self, router):
        """Routes queries needing both student info and strategies."""
        result = router.route(
            "What teaching strategies work best for Alex Johnson?"
        )
        assert AgentType.STUDENT_AGENT in result.agents
        assert AgentType.RAG_AGENT in result.agents
        assert result.is_multi_agent

    def test_routes_student_and_admin_query(self, router):
        """Routes queries needing both student info and admin tasks."""
        result = router.route(
            "Draft a progress report for Alex"
        )
        assert AgentType.STUDENT_AGENT in result.agents
        assert AgentType.ADMIN_AGENT in result.agents
        assert result.is_multi_agent

    def test_routes_complex_query_to_multiple_agents(self, router):
        """Routes complex queries to multiple agents."""
        result = router.route(
            "Check Alex's profile and then suggest strategies for his triggers"
        )
        assert AgentType.STUDENT_AGENT in result.agents
        assert AgentType.RAG_AGENT in result.agents
        assert result.is_multi_agent

    def test_extracts_name_in_multi_agent_query(self, router):
        """Extracts student name in multi-agent queries."""
        result = router.route(
            "What teaching strategies work best for Alex Johnson?"
        )
        assert result.extracted_entities.get("name") == "Alex Johnson"


class TestLowConfidenceRouting:
    """Tests for low-confidence and fallback scenarios."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_ambiguous_query_needs_llm(self, router):
        """Ambiguous queries require LLM confirmation."""
        result = router.route("Can you assist with this task?")
        assert result.requires_llm_confirmation is True

    def test_unrelated_query_needs_llm(self, router):
        """Unrelated queries require LLM confirmation."""
        result = router.route("What's the weather today?")
        assert result.requires_llm_confirmation is True

    def test_low_confidence_for_vague_query(self, router):
        """Vague queries have low confidence."""
        result = router.route("I need help")
        assert result.confidence < 0.5

    def test_empty_query_needs_llm(self, router):
        """Empty queries require LLM confirmation."""
        result = router.route("")
        assert result.requires_llm_confirmation is True


class TestKeywordMatching:
    """Tests for keyword-based routing."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_single_keyword_medium_confidence(self, router):
        """Single keyword match has medium confidence."""
        result = router.route("What is the student profile format?")
        # "profile" is a keyword, no pattern match
        assert AgentType.STUDENT_AGENT in result.agents
        assert result.confidence == 0.7  # Keyword match

    def test_multiple_keywords_higher_confidence(self, router):
        """Multiple keyword matches increase confidence."""
        result = router.route("Student profile triggers learning style")
        assert AgentType.STUDENT_AGENT in result.agents
        assert result.confidence >= 0.7  # Multiple keywords

    def test_competing_keywords_best_wins(self, router):
        """When keywords compete, highest count wins."""
        result = router.route("Suggest strategies methods techniques approach")
        # All RAG keywords
        assert AgentType.RAG_AGENT in result.agents


class TestRouterUtilities:
    """Tests for router utility functions."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_extract_student_name_from_possessive(self, router):
        """Extracts name from possessive form."""
        name = router.extract_student_name("Show me Alex's profile")
        assert name == "Alex"

    def test_extract_student_name_with_full_name(self, router):
        """Extracts name from 'check on [Name]' pattern."""
        # Pattern captures the word after "check on", which is "Alex"
        name = router.extract_student_name("Check on Alex Johnson")
        assert name == "Alex"

    def test_extract_student_name_no_match(self, router):
        """Returns None when no name found."""
        name = router.extract_student_name("What strategies work for ADHD?")
        assert name is None

    def test_get_routing_explanation(self, router):
        """Generates readable routing explanation."""
        result = router.route("Show me Alex's profile")
        explanation = router.get_routing_explanation(result)
        assert "STUDENT_AGENT" in explanation
        assert "90%" in explanation or "confidence" in explanation.lower()

    def test_explanation_for_llm_fallback(self, router):
        """Generates explanation for LLM fallback."""
        result = router.route("random unrelated query xyz")
        explanation = router.get_routing_explanation(result)
        assert "LLM" in explanation


class TestRoutingResultDataclass:
    """Tests for RoutingResult dataclass."""

    def test_default_entities_empty_dict(self):
        """Default extracted_entities is empty dict."""
        result = RoutingResult(
            agents=[AgentType.STUDENT_AGENT],
            confidence=0.9
        )
        assert result.extracted_entities == {}

    def test_entities_preserved(self):
        """Extracted entities are preserved."""
        result = RoutingResult(
            agents=[AgentType.STUDENT_AGENT],
            confidence=0.9,
            extracted_entities={"name": "Alex"}
        )
        assert result.extracted_entities["name"] == "Alex"

    def test_agent_property_returns_first(self):
        """The agent property returns the first agent in the list."""
        result = RoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT],
            confidence=0.9
        )
        assert result.agent == AgentType.STUDENT_AGENT

    def test_is_multi_agent_property(self):
        """is_multi_agent returns True for multiple agents."""
        single = RoutingResult(agents=[AgentType.RAG_AGENT], confidence=0.9)
        multi = RoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT],
            confidence=0.9
        )
        assert single.is_multi_agent is False
        assert multi.is_multi_agent is True


class TestSingletonAndConvenience:
    """Tests for singleton pattern and convenience functions."""

    def test_get_router_returns_instance(self):
        """get_router returns a RuleBasedRouter instance."""
        router = get_router()
        assert isinstance(router, RuleBasedRouter)

    def test_get_router_returns_same_instance(self):
        """get_router returns the same instance."""
        router1 = get_router()
        router2 = get_router()
        assert router1 is router2

    def test_route_query_convenience_function(self):
        """route_query convenience function works."""
        result = route_query("Show me Alex's profile")
        assert AgentType.STUDENT_AGENT in result.agents


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_case_insensitive_matching(self, router):
        """Matching is case-insensitive for keywords."""
        result1 = router.route("SHOW ME ALEX'S PROFILE")
        result2 = router.route("show me alex's profile")
        # Both should route to student agent (via keyword)
        assert AgentType.STUDENT_AGENT in result1.agents
        assert AgentType.STUDENT_AGENT in result2.agents

    def test_handles_punctuation(self, router):
        """Handles queries with punctuation."""
        result = router.route("What are Alex's triggers?!")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_handles_extra_whitespace(self, router):
        """Handles queries with extra whitespace."""
        result = router.route("   Show me   Alex's   profile   ")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_very_long_query(self, router):
        """Handles very long queries."""
        long_query = "Show me Alex's profile " + "and more details " * 100
        result = router.route(long_query)
        assert AgentType.STUDENT_AGENT in result.agents

    def test_unicode_in_query(self, router):
        """Handles unicode characters."""
        result = router.route("Show me Alex's profile — with emojis")
        assert AgentType.STUDENT_AGENT in result.agents


class TestRealWorldScenarios:
    """Tests with realistic teacher queries."""

    @pytest.fixture
    def router(self):
        return RuleBasedRouter()

    def test_morning_check_scenario(self, router):
        """Morning check-in scenario."""
        result = router.route("How is Alex doing today?")
        # Pattern: "how is [Name]"
        assert AgentType.STUDENT_AGENT in result.agents

    def test_meltdown_help_scenario(self, router):
        """Crisis intervention scenario."""
        result = router.route("Alex is having a meltdown, what should I do?")
        # Has student name - should include STUDENT_AGENT
        assert AgentType.STUDENT_AGENT in result.agents

    def test_iep_meeting_prep_scenario(self, router):
        """IEP meeting preparation scenario."""
        result = router.route("Prepare materials for Jordan's IEP meeting")
        # Has student name and admin task
        assert AgentType.STUDENT_AGENT in result.agents
        assert AgentType.ADMIN_AGENT in result.agents

    def test_new_strategy_request_scenario(self, router):
        """New strategy request scenario."""
        result = router.route(
            "I've tried visual schedules but they're not working. "
            "What strategies work for autism?"
        )
        assert AgentType.RAG_AGENT in result.agents

    def test_parent_communication_scenario(self, router):
        """Parent communication scenario."""
        result = router.route(
            "Draft an email to the parents about the meeting"
        )
        assert AgentType.ADMIN_AGENT in result.agents

    def test_behavior_tracking_scenario(self, router):
        """Behavior tracking scenario."""
        result = router.route("Update that Alex had a good day with no incidents")
        assert AgentType.STUDENT_AGENT in result.agents

    def test_personalized_strategy_request(self, router):
        """Strategy request for specific student."""
        result = router.route(
            "What teaching strategies work best for Alex Johnson?"
        )
        # Should route to both STUDENT and RAG agents
        assert AgentType.STUDENT_AGENT in result.agents
        assert AgentType.RAG_AGENT in result.agents
        assert result.extracted_entities.get("name") == "Alex Johnson"


class TestLLMFallbackRouting:
    """Tests for LLM fallback routing functionality."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        from unittest.mock import AsyncMock, MagicMock
        client = MagicMock()
        client.complete = AsyncMock(return_value={
            "content": '{"intent": "test", "primary_agent": "RAG_AGENT", "student_name": null}',
            "tokens_used": {"input": 50, "output": 30},
            "cost": 0.001
        })
        return client

    @pytest.fixture
    def mock_tracker(self):
        """Create a mock step tracker."""
        from unittest.mock import MagicMock
        tracker = MagicMock()
        tracker.add_step = MagicMock()
        return tracker

    @pytest.fixture
    def router_with_llm(self, mock_llm_client, mock_tracker):
        """Create router with LLM client configured."""
        return RuleBasedRouter(
            llm_client=mock_llm_client,
            step_tracker=mock_tracker
        )

    @pytest.fixture
    def router_without_llm(self):
        """Create router without LLM client."""
        return RuleBasedRouter()

    @pytest.mark.asyncio
    async def test_route_with_fallback_uses_rules_when_llm_disabled(self, router_with_llm, mock_llm_client):
        """Rule-based routing is used when use_llm_fallback=False."""
        result = await router_with_llm.route_with_fallback(
            "Show me Alex's profile",
            use_llm_fallback=False
        )

        assert AgentType.STUDENT_AGENT in result.agents
        # LLM should NOT be called when disabled
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_with_fallback_uses_llm_when_enabled(self, router_with_llm, mock_llm_client):
        """LLM routing is used when use_llm_fallback=True (default)."""
        result = await router_with_llm.route_with_fallback(
            "Hello there",
            use_llm_fallback=True
        )

        # LLM should be called directly
        mock_llm_client.complete.assert_called_once()
        assert result.matched_pattern == "llm_routing"

    @pytest.mark.asyncio
    async def test_route_with_fallback_rules_only_for_ambiguous(self, router_with_llm, mock_llm_client):
        """Rule-based routing returns low confidence for ambiguous queries when LLM is disabled."""
        result = await router_with_llm.route_with_fallback(
            "Hello there",
            use_llm_fallback=False
        )

        # LLM should NOT be called when disabled
        mock_llm_client.complete.assert_not_called()
        assert result.requires_llm_confirmation is True

    @pytest.mark.asyncio
    async def test_route_with_fallback_no_llm_configured(self, router_without_llm):
        """Falls back to rule-based when no LLM client is configured."""
        result = await router_without_llm.route_with_fallback(
            "Hello there"
        )

        # Should return low-confidence rule-based result
        assert result.requires_llm_confirmation is True

    @pytest.mark.asyncio
    async def test_llm_route_extracts_student_name(self, router_with_llm, mock_llm_client):
        """LLM routing extracts student name from response."""
        mock_llm_client.complete.return_value = {
            "content": '{"intent": "profile", "primary_agent": "STUDENT_AGENT", "student_name": "Alex"}',
            "tokens_used": {"input": 50, "output": 30}
        }

        result = await router_with_llm.route_with_fallback("Hello there")

        assert AgentType.STUDENT_AGENT in result.agents
        assert result.extracted_entities.get("name") == "Alex"

    @pytest.mark.asyncio
    async def test_llm_route_multi_agent(self, router_with_llm, mock_llm_client):
        """LLM routing supports multi-agent responses."""
        mock_llm_client.complete.return_value = {
            "content": '{"intent": "personalized", "primary_agent": "STUDENT_AGENT", "follow_up_agent": "RAG_AGENT", "student_name": "Alex"}',
            "tokens_used": {"input": 50, "output": 30}
        }

        result = await router_with_llm.route_with_fallback("Hello there")

        assert AgentType.STUDENT_AGENT in result.agents
        assert AgentType.RAG_AGENT in result.agents

    @pytest.mark.asyncio
    async def test_llm_route_handles_invalid_json(self, router_with_llm, mock_llm_client):
        """LLM routing handles invalid JSON gracefully."""
        mock_llm_client.complete.return_value = {
            "content": "This is not valid JSON",
            "tokens_used": {"input": 50, "output": 30}
        }

        result = await router_with_llm.route_with_fallback("Hello there")

        # Should fall back to RAG_AGENT
        assert AgentType.RAG_AGENT in result.agents
        assert result.matched_pattern == "llm_routing_fallback"

    @pytest.mark.asyncio
    async def test_llm_route_tracks_step(self, router_with_llm, mock_llm_client, mock_tracker):
        """LLM routing tracks step when tracker configured."""
        await router_with_llm.route_with_fallback("Hello there")

        # Step should be tracked
        mock_tracker.add_step.assert_called_once()
        call_args = mock_tracker.add_step.call_args
        assert call_args.kwargs["module"] == "ORCHESTRATOR"
        assert call_args.kwargs["prompt"]["action"] == "llm_routing"
