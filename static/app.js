// ===== State =====
let chatHistory = [];
let isLoading = false;

// ===== DOM Elements =====
const messagesEl = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const welcomeCard = document.getElementById('welcomeCard');
const welcomeExamples = document.getElementById('welcomeExamples');
const sidebarSuggestions = document.getElementById('sidebarSuggestions');
const sidebar = document.getElementById('sidebar');
const schemaModalBtn = document.getElementById('schemaModalBtn');
const schemaModalOverlay = document.getElementById('schemaModalOverlay');
const schemaModalClose = document.getElementById('schemaModalClose');
const erdTables = document.getElementById('erdTables');
const erdLines = document.getElementById('erdLines');
const reasoningToggleBtn = document.getElementById('reasoningToggleBtn');
const reasoningPanel = document.getElementById('reasoningPanel');
const reasoningPanelClose = document.getElementById('reasoningPanelClose');
const reasoningSteps = document.getElementById('reasoningSteps');
const reasoningEmpty = document.getElementById('reasoningEmpty');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const themeToggle = document.getElementById('themeToggle');

// ===== Example Questions =====
const exampleQuestions = [
    "What were the total sales by country last year?",
    "Show me the top 10 best-selling products",
    "How did revenue trend month over month in 2024?",
    "Which customer segment is most profitable?",
    "Compare marketing campaign ROI",
];

// ===== Schema data cache =====
let schemaData = null;

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    renderWelcomeExamples();
    loadSidebarSuggestions();
    prefetchSchema();
    setupEventListeners();
});

function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    }
}

function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
    });

    // Sidebar toggle (mobile)
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        sidebarOverlay.classList.toggle('active');
    });

    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    });

    // Theme toggle
    themeToggle.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (isLight) {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
        // Re-render charts with updated theme
        recolorCharts();
    });

    // Welcome tip link
    document.querySelectorAll('.example-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const q = link.getAttribute('data-question');
            if (q) askQuestion(q);
        });
    });

    // Reasoning panel
    reasoningToggleBtn.addEventListener('click', toggleReasoningPanel);
    reasoningPanelClose.addEventListener('click', closeReasoningPanel);

    // Schema modal
    schemaModalBtn.addEventListener('click', openSchemaModal);
    schemaModalClose.addEventListener('click', closeSchemaModal);
    schemaModalOverlay.addEventListener('click', (e) => {
        if (e.target === schemaModalOverlay) closeSchemaModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && schemaModalOverlay.classList.contains('open')) {
            closeSchemaModal();
        }
    });
}

// ===== Welcome Examples =====
function renderWelcomeExamples() {
    exampleQuestions.forEach(q => {
        const btn = document.createElement('button');
        btn.className = 'welcome-example-btn';
        btn.textContent = q;
        btn.addEventListener('click', () => askQuestion(q));
        welcomeExamples.appendChild(btn);
    });
}

// ===== Sidebar Suggestions =====
async function loadSidebarSuggestions() {
    try {
        const res = await fetch('/api/suggestions');
        const data = await res.json();
        data.suggestions.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-item';
            btn.textContent = q;
            btn.addEventListener('click', () => askQuestion(q));
            sidebarSuggestions.appendChild(btn);
        });
    } catch (e) {
        // Fall back to local examples
        exampleQuestions.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-item';
            btn.textContent = q;
            btn.addEventListener('click', () => askQuestion(q));
            sidebarSuggestions.appendChild(btn);
        });
    }
}

// ===== Schema Modal & ERD =====
async function prefetchSchema() {
    try {
        const res = await fetch('/api/schema');
        const data = await res.json();
        schemaData = data.tables;
    } catch (e) {
        // Will retry when modal opens
    }
}

