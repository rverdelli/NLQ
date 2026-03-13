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

// Relationships definition for drawing lines
const RELATIONSHIPS = [
    { from: 'orders', fromCol: 'customer_id', to: 'customers', toCol: 'id' },
    { from: 'order_items', fromCol: 'order_id', to: 'orders', toCol: 'id' },
    { from: 'order_items', fromCol: 'product_id', to: 'products', toCol: 'id' },
    { from: 'products', fromCol: 'category_id', to: 'categories', toCol: 'id' },
    { from: 'reviews', fromCol: 'product_id', to: 'products', toCol: 'id' },
    { from: 'reviews', fromCol: 'customer_id', to: 'customers', toCol: 'id' },
];

function renderERD(tables) {
    erdTables.innerHTML = '';
    erdLines.innerHTML = '';

    // Render table cards
    tables.forEach(table => {
        const card = document.createElement('div');
        card.className = 'erd-table-card';
        card.setAttribute('data-table', table.name);

        // Header
        const head = document.createElement('div');
        head.className = 'erd-table-head';
        head.innerHTML = `
            <span class="erd-table-name">${table.name}</span>
            <span class="erd-table-count">${table.row_count.toLocaleString()} rows</span>
        `;
        card.appendChild(head);

        // Description
        const desc = document.createElement('div');
        desc.className = 'erd-table-desc';
        desc.textContent = table.description;
        card.appendChild(desc);

        // Columns
        const colsDiv = document.createElement('div');
        colsDiv.className = 'erd-columns';

        table.columns.forEach(col => {
            const isPK = col.name === 'id';
            const isFK = !!col.references;

            const row = document.createElement('div');
            row.className = 'erd-col';
            row.setAttribute('data-table', table.name);
            row.setAttribute('data-col', col.name);

            // Icon
            const icon = document.createElement('span');
            icon.className = 'erd-col-icon ' + (isPK ? 'pk' : isFK ? 'fk' : 'regular');
            icon.textContent = isPK ? 'PK' : isFK ? 'FK' : '';
            row.appendChild(icon);

            // Name
            const nameSpan = document.createElement('span');
            nameSpan.className = 'erd-col-name';
            nameSpan.textContent = col.name;
            row.appendChild(nameSpan);

            // Type
            const typeSpan = document.createElement('span');
            typeSpan.className = 'erd-col-type';
            typeSpan.textContent = col.type;
            row.appendChild(typeSpan);

            // FK reference
            if (isFK) {
                const refSpan = document.createElement('span');
                refSpan.className = 'erd-col-ref';
                refSpan.textContent = '\u2192 ' + col.references;
                refSpan.title = 'Foreign key to ' + col.references;
                row.appendChild(refSpan);
            }

            // Tooltip with description
            if (col.description) {
                row.title = col.description;
            }

            colsDiv.appendChild(row);
        });

        card.appendChild(colsDiv);
        erdTables.appendChild(card);
    });

    // Draw relationship lines after layout settles
    requestAnimationFrame(() => {
        requestAnimationFrame(() => drawRelationshipLines());
    });

    // Redraw on resize
    const resizeObserver = new ResizeObserver(() => drawRelationshipLines());
    resizeObserver.observe(erdTables);
}

function drawRelationshipLines() {
    erdLines.innerHTML = '';
    const canvas = document.getElementById('erdCanvas');
    if (!canvas) return;
    const canvasRect = canvas.getBoundingClientRect();

    // Size the SVG to fill the canvas
    erdLines.setAttribute('width', canvas.scrollWidth);
    erdLines.setAttribute('height', canvas.scrollHeight);
    erdLines.style.width = canvas.scrollWidth + 'px';
    erdLines.style.height = canvas.scrollHeight + 'px';

    RELATIONSHIPS.forEach((rel, idx) => {
        const fromCard = erdTables.querySelector(`[data-table="${rel.from}"]`);
        const toCard = erdTables.querySelector(`[data-table="${rel.to}"]`);
        if (!fromCard || !toCard) return;

        // Find the FK column row in the source card
        const fromRow = fromCard.querySelector(`[data-col="${rel.fromCol}"]`);
        // Find the PK column row in the target card
        const toRow = toCard.querySelector(`[data-col="${rel.toCol}"]`);
        if (!fromRow || !toRow) return;

        const fromRect = fromRow.getBoundingClientRect();
        const toRect = toRow.getBoundingClientRect();

        // Calculate positions relative to the canvas
        const fromY = fromRect.top + fromRect.height / 2 - canvasRect.top + canvas.scrollTop;
        const toY = toRect.top + toRect.height / 2 - canvasRect.top + canvas.scrollTop;

        const fromCardRect = fromCard.getBoundingClientRect();
        const toCardRect = toCard.getBoundingClientRect();

        // Determine which side to connect from/to
        let fromX, toX;
        const fromCenterX = fromCardRect.left + fromCardRect.width / 2 - canvasRect.left;
        const toCenterX = toCardRect.left + toCardRect.width / 2 - canvasRect.left;

        if (fromCenterX < toCenterX) {
            // Source is to the left of target
            fromX = fromCardRect.right - canvasRect.left;
            toX = toCardRect.left - canvasRect.left;
        } else if (fromCenterX > toCenterX) {
            // Source is to the right of target
            fromX = fromCardRect.left - canvasRect.left;
            toX = toCardRect.right - canvasRect.left;
        } else {
            // Same column — connect via the right side with a curve
            fromX = fromCardRect.right - canvasRect.left;
            toX = toCardRect.right - canvasRect.left;
        }

        // Draw a curved path
        const midX = (fromX + toX) / 2;
        const controlOffset = Math.max(40, Math.abs(fromX - toX) * 0.3);

        let path;
        if (fromCenterX === toCenterX) {
            // Same column — curve out to the right
            const bulge = 50;
            path = `M ${fromX} ${fromY} C ${fromX + bulge} ${fromY}, ${toX + bulge} ${toY}, ${toX} ${toY}`;
        } else {
            path = `M ${fromX} ${fromY} C ${fromX + (toX > fromX ? controlOffset : -controlOffset)} ${fromY}, ${toX + (toX > fromX ? -controlOffset : controlOffset)} ${toY}, ${toX} ${toY}`;
        }

        const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        pathEl.setAttribute('d', path);
        pathEl.setAttribute('class', 'erd-rel-line');
        erdLines.appendChild(pathEl);

        // Add dots at endpoints
        [{ x: fromX, y: fromY }, { x: toX, y: toY }].forEach(pt => {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', pt.x);
            circle.setAttribute('cy', pt.y);
            circle.setAttribute('r', 4);
            circle.setAttribute('class', 'erd-rel-dot');
            erdLines.appendChild(circle);
        });
    });
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

    // Hide welcome
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

    // Show loading
    isLoading = true;
    sendBtn.disabled = true;
    const loadingEl = addLoading();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                history: chatHistory.slice(-20), // last 20 messages for context
            }),
        });

        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }

        const data = await res.json();

        // Remove loading
        loadingEl.remove();

        // Add bot message
        addBotMessage(data);
        chatHistory.push({ role: 'assistant', content: data.reply });

    } catch (e) {
        loadingEl.remove();
        addMessage('bot', `Sorry, something went wrong: ${e.message}. Please try again.`);
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
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
