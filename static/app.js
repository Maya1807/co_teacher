/**
 * Co-Teacher Chat Application
 * Modern chat interface with landing screen, chat bubbles, and trace sidebar
 */

const API_BASE = '';

// State
let isLanding = true;
let messages = [];
let currentTraceMessageId = null;

// DOM elements (populated on load)
let landingScreen, chatScreen, messagesContainer, chatInput, landingInput, sendBtn;
let traceSidebar, traceOverlay, sidebarContent;
let classSidebar, classOverlay, classSidebarContent, classHeaderTitle;

// Class data
let studentsData = [];

// Predictions data
let predictionsData = [];
let predictionsExpanded = false;

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', () => {
    // Cache DOM elements
    landingScreen = document.getElementById('landing-screen');
    chatScreen = document.getElementById('chat-screen');
    messagesContainer = document.getElementById('messages');
    chatInput = document.getElementById('chat-input');
    landingInput = document.getElementById('landing-input');
    sendBtn = document.getElementById('send-btn');
    traceSidebar = document.getElementById('trace-sidebar');
    traceOverlay = document.getElementById('trace-overlay');
    sidebarContent = document.getElementById('sidebar-content');
    classSidebar = document.getElementById('class-sidebar');
    classOverlay = document.getElementById('class-overlay');
    classSidebarContent = document.getElementById('class-sidebar-content');
    classHeaderTitle = document.getElementById('class-header-title');

    // Focus landing input
    if (landingInput) {
        landingInput.focus();
    }

    // Load class data, predictions, and schedule
    loadClassData();
    loadPredictions();
    loadSchedule();

    // Handle Enter key on landing input
    if (landingInput) {
        landingInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendFromLanding();
            }
        });
    }
});

/**
 * Switch from landing screen to chat screen
 */
function switchToChat() {
    if (!isLanding) return;

    landingScreen.style.display = 'none';
    chatScreen.style.display = 'flex';
    isLanding = false;

    // Focus chat input
    if (chatInput) {
        chatInput.focus();
    }
}

/**
 * Start a new conversation - return to landing screen
 */
function startNewChat() {
    // Clear messages array
    messages.length = 0;

    // Clear messages container
    if (messagesContainer) {
        messagesContainer.innerHTML = '';
    }

    // Clear input fields
    if (chatInput) {
        chatInput.value = '';
    }
    if (landingInput) {
        landingInput.value = '';
    }

    // Switch back to landing screen
    chatScreen.style.display = 'none';
    landingScreen.style.display = 'flex';
    isLanding = true;

    // Focus landing input
    if (landingInput) {
        landingInput.focus();
    }
}

/**
 * Send message from landing screen
 */
function sendFromLanding() {
    const text = landingInput.value.trim();
    if (!text) return;

    // Switch to chat view first
    switchToChat();

    // Add initial bot greeting
    addBotMessage("Hey! how can I help you today?", []);

    // Process the user message
    processUserMessage(text);
}

/**
 * Send message from example chip
 */
function sendChip(text) {
    landingInput.value = text;
    sendFromLanding();
}

/**
 * Handle keyboard events in chat input
 */
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * Auto-resize textarea
 */
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

/**
 * Send message from chat input
 */
function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    processUserMessage(text);
    chatInput.value = '';
    chatInput.style.height = 'auto';
}

/**
 * Process a user message - add to UI and call API
 */