function openSchemaModal() {
    schemaModalOverlay.classList.add('open');
    if (schemaData) {
        renderERD(schemaData);
    } else {
        erdTables.innerHTML = '<p style="color:var(--text-muted);padding:40px;text-align:center;">Loading schema...</p>';
        prefetchSchema().then(() => {
            if (schemaData) renderERD(schemaData);
            else erdTables.innerHTML = '<p style="color:var(--error);padding:40px;text-align:center;">Could not load schema.</p>';
        });
    }
}

function closeSchemaModal() {
    schemaModalOverlay.classList.remove('open');
}

// Build lookup: tableName → list of { col, refTable, refCol, direction }
// direction: 'out' = this table has FK pointing to another, 'in' = another table points here
function buildRelationMap(tables) {
    const map = {}; // tableName -> []
    tables.forEach(t => { map[t.name] = []; });

    tables.forEach(table => {
        table.columns.forEach(col => {
            if (!col.references) return;
            // references is e.g. "customers.id"
            const [refTable, refCol] = col.references.split('.');
            // Outgoing FK from this table
            if (map[table.name]) {
                map[table.name].push({
                    direction: 'out',
                    localCol: col.name,
                    refTable,
                    refCol: refCol || 'id',
                });
            }
            // Incoming FK into the referenced table
            if (map[refTable]) {
                map[refTable].push({
                    direction: 'in',
                    localCol: refCol || 'id',
                    refTable: table.name,
                    refCol: col.name,
                });
            }
        });
    });
    return map;
}

function renderERD(tables) {
    erdTables.innerHTML = '';
    erdLines.innerHTML = ''; // kept in DOM but unused

    const relMap = buildRelationMap(tables);

    tables.forEach(table => {
        const card = document.createElement('div');
        card.className = 'erd-table-card';
        card.setAttribute('data-table', table.name);

        // ── Header ──────────────────────────────────────────
        const head = document.createElement('div');
        head.className = 'erd-table-head';
        head.innerHTML = `
            <span class="erd-table-name">${table.name}</span>
            <span class="erd-table-count">${table.row_count.toLocaleString()} rows</span>
        `;
        card.appendChild(head);

        // ── Description ─────────────────────────────────────
        const desc = document.createElement('div');
        desc.className = 'erd-table-desc';
        desc.textContent = table.description;
        card.appendChild(desc);

        // ── Section label: Columns ───────────────────────────
        card.appendChild(makeSectionLabel('Columns'));

        // ── Columns ─────────────────────────────────────────
        const colsDiv = document.createElement('div');
        colsDiv.className = 'erd-columns';

        table.columns.forEach(col => {
            const isPK = col.name === 'id';
            const isFK = !!col.references;

            const row = document.createElement('div');
            row.className = 'erd-col';
            row.title = col.description || '';

            const icon = document.createElement('span');
            icon.className = 'erd-col-icon ' + (isPK ? 'pk' : isFK ? 'fk' : 'regular');
            icon.textContent = isPK ? 'PK' : isFK ? 'FK' : '';
            row.appendChild(icon);

            const nameSpan = document.createElement('span');
            nameSpan.className = 'erd-col-name';
            nameSpan.textContent = col.name;
            row.appendChild(nameSpan);

            const typeSpan = document.createElement('span');
            typeSpan.className = 'erd-col-type';
            typeSpan.textContent = col.type;
            row.appendChild(typeSpan);

            colsDiv.appendChild(row);
        });

        card.appendChild(colsDiv);

        // ── Relations section ────────────────────────────────
        const rels = relMap[table.name] || [];
        if (rels.length > 0) {
            card.appendChild(makeSectionLabel('Relations'));

            const relsDiv = document.createElement('div');
            relsDiv.className = 'erd-relations';

            rels.forEach(rel => {
                const row = document.createElement('div');
                row.className = 'erd-rel-row';

                if (rel.direction === 'out') {
                    // This table's FK points to another table
                    row.innerHTML = `
                        <span class="erd-rel-icon out" title="Foreign key out">&#x2192;</span>
                        <span class="erd-rel-text">
                            <span class="erd-rel-col">${rel.localCol}</span>
                            <span class="erd-rel-arrow">links to</span>
                            <span class="erd-rel-target">${rel.refTable}</span>
                            <span class="erd-rel-arrow">.${rel.refCol}</span>
                        </span>
                    `;
                } else {
                    // Another table's FK points into this table
                    row.innerHTML = `
                        <span class="erd-rel-icon in" title="Referenced by">&#x2190;</span>
                        <span class="erd-rel-text">
                            <span class="erd-rel-target">${rel.refTable}</span>
                            <span class="erd-rel-arrow">.${rel.refCol}</span>
                            <span class="erd-rel-arrow"> references </span>
                            <span class="erd-rel-col">${rel.localCol}</span>
                        </span>
                    `;
                }

                relsDiv.appendChild(row);
            });

            card.appendChild(relsDiv);
        }

        erdTables.appendChild(card);
    });
}

