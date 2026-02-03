"""
Frontend integration tests.
Verifies that static files are served correctly and contain expected content.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestStaticFilesServing:
    """Tests for static file serving."""

    @pytest.mark.asyncio
    async def test_root_serves_index_html(self):
        """Test that root path serves index.html."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "Co-Teacher" in response.text

    @pytest.mark.asyncio
    async def test_index_html_structure(self):
        """Test that index.html contains required elements."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            html = response.text

            # Required structural elements (chat-based UI)
            assert '<textarea' in html
            assert 'id="chat-input"' in html
            assert 'id="send-btn"' in html
            assert 'id="messages"' in html
            assert 'id="trace-sidebar"' in html

    @pytest.mark.asyncio
    async def test_index_html_has_student_sidebar(self):
        """Test that index.html has student sidebar that loads dynamically."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            html = response.text

            # Check for sidebar elements (chat-based UI)
            assert 'id="class-sidebar"' in html
            assert 'id="class-sidebar-content"' in html

            # Students are loaded dynamically via JavaScript
            js_response = await client.get("/static/app.js")
            js_content = js_response.text

            assert '/api/students' in js_content

    @pytest.mark.asyncio
    async def test_index_html_has_landing_screen(self):
        """Test that index.html has landing screen with input."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            html = response.text

            assert 'id="landing-screen"' in html
            assert 'id="landing-input"' in html

    @pytest.mark.asyncio
    async def test_index_html_has_chat_screen(self):
        """Test that index.html has chat screen elements."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            html = response.text

            assert 'id="chat-screen"' in html
            assert 'id="new-chat-btn"' in html

    @pytest.mark.asyncio
    async def test_styles_css_served(self):
        """Test that styles.css is served correctly."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/styles.css")
            assert response.status_code == 200
            assert "text/css" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_styles_css_has_required_styles(self):
        """Test that styles.css contains required CSS rules."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/styles.css")
            css = response.text

            # CSS variables (chat-based UI)
            assert '--purple' in css
            assert '--bg-gray' in css

            # Required classes (chat-based UI)
            assert '.chat-messages' in css
            assert '.chat-input-bar' in css
            assert '.sidebar' in css
            assert '.step-header' in css
            assert '.typing-indicator' in css

    @pytest.mark.asyncio
    async def test_styles_css_has_responsive_design(self):
        """Test that styles.css includes responsive media queries."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/styles.css")
            css = response.text

            assert '@media' in css
            assert 'max-width: 768px' in css

    @pytest.mark.asyncio
    async def test_app_js_served(self):
        """Test that app.js is served correctly."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            assert response.status_code == 200
            # JavaScript may be served with various content types
            content_type = response.headers.get("content-type", "")
            assert "javascript" in content_type or "text/plain" in content_type or "application" in content_type

    @pytest.mark.asyncio
    async def test_app_js_has_required_functions(self):
        """Test that app.js contains required functions."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            js = response.text

            # Required functions (chat-based UI)
            assert 'function sendMessage' in js or 'async function sendMessage' in js
            assert 'function addBotMessage' in js
            assert 'function addUserMessage' in js
            assert 'function renderTraceSteps' in js
            assert 'function openTrace' in js
            assert 'function closeTrace' in js

    @pytest.mark.asyncio
    async def test_app_js_uses_correct_api_field(self):
        """Test that app.js sends 'prompt' (the correct field name) to API."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            js = response.text

            # Should use 'prompt' field (the correct field name)
            assert 'prompt: text' in js or '"prompt":' in js or 'prompt:' in js
            # The old bug was sending { query } instead of { prompt }
            assert 'body: JSON.stringify({ query })' not in js

    @pytest.mark.asyncio
    async def test_app_js_has_class_data_loading(self):
        """Test that app.js has class data loading functionality."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            js = response.text

            assert 'function loadClassData' in js or 'async function loadClassData' in js
            assert '/api/students' in js

    @pytest.mark.asyncio
    async def test_app_js_has_predictions(self):
        """Test that app.js has predictions functionality."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            js = response.text

            assert 'function loadPredictions' in js or 'async function loadPredictions' in js
            assert 'function renderPredictions' in js

    @pytest.mark.asyncio
    async def test_app_js_has_copy_functionality(self):
        """Test that app.js has copy to clipboard functionality."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            js = response.text

            assert 'function copyText' in js
            assert 'clipboard' in js

    @pytest.mark.asyncio
    async def test_app_js_has_toggle_step(self):
        """Test that app.js has toggle step functionality."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            js = response.text

            assert 'function toggleStep' in js


class TestFrontendAPIIntegration:
    """Tests for frontend-API integration."""

    @pytest.mark.asyncio
    async def test_api_docs_available(self):
        """Test that API documentation is available."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/docs")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_info_endpoints_available(self):
        """Test that API info endpoints are available."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/team_info")
            assert response.status_code == 200
            response = await client.get("/api/agent_info")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_app_js_targets_correct_execute_endpoint(self):
        """Test that app.js targets the correct execute endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/app.js")
            js = response.text

            assert '/api/execute' in js
            assert 'POST' in js


class TestAccessibility:
    """Accessibility tests for the frontend."""

    @pytest.mark.asyncio
    async def test_index_has_lang_attribute(self):
        """Test that index.html has lang attribute for accessibility."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            html = response.text

            assert 'lang="en"' in html

    @pytest.mark.asyncio
    async def test_index_has_meta_viewport(self):
        """Test that index.html has viewport meta tag for mobile."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            html = response.text

            assert 'viewport' in html
            assert 'width=device-width' in html

    @pytest.mark.asyncio
    async def test_interactive_elements_have_aria_labels(self):
        """Test that interactive elements have aria-label for accessibility."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            html = response.text

            # Check for aria-label on interactive elements
            assert 'aria-label="View class info"' in html
            assert 'aria-label="Close' in html

    @pytest.mark.asyncio
    async def test_styles_has_reduced_motion(self):
        """Test that styles.css respects prefers-reduced-motion."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/styles.css")
            css = response.text

            assert 'prefers-reduced-motion' in css