async function processUserMessage(text) {
    // Add user message to UI
    addUserMessage(text);

    // Disable input while processing
    if (sendBtn) sendBtn.disabled = true;

    // Show typing indicator
    showTypingIndicator(true);

    try {
        const response = await fetch(`${API_BASE}/api/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: text })
        });

        const data = await response.json();

        if (response.status === 422 || data.status === 'error') {
            const errorMsg = data.detail?.[0]?.msg || data.error || 'An error occurred';
            addErrorMessage(errorMsg);
        } else {
            addBotMessage(data.response, data.steps || []);

            // Always refresh student data after each response
            // This ensures UI stays in sync with any profile updates
            loadClassData();
        }
    } catch (error) {
        addErrorMessage(`Network error: ${error.message}`);
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        showTypingIndicator(false);
        scrollToBottom();
    }
}

/**
 * Add a user message to the chat
 */
function addUserMessage(content) {
    const messageId = Date.now();
    const timestamp = new Date();

    messages.push({
        id: messageId,
        role: 'user',
        content,
        timestamp
    });

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';
    messageDiv.dataset.messageId = messageId;

    const timeStr = formatTime(timestamp);
    const formattedContent = formatMessageContent(content);

    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-bubble">${formattedContent}</div>
            <span class="message-time">${timeStr}</span>
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Add a bot message to the chat
 */
function addBotMessage(content, steps = []) {
    const messageId = Date.now();
    const timestamp = new Date();

    messages.push({
        id: messageId,
        role: 'assistant',
        content,
        steps,
        timestamp
    });

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.dataset.messageId = messageId;

    const timeStr = formatTime(timestamp);
    const formattedContent = formatMessageContent(content);
    const hasSteps = steps && steps.length > 0;

    // Bot avatar image
    const avatarImg = `<img src="/static/icon.png" alt="Co-Teacher Bot" class="bot-avatar-img">`;

    messageDiv.innerHTML = `
        <div class="bot-avatar">${avatarImg}</div>
        <div class="message-content">
            <div class="message-bubble" ${hasSteps ? `onclick="openTrace(${messageId})"` : ''}>
                ${formattedContent}
            </div>
            <span class="message-time">${timeStr}</span>
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Add an error message
 */
function addErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message assistant';
    errorDiv.innerHTML = `
        <div class="bot-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="2" fill="none"/>
                <line x1="12" y1="8" x2="12" y2="12" stroke="#ef4444" stroke-width="2"/>
                <circle cx="12" cy="16" r="1" fill="#ef4444"/>
            </svg>
        </div>
        <div class="message-content">
            <div class="message-bubble" style="border: 1px solid #fecaca; background: #fef2f2; color: #dc2626;">
                ${escapeHtml(message)}
            </div>
        </div>
    `;
    messagesContainer.appendChild(errorDiv);
    scrollToBottom();
}

/**
 * Show/hide typing indicator
 */
function showTypingIndicator(show) {
    const existingIndicator = document.getElementById('typing-indicator');

    if (show) {
        if (!existingIndicator) {
            const indicator = document.createElement('div');
            indicator.id = 'typing-indicator';
            indicator.className = 'typing-indicator';
            indicator.innerHTML = `
                <div class="bot-avatar">
                    <img src="/static/icon.png" alt="Co-Teacher Bot" class="bot-avatar-img">
                </div>
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            messagesContainer.appendChild(indicator);
        }
        scrollToBottom();
    } else {
        if (existingIndicator) {
            existingIndicator.remove();
        }
    }
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

/**
 * Open trace sidebar for a message
 */
function openTrace(messageId) {
    const message = messages.find(m => m.id === messageId);
    if (!message || !message.steps || message.steps.length === 0) return;

    currentTraceMessageId = messageId;
    renderTraceSteps(message.steps);

    traceSidebar.classList.add('open');
    traceOverlay.classList.add('open');

    // Trap focus in sidebar
    trapFocus();
}

/**
 * Close trace sidebar
 */
function closeTrace() {
    traceSidebar.classList.remove('open');
    traceOverlay.classList.remove('open');
    currentTraceMessageId = null;
}

/**
 * Render trace steps in sidebar
 */
function renderTraceSteps(steps) {
    sidebarContent.innerHTML = '';

    steps.forEach((step, index) => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'trace-step';
        stepDiv.dataset.stepIndex = index;

        const moduleName = step.module || `Step ${index + 1}`;
        const promptText = typeof step.prompt === 'string'
            ? step.prompt
            : JSON.stringify(step.prompt, null, 2);
        const responseText = typeof step.response === 'string'
            ? step.response
            : JSON.stringify(step.response, null, 2);

        stepDiv.innerHTML = `
            <div class="step-header" onclick="toggleStep(${index})">
                <span class="step-module">${escapeHtml(moduleName)}</span>
                <span class="chevron">▼</span>
            </div>
            <div class="step-body">
                <div class="step-section">
                    <div class="step-section-header">
                        <span class="step-section-label">Prompt</span>
                        <button class="copy-btn" onclick="copyText(this, 'prompt', ${index})">Copy</button>
                    </div>
                    <pre>${escapeHtml(promptText)}</pre>
                </div>
                <div class="step-section">
                    <div class="step-section-header">
                        <span class="step-section-label">Response</span>
                        <button class="copy-btn" onclick="copyText(this, 'response', ${index})">Copy</button>
                    </div>
                    <pre>${escapeHtml(responseText)}</pre>
                </div>
            </div>
        `;

        sidebarContent.appendChild(stepDiv);
    });
}

/**
 * Toggle step accordion
 */
function toggleStep(index) {
    const stepDiv = document.querySelector(`.trace-step[data-step-index="${index}"]`);
    if (stepDiv) {
        stepDiv.classList.toggle('open');
    }
}

/**
 * Copy text to clipboard
 */
function copyText(button, type, stepIndex) {
    const message = messages.find(m => m.id === currentTraceMessageId);
    if (!message || !message.steps[stepIndex]) return;

    const step = message.steps[stepIndex];
    let text = type === 'prompt' ? step.prompt : step.response;

    if (typeof text !== 'string') {
        text = JSON.stringify(text, null, 2);
    }

    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 1500);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

/**
 * Trap focus within sidebar when open
 */
function trapFocus() {
    const focusableElements = traceSidebar.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length > 0) {
        focusableElements[0].focus();
    }
}

/**
 * Format message content with basic markdown
 */
function formatMessageContent(content) {
    if (!content) return '';

    let formatted = escapeHtml(content)
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Handle bullet points
    formatted = formatted.replace(/^[-•]\s+(.*)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)+/g, '<ul>$&</ul>');

    // Handle numbered lists
    formatted = formatted.replace(/^\d+\.\s+(.*)$/gm, '<li>$1</li>');

    return `<p>${formatted}</p>`.replace(/<p><\/p>/g, '');
}

/**
 * Format time for display
 */
function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: false
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (typeof text !== 'string') {
        text = JSON.stringify(text, null, 2);
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Keyboard handlers
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeTrace();
        closeClassSidebar();
    }
});

/* ==================== CLASS SIDEBAR ==================== */

/**
 * Load class data (students) from API
 */
async function loadClassData() {
    try {
        const response = await fetch(`${API_BASE}/api/students?full=true`);
        if (!response.ok) throw new Error('Failed to load students');

        const data = await response.json();
        studentsData = data.students || [];

        // Update header with teacher name if available
        if (classHeaderTitle) {
            classHeaderTitle.textContent = `My Class`;
        }

        renderStudentsList();
    } catch (error) {
        console.error('Error loading class data:', error);
        if (classSidebarContent) {
            classSidebarContent.innerHTML = `
                <div class="students-error">
                    Failed to load students.<br>
                    <button onclick="loadClassData()" style="margin-top: 12px; padding: 8px 16px; cursor: pointer;">
                        Retry
                    </button>
                </div>
            `;
        }
    }
}

/**
 * Render students list in sidebar
 */
function renderStudentsList() {
    if (!classSidebarContent || !studentsData.length) {
        if (classSidebarContent) {
            classSidebarContent.innerHTML = '<div class="students-loading">No students found</div>';
        }
        return;
    }

    classSidebarContent.innerHTML = studentsData.map((student, index) => {
        const disabilityChip = student.disability_type
            ? `<span class="student-chip focus">${escapeHtml(student.disability_type)}</span>`
            : '';

        const worksChip = student.successful_methods && student.successful_methods.length > 0
            ? `<span class="student-chip works">${escapeHtml(student.successful_methods[0])}</span>`
            : '';

        const avoidChip = student.failed_methods && student.failed_methods.length > 0
            ? `<span class="student-chip avoid">Avoid: ${escapeHtml(student.failed_methods[0])}</span>`
            : '';

        const triggers = student.triggers || [];
        const successfulMethods = student.successful_methods || [];
        const failedMethods = student.failed_methods || [];

        return `
            <div class="student-card" data-student-index="${index}">
                <div class="student-header" onclick="toggleStudent(${index})">
                    <div class="student-info">
                        <span class="student-name">${escapeHtml(student.name || 'Unknown')}</span>
                        <div class="student-chips">
                            ${disabilityChip}
                            ${worksChip}
                            ${avoidChip}
                        </div>
                    </div>
                    <span class="student-chevron">▼</span>
                </div>
                <div class="student-details">
                    ${student.grade ? `
                        <div class="student-section">
                            <div class="student-section-title">Grade</div>
                            <div>${escapeHtml(student.grade)}</div>
                        </div>
                    ` : ''}

                    ${student.learning_style ? `
                        <div class="student-section">
                            <div class="student-section-title">Learning Style</div>
                            <div>${escapeHtml(student.learning_style)}</div>
                        </div>
                    ` : ''}

                    ${triggers.length > 0 ? `
                        <div class="student-section">
                            <div class="student-section-title">Triggers</div>
                            <ul class="student-section-list">
                                ${triggers.map(t => `<li>${escapeHtml(t)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}

                    ${successfulMethods.length > 0 ? `
                        <div class="student-section">
                            <div class="student-section-title">What Works</div>
                            <ul class="student-section-list">
                                ${successfulMethods.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}

                    ${failedMethods.length > 0 ? `
                        <div class="student-section">
                            <div class="student-section-title">What to Avoid</div>
                            <ul class="student-section-list">
                                ${failedMethods.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}

                    ${student.notes ? `
                        <div class="student-section">
                            <div class="student-section-title">Notes</div>
                            <div>${escapeHtml(student.notes)}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Toggle student accordion
 */
function toggleStudent(index) {
    const studentCard = document.querySelector(`.student-card[data-student-index="${index}"]`);
    if (studentCard) {
        studentCard.classList.toggle('open');
    }
}

/**
 * Toggle class sidebar open/close
 */
function toggleClassSidebar() {
    if (!classSidebar || !classOverlay) {
        // Try to get them again
        classSidebar = document.getElementById('class-sidebar');
        classOverlay = document.getElementById('class-overlay');
    }
    if (classSidebar && classSidebar.classList.contains('open')) {
        closeClassSidebar();
    } else {
        openClassSidebar();
    }
}

/**
 * Open class sidebar
 */
function openClassSidebar() {
    if (classSidebar) classSidebar.classList.add('open');
    if (classOverlay) classOverlay.classList.add('open');
}

/**
 * Close class sidebar
 */
function closeClassSidebar() {
    if (classSidebar) classSidebar.classList.remove('open');
    if (classOverlay) classOverlay.classList.remove('open');
}

/* ==================== PREDICTIONS ==================== */

/**
 * Load predictions from API
 */
async function loadPredictions() {
    const predictionsContent = document.getElementById('predictions-content');
    const predictionsBadge = document.getElementById('predictions-badge');

    try {
        const response = await fetch(`${API_BASE}/api/predictions/today`);
        if (!response.ok) throw new Error('Failed to load predictions');

        const data = await response.json();
        predictionsData = data.predictions || [];

        // Update badge
        if (predictionsBadge) {
            const highRisk = predictionsData.filter(p => p.risk_level === 'high').length;
            const mediumRisk = predictionsData.filter(p => p.risk_level === 'medium').length;

            if (highRisk > 0) {
                predictionsBadge.textContent = `${highRisk} alert${highRisk > 1 ? 's' : ''}`;
                predictionsBadge.className = 'predictions-badge high';
            } else if (mediumRisk > 0) {
                predictionsBadge.textContent = `${mediumRisk} heads up`;
                predictionsBadge.className = 'predictions-badge medium';
            } else if (data.events && data.events.length > 0) {
                predictionsBadge.textContent = 'All clear';
                predictionsBadge.className = 'predictions-badge low';
            } else {
                predictionsBadge.textContent = 'No events';
                predictionsBadge.className = 'predictions-badge none';
            }
        }

        renderPredictions(data);
    } catch (error) {
        console.error('Error loading predictions:', error);
        if (predictionsContent) {
            predictionsContent.innerHTML = `
                <div class="predictions-error">
                    Failed to load predictions
                </div>
            `;
        }
    }
}

/**
 * Refresh predictions (bypass cache)
 */
async function refreshPredictions(event) {
    event.stopPropagation();  // Don't toggle the section

    const refreshBtn = event.currentTarget;
    refreshBtn.classList.add('spinning');

    const predictionsContent = document.getElementById('predictions-content');
    const predictionsBadge = document.getElementById('predictions-badge');

    predictionsContent.innerHTML = '<div class="predictions-loading">Refreshing predictions...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/predictions/today?refresh=true`);
        if (!response.ok) throw new Error('Failed to refresh');

        const data = await response.json();
        predictionsData = data.predictions || [];

        // Update badge
        if (predictionsBadge) {
            const highRisk = predictionsData.filter(p => p.risk_level === 'high').length;
            const mediumRisk = predictionsData.filter(p => p.risk_level === 'medium').length;

            if (highRisk > 0) {
                predictionsBadge.textContent = `${highRisk} alert${highRisk > 1 ? 's' : ''}`;
                predictionsBadge.className = 'predictions-badge high';
            } else if (mediumRisk > 0) {
                predictionsBadge.textContent = `${mediumRisk} heads up`;
                predictionsBadge.className = 'predictions-badge medium';
            } else if (data.events && data.events.length > 0) {
                predictionsBadge.textContent = 'All clear';
                predictionsBadge.className = 'predictions-badge low';
            } else {
                predictionsBadge.textContent = 'No events';
                predictionsBadge.className = 'predictions-badge none';
            }
        }

        renderPredictions(data);
    } catch (error) {
        console.error('Error refreshing predictions:', error);
        predictionsContent.innerHTML = '<div class="predictions-error">Failed to refresh</div>';
    } finally {
        refreshBtn.classList.remove('spinning');
    }
}

/**
 * Render predictions in the sidebar
 */
function renderPredictions(data) {
    const predictionsContent = document.getElementById('predictions-content');
    if (!predictionsContent) return;

    const { events, predictions, summary } = data;

    // If no events
    if (!events || events.length === 0) {
        predictionsContent.innerHTML = `
            <div class="predictions-empty">
                <div class="predictions-empty-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                        <line x1="16" y1="2" x2="16" y2="6"/>
                        <line x1="8" y1="2" x2="8" y2="6"/>
                        <line x1="3" y1="10" x2="21" y2="10"/>
                    </svg>
                </div>
                <div class="predictions-empty-text">No events scheduled for today</div>
            </div>
        `;
        return;
    }

    // If no predictions (all clear)
    if (!predictions || predictions.length === 0) {
        predictionsContent.innerHTML = `
            <div class="predictions-all-clear">
                <div class="predictions-all-clear-icon">&#10003;</div>
                <div class="predictions-all-clear-text">All clear for today</div>
                <div class="predictions-all-clear-subtext">${events.length} event${events.length > 1 ? 's' : ''} scheduled, no concerns identified</div>
            </div>
        `;
        return;
    }

    // Filter out low risk predictions
    const filteredPredictions = predictions.filter(p => p.risk_level !== 'low');

    // If no medium/high risk predictions, show all clear
    if (filteredPredictions.length === 0) {
        predictionsContent.innerHTML = `
            <div class="predictions-all-clear">
                <div class="predictions-all-clear-icon">&#10003;</div>
                <div class="predictions-all-clear-text">All clear for today</div>
                <div class="predictions-all-clear-subtext">${events.length} event${events.length > 1 ? 's' : ''} scheduled, no concerns identified</div>
            </div>
        `;
        return;
    }

    // Group predictions by event
    const byEvent = {};
    filteredPredictions.forEach(p => {
        const key = p.event_title;
        if (!byEvent[key]) {
            byEvent[key] = {
                event_title: p.event_title,
                event_time: p.event_time,
                predictions: []
            };
        }
        byEvent[key].predictions.push(p);
    });

    // Render predictions
    let html = '';
    let groupIndex = 0;
    Object.values(byEvent).forEach(group => {
        const timeStr = group.event_time ? `@ ${group.event_time}` : '';

        const groupId = `event-group-${groupIndex++}`;
        html += `
            <div class="prediction-event-group collapsed" id="${groupId}">
                <div class="prediction-event-header" onclick="toggleEventGroup('${groupId}')">
                    <span class="prediction-event-title">${escapeHtml(group.event_title)}</span>
                    <div style="display: flex; align-items: center;">
                        <span class="prediction-event-time">${escapeHtml(timeStr)}</span>
                        <span class="prediction-event-chevron">▼</span>
                    </div>
                </div>
                <div class="prediction-students">
        `;

        group.predictions.forEach(p => {
            const riskClass = `risk-${p.risk_level}`;
            const riskLabel = p.risk_level === 'high' ? 'High Risk' :
                             p.risk_level === 'medium' ? 'Heads Up' : 'Low Risk';

            const triggersHtml = p.triggers_matched && p.triggers_matched.length > 0
                ? `<div class="prediction-triggers">Triggers: ${escapeHtml(p.triggers_matched.join(', '))}</div>`
                : '';

            const recsHtml = p.recommendations && p.recommendations.length > 0
                ? `<ul class="prediction-recommendations">${p.recommendations.slice(0, 2).map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>`
                : '';

            html += `
                <div class="prediction-student-card ${riskClass}">
                    <div class="prediction-student-header">
                        <span class="prediction-student-name">${escapeHtml(p.student_name)}</span>
                        <span class="prediction-risk-badge ${riskClass}">${riskLabel}</span>
                    </div>
                    ${triggersHtml}
                    ${recsHtml}
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    });

    predictionsContent.innerHTML = html;
}

/**
 * Toggle predictions section expanded/collapsed
 */
function togglePredictions() {
    const section = document.getElementById('predictions-section');
    if (section) {
        section.classList.toggle('collapsed');
        predictionsExpanded = !section.classList.contains('collapsed');
    }
}

/**
 * Toggle individual event group collapsed/expanded
 */
function toggleEventGroup(groupId) {
    const group = document.getElementById(groupId);
    if (group) {
        group.classList.toggle('collapsed');
    }
}

/**
 * Toggle students section collapsed/expanded
 */
function toggleStudents() {
    const section = document.getElementById('students-section');
    if (section) {
        section.classList.toggle('collapsed');
    }
}

/**
 * Toggle schedule section collapsed/expanded
 */
function toggleSchedule() {
    const section = document.getElementById('schedule-section');
    if (section) {
        section.classList.toggle('collapsed');
    }
}

/**
 * Load today's schedule
 */
async function loadSchedule() {
    const scheduleContent = document.getElementById('schedule-content');
    const scheduleBadge = document.getElementById('schedule-badge');

    if (!scheduleContent) return;

    try {
        const response = await fetch(`${API_BASE}/api/schedule/today`);
        if (!response.ok) throw new Error('Failed to load schedule');

        const data = await response.json();
        const events = data.events || [];

        // Update badge
        if (scheduleBadge) {
            scheduleBadge.textContent = `${events.length} event${events.length !== 1 ? 's' : ''}`;
        }

        renderSchedule(events);
    } catch (error) {
        console.error('Error loading schedule:', error);
        scheduleContent.innerHTML = `
            <div class="schedule-empty">
                <div>Could not load schedule</div>
            </div>
        `;
        if (scheduleBadge) {
            scheduleBadge.textContent = '';
        }
    }
}

/**
 * Render today's schedule
 */
function renderSchedule(events) {
    const scheduleContent = document.getElementById('schedule-content');
    if (!scheduleContent) return;

    if (!events || events.length === 0) {
        scheduleContent.innerHTML = `
            <div class="schedule-empty">
                No events scheduled for today
            </div>
        `;
        return;
    }

    // Sort by start time
    events.sort((a, b) => (a.start_time || '').localeCompare(b.start_time || ''));

    let html = '';
    events.forEach(event => {
        const timeStr = event.start_time ? formatTime(event.start_time) : '';
        const eventType = event.event_type || 'class_schedule';
        const typeLabel = formatEventType(eventType);

        html += `
            <div class="schedule-item type-${eventType.replace('_schedule', '')}">
                <div class="schedule-item-time">${escapeHtml(timeStr)}</div>
                <div class="schedule-item-details">
                    <div class="schedule-item-title">${escapeHtml(event.title)}</div>
                    <div class="schedule-item-type">${escapeHtml(typeLabel)}</div>
                </div>
            </div>
        `;
    });

    scheduleContent.innerHTML = html;
}

/**
 * Format time from HH:MM:SS string or Date object to HH:MM AM/PM
 */
function formatTime(timeInput) {
    if (!timeInput) return '';

    let hours, minutes;

    // Handle Date objects
    if (timeInput instanceof Date) {
        hours = timeInput.getHours();
        minutes = timeInput.getMinutes().toString().padStart(2, '0');
    }
    // Handle string format "HH:MM:SS" or "HH:MM"
    else if (typeof timeInput === 'string') {
        const parts = timeInput.split(':');
        hours = parseInt(parts[0], 10);
        minutes = parts[1] || '00';
    } else {
        return '';
    }

    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    return `${hours}:${minutes} ${ampm}`;
}

/**
 * Format event type for display
 */
function formatEventType(eventType) {
    const typeMap = {
        'class_schedule': 'Class',
        'class': 'Class',
        'one_on_one': 'One-on-One',
        'meeting': 'Meeting',
        'communication': 'Communication',
        'planning': 'Planning',
        'special_event': 'Special Event',
        'drill': 'Drill',
        'field_trip': 'Field Trip',
        'testing': 'Testing',
        'transition': 'Transition'
    };
    return typeMap[eventType] || eventType.replace(/_/g, ' ');
}