function makeSectionLabel(text) {
    const el = document.createElement('div');
    el.className = 'erd-section-label';
    el.textContent = text;
    return el;
}

// ===== Chat =====
function askQuestion(question) {
    messageInput.value = question;
    messageInput.style.height = 'auto';
    sendMessage();
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isLoading) return;

    // Hide welcome card
    if (welcomeCard) welcomeCard.style.display = 'none';

    // Close mobile sidebar
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');

    // Add user message
    addMessage('user', text);
    chatHistory.push({ role: 'user', content: text });

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Open and clear reasoning panel
    openReasoningPanel();
    clearReasoningPanel();

    // Show loading
    isLoading = true;
    sendBtn.disabled = true;
    const loadingEl = addLoading();

    // Stream state
    const state = { chart: null, queryInfo: null, reply: '', suggestions: [], error: null };
    // Pointer to the live text step DOM node for streaming updates
    let textPreviewEl = null;

    try {
        const res = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                history: chatHistory.slice(-20),
            }),
        });

        if (!res.ok) throw new Error(`Server error: ${res.status}`);

        // Parse the SSE stream line by line
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop(); // keep incomplete tail

            for (const part of parts) {
                const line = part.trim();
                if (!line.startsWith('data: ')) continue;
                let event;
                try { event = JSON.parse(line.slice(6)); } catch { continue; }
                textPreviewEl = handleStreamEvent(event, state, textPreviewEl);
            }
        }

        // Stream ended — mark text step complete
        if (textPreviewEl) {
            textPreviewEl.classList.remove('streaming');
            appendReasoningResult(textPreviewEl.parentElement, true, 'Response complete');
        }

    } catch (e) {
        state.error = e.message;
        addReasoningThinking(`Error: ${e.message}`);
    }

    loadingEl.remove();

    if (state.error && !state.reply) {
        addMessage('bot', `Sorry, something went wrong: ${state.error}. Please try again.`);
    } else if (state.reply) {
        addBotMessage({ reply: state.reply, chart: state.chart, query_info: state.queryInfo, suggestions: state.suggestions });
        chatHistory.push({ role: 'assistant', content: state.reply });
    }

    isLoading = false;
    sendBtn.disabled = false;
    messageInput.focus();
}

// ===== Stream Event Handler =====
function handleStreamEvent(event, state, textPreviewEl) {
    switch (event.type) {

        case 'reasoning':
            addReasoningThinking(event.message);
            break;

        case 'tool_call':
            if (event.tool === 'run_query') {
                addReasoningSQLStep(event.sql, event.explanation);
            } else if (event.tool === 'create_chart') {
                addReasoningChartStep(event.chart_type, event.title);
            } else if (event.tool === 'explain_schema') {
                addReasoningSchemaStep(event.scope, event.table_name);
            }
            break;

        case 'tool_result':
            if (event.tool === 'run_query') {
                finaliseReasoningSQLStep(event.row_count, event.error);
            } else if (event.tool === 'create_chart') {
                finaliseReasoningChartStep(event.chart_type, event.title);
            }
            break;

        case 'text_start':
            textPreviewEl = addReasoningTextStep();
            break;

        case 'text_delta':
            state.reply += event.text;
            if (textPreviewEl) {
                textPreviewEl.textContent = state.reply;
                textPreviewEl.scrollTop = textPreviewEl.scrollHeight;
            }
            break;

        case 'chart':
            state.chart = event.data;
            break;

        case 'query_info':
            state.queryInfo = event.data;
            break;

        case 'done':
            state.reply = event.reply || state.reply;
            state.chart = event.chart || state.chart;
            state.queryInfo = event.query_info || state.queryInfo;
            state.suggestions = event.suggestions || [];
            break;

        case 'error':
            state.error = event.message;
            addReasoningThinking(`⚠ ${event.message}`);
            break;
    }
    return textPreviewEl;
}

// ===== Reasoning Panel Controls =====
function openReasoningPanel() {
    reasoningPanel.classList.add('open');
    reasoningToggleBtn.classList.add('active');
}

function closeReasoningPanel() {
    reasoningPanel.classList.remove('open');
    reasoningToggleBtn.classList.remove('active');
}

function toggleReasoningPanel() {
    if (reasoningPanel.classList.contains('open')) {
        closeReasoningPanel();
    } else {
        openReasoningPanel();
    }
}

function clearReasoningPanel() {
    // Remove everything except the empty-state placeholder
    Array.from(reasoningSteps.children).forEach(child => {
        if (child !== reasoningEmpty) child.remove();
    });
    reasoningEmpty.style.display = 'none';
}

// ===== Reasoning Step Builders =====

function addReasoningThinking(message) {
    const el = document.createElement('div');
    el.className = 'rs-thinking';
    el.innerHTML = `<span class="rs-thinking-dot pulsing"></span><span>${escapeHtml(message)}</span>`;
    reasoningSteps.appendChild(el);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
    return el;
}

// SQL step — two-phase: header added now, result row added later
let _activeSQLStep = null;

function addReasoningSQLStep(sql, explanation) {
    const el = document.createElement('div');
    el.className = 'rs-step rs-sql-step';
    el.innerHTML = `
        <div class="rs-sql-header">
            <span class="rs-sql-icon">SQL</span>
            <span class="rs-sql-label">Running SQL query</span>
            <span class="rs-spinner"></span>
        </div>
        ${explanation ? `<div class="rs-sql-explanation">${escapeHtml(explanation)}</div>` : ''}
        <pre class="rs-sql-code">${escapeHtml(sql)}</pre>
    `;
    reasoningSteps.appendChild(el);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
    _activeSQLStep = el;
    return el;
}

function finaliseReasoningSQLStep(rowCount, isError) {
    const el = _activeSQLStep;
    if (!el) return;
    // Remove spinner
    const spinner = el.querySelector('.rs-spinner');
    if (spinner) spinner.remove();
    // Add result row
    const result = document.createElement('div');
    result.className = 'rs-sql-result ' + (isError ? 'error' : 'ok');
    result.innerHTML = isError
        ? `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Query error`
        : `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> ${rowCount.toLocaleString()} row${rowCount !== 1 ? 's' : ''} returned`;
    el.appendChild(result);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
    _activeSQLStep = null;
}

// Chart step — two-phase
let _activeChartStep = null;

function addReasoningChartStep(chartType, title) {
    const el = document.createElement('div');
    el.className = 'rs-step rs-chart-step';
    el.innerHTML = `
        <div class="rs-chart-header">
            <span class="rs-chart-icon">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="2" width="20" height="20" rx="2"/><path d="M7 17V10M12 17V7M17 17v-5"/></svg>
            </span>
            <span class="rs-chart-label">Creating ${escapeHtml(chartType)} chart</span>
            <span class="rs-spinner"></span>
        </div>
        <div class="rs-chart-detail">${escapeHtml(title)}</div>
    `;
    reasoningSteps.appendChild(el);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
    _activeChartStep = el;
    return el;
}

function finaliseReasoningChartStep(chartType, title) {
    const el = _activeChartStep;
    if (!el) return;
    const spinner = el.querySelector('.rs-spinner');
    if (spinner) spinner.remove();
    const result = document.createElement('div');
    result.className = 'rs-chart-result';
    result.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Chart ready`;
    el.appendChild(result);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
    _activeChartStep = null;
}

function addReasoningSchemaStep(scope, tableName) {
    const label = scope === 'table_detail' && tableName
        ? `Schema: ${tableName} table`
        : scope === 'relationships' ? 'Schema: relationships'
        : 'Schema: overview';
    const el = document.createElement('div');
    el.className = 'rs-step rs-schema-step';
    el.innerHTML = `
        <span class="rs-schema-icon">DB</span>
        <span class="rs-schema-label">${escapeHtml(label)}</span>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2.5" style="margin-left:auto"><polyline points="20 6 9 17 4 12"/></svg>
    `;
    reasoningSteps.appendChild(el);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
    return el;
}

function addReasoningTextStep() {
    const el = document.createElement('div');
    el.className = 'rs-step rs-text-step';
    el.innerHTML = `
        <div class="rs-text-header">
            <span class="rs-text-icon">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="13" y1="18" x2="3" y2="18"/></svg>
            </span>
            <span class="rs-text-label">Generating response</span>
        </div>
        <div class="rs-text-preview streaming"></div>
    `;
    reasoningSteps.appendChild(el);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
    // Return the preview div so caller can stream text into it
    return el.querySelector('.rs-text-preview');
}

function appendReasoningResult(stepEl, ok, message) {
    if (!stepEl) return;
    const header = stepEl.querySelector('.rs-text-header');
    if (!header) return;
    const result = document.createElement('div');
    result.style.cssText = 'display:flex;align-items:center;gap:6px;padding:5px 10px;font-size:0.74rem;border-top:1px solid var(--border);background:var(--bg-secondary);color:#22c55e;';
    result.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> ${escapeHtml(message)}`;
    stepEl.appendChild(result);
    reasoningSteps.scrollTop = reasoningSteps.scrollHeight;
}

function addMessage(role, text) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;

    div.appendChild(bubble);
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
}

function addBotMessage(data) {
    const div = document.createElement('div');
    div.className = 'message bot';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    // Text content
    const textDiv = document.createElement('div');
    textDiv.className = 'bot-text';
    textDiv.innerHTML = renderMarkdown(data.reply);
    bubble.appendChild(textDiv);

    // Chart
    if (data.chart) {
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-container';
        const chartId = 'chart-' + Date.now();
        chartDiv.id = chartId;
        bubble.appendChild(chartDiv);

        // Render after DOM update
        setTimeout(() => {
            try {
                const layout = { ...data.chart.layout };
                // Adapt to theme
                const isLight = document.documentElement.getAttribute('data-theme') === 'light';
                if (isLight) {
                    layout.font = { ...layout.font, color: '#1e293b' };
                    if (layout.xaxis) layout.xaxis.gridcolor = 'rgba(148,163,184,0.2)';
                    if (layout.yaxis) layout.yaxis.gridcolor = 'rgba(148,163,184,0.2)';
                }
                layout.autosize = true;
                layout.height = 400;

                Plotly.newPlot(chartId, data.chart.data, layout, {
                    responsive: true,
                    displayModeBar: false,
                });
            } catch (e) {
                console.error('Chart render error:', e);
            }
        }, 50);
    }

    // SQL section
    if (data.query_info && data.query_info.sql) {
        const sqlSection = document.createElement('div');
        sqlSection.className = 'sql-section';

        const toggle = document.createElement('button');
        toggle.className = 'sql-toggle';
        toggle.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg> Show SQL`;

        const content = document.createElement('div');
        content.className = 'sql-content';
        content.innerHTML = `<pre>${escapeHtml(data.query_info.sql)}</pre>`;
        if (data.query_info.row_count !== null) {
            content.innerHTML += `<div class="sql-row-count">${data.query_info.row_count} row${data.query_info.row_count !== 1 ? 's' : ''} returned</div>`;
        }
        if (data.query_info.explanation) {
            content.innerHTML += `<div class="sql-row-count">${escapeHtml(data.query_info.explanation)}</div>`;
        }

        toggle.addEventListener('click', () => {
            content.classList.toggle('open');
            toggle.innerHTML = content.classList.contains('open')
                ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg> Hide SQL`
                : `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg> Show SQL`;
        });

        sqlSection.appendChild(toggle);
        sqlSection.appendChild(content);
        bubble.appendChild(sqlSection);
    }

    // Suggestion chips
    if (data.suggestions && data.suggestions.length > 0) {
        const chips = document.createElement('div');
        chips.className = 'suggestion-chips';
        data.suggestions.forEach(s => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.textContent = s;
            chip.addEventListener('click', () => askQuestion(s));
            chips.appendChild(chip);
        });
        bubble.appendChild(chips);
    }

    div.appendChild(bubble);
    messagesEl.appendChild(div);
    scrollToBottom();
}

function addLoading() {
    const div = document.createElement('div');
    div.className = 'message bot';
    div.innerHTML = `
        <div class="message-bubble">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ===== Markdown Renderer =====
function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');

    // Tables
    html = renderMarkdownTables(html);

    // Unordered lists
    html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Numbered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>(<h[34]>)/g, '$1');
    html = html.replace(/(<\/h[34]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)<\/p>/g, '$1');
    html = html.replace(/<p>(<table>)/g, '$1');
    html = html.replace(/(<\/table>)<\/p>/g, '$1');

    return html;
}

function renderMarkdownTables(html) {
    const lines = html.split('\n');
    let result = [];
    let inTable = false;
    let tableLines = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('|') && line.endsWith('|')) {
            if (!inTable) {
                inTable = true;
                tableLines = [];
            }
            tableLines.push(line);
        } else {
            if (inTable) {
                result.push(buildTable(tableLines));
                inTable = false;
                tableLines = [];
            }
            result.push(lines[i]);
        }
    }
    if (inTable) result.push(buildTable(tableLines));

    return result.join('\n');
}

function buildTable(lines) {
    if (lines.length < 2) return lines.join('\n');

    const parseRow = line => line.split('|').slice(1, -1).map(c => c.trim());
    const headers = parseRow(lines[0]);

    // Skip separator line
    let dataStart = 1;
    if (lines[1] && lines[1].match(/^\|[\s\-:|]+\|$/)) {
        dataStart = 2;
    }

    let html = '<table><thead><tr>';
    headers.forEach(h => html += `<th>${h}</th>`);
    html += '</tr></thead><tbody>';

    for (let i = dataStart; i < lines.length; i++) {
        const cells = parseRow(lines[i]);
        html += '<tr>';
        cells.forEach(c => html += `<td>${c}</td>`);
        html += '</tr>';
    }

    html += '</tbody></table>';
    return html;
}

// ===== Helpers =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function recolorCharts() {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    document.querySelectorAll('.chart-container').forEach(el => {
        if (el.id) {
            try {
                Plotly.relayout(el.id, {
                    'font.color': isLight ? '#1e293b' : '#e2e8f0',
                    'xaxis.gridcolor': isLight ? 'rgba(148,163,184,0.2)' : 'rgba(148,163,184,0.1)',
                    'yaxis.gridcolor': isLight ? 'rgba(148,163,184,0.2)' : 'rgba(148,163,184,0.1)',
                });
            } catch (e) {
                // Chart may not exist
            }
        }
    });
}
