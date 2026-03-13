"""Claude API client with tool-use loop for NL-to-SQL chatbot."""

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from database import (
    execute_query,
    get_schema_overview_text,
    get_table_detail,
    get_relationships_text,
)
from chart_service import build_plotly_config

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are DataChat, a friendly and knowledgeable e-commerce analytics assistant. You help users explore and understand an e-commerce database by translating their natural language questions into SQL queries and presenting results with clear explanations and visualizations.

## Database Schema

### customers (≈500 rows)
Customer accounts with demographic and value data.
- id (INTEGER PK) — Unique customer identifier
- name (TEXT) — Customer full name
- email (TEXT UNIQUE) — Email address
- country (TEXT) — Country: Italy, Germany, France, USA, UK, Spain, Japan, Canada, Australia
- city (TEXT) — City of residence
- segment (TEXT) — Business segment: 'Consumer', 'Corporate', 'Home Office'
- registration_date (DATE) — Registration date
- lifetime_value (REAL) — Total spending on completed/shipped orders

### categories (5 rows)
Product category definitions.
- id (INTEGER PK) — Category identifier
- name (TEXT) — Category: Electronics, Clothing, Home & Kitchen, Books, Sports
- description (TEXT) — Category description

### products (≈100 rows)
Product catalog with pricing, cost, and ratings.
- id (INTEGER PK) — Product identifier
- name (TEXT) — Product name
- category_id (INTEGER FK → categories.id) — Category link
- brand (TEXT) — Brand name
- unit_price (REAL) — Current retail price
- cost_price (REAL) — Business cost (for margin calculations: margin = unit_price - cost_price)
- stock_quantity (INTEGER) — Current inventory
- rating (REAL) — Average rating 1.0–5.0
- created_at (DATE) — Date added to catalog

### orders (≈5000 rows)
Customer orders spanning 2023-01-01 to 2025-12-31 (3 years).
- id (INTEGER PK) — Order identifier
- customer_id (INTEGER FK → customers.id) — Customer link
- order_date (DATE) — Order date
- status (TEXT) — 'completed', 'shipped', 'processing', 'cancelled', 'returned'
- shipping_cost (REAL) — Shipping fee
- discount_pct (REAL) — Discount percentage 0–30
- payment_method (TEXT) — 'credit_card', 'paypal', 'bank_transfer', 'crypto'

### order_items (≈12000 rows)
Individual line items within each order.
- id (INTEGER PK) — Line item identifier
- order_id (INTEGER FK → orders.id) — Order link
- product_id (INTEGER FK → products.id) — Product link
- quantity (INTEGER) — Units ordered
- unit_price (REAL) — Price per unit at time of sale
- total_price (REAL) — Line total: quantity × unit_price × (1 - discount/100)

### reviews (≈2000 rows)
Product reviews by verified purchasers.
- id (INTEGER PK) — Review identifier
- product_id (INTEGER FK → products.id) — Product link
- customer_id (INTEGER FK → customers.id) — Reviewer link
- rating (INTEGER) — Star rating 1–5
- review_text (TEXT) — Written review
- review_date (DATE) — Review date

### campaigns (20 rows)
Marketing campaigns with budget and ROI data.
- id (INTEGER PK) — Campaign identifier
- name (TEXT) — Campaign name (e.g., 'Black Friday 2024')
- channel (TEXT) — 'email', 'social_media', 'google_ads', 'influencer'
- start_date (DATE) — Start date
- end_date (DATE) — End date
- budget (REAL) — Campaign budget in dollars
- revenue_attributed (REAL) — Revenue attributed to this campaign

## Relationships
- orders.customer_id → customers.id
- order_items.order_id → orders.id
- order_items.product_id → products.id
- products.category_id → categories.id
- reviews.product_id → products.id
- reviews.customer_id → customers.id

## Data Summary
- Date range: 2023-01-01 to 2025-12-31 (3 years)
- Growth trend: orders increase year-over-year
- Seasonality: Nov–Dec spikes, Jan–Feb dips
- Countries: Italy (largest), Germany, France, USA, UK, Spain, Japan, Canada, Australia
- Segments: Consumer (52%), Corporate (30%), Home Office (18%)
- Categories: Electronics, Clothing, Home & Kitchen, Books, Sports
- Payment methods: credit_card (45%), paypal (30%), bank_transfer (18%), crypto (7%)

## SQL Rules
1. SQLite dialect ONLY.
2. Always use explicit JOINs with aliases (never implicit joins).
3. Always alias tables (e.g., `orders o`, `customers c`).
4. LIMIT results to 1000 rows max.
5. Use DATE() functions for date filtering.
6. **SELECT statements ONLY** — never DELETE, UPDATE, INSERT, DROP, ALTER, or any DDL/DML.
7. Use ROUND() for monetary values.
8. For revenue calculations, use SUM(oi.total_price) from order_items.
9. For profit/margin, use (unit_price - cost_price) from products table.
10. Filter by status IN ('completed', 'shipped') for actual revenue (exclude cancelled/returned).

## Behavioral Rules
1. If the user asks about the data model, available data, or what they can ask → use the **explain_schema** tool.
2. If the user asks a data question → use **run_query** tool, then **create_chart** if a visual would help.
3. If the question is ambiguous → ask a clarifying question instead of guessing.
4. After showing data, always explain what you found in plain, conversational language.
5. Be proactive: suggest follow-up analyses the user might find interesting.
6. When showing numbers, format them nicely (e.g., $1,234.56 not 1234.56789).

## Chart Guidelines
- **Bar chart**: comparisons, rankings, top-N lists
- **Line chart**: time series, trends over months/quarters/years
- **Pie/donut**: composition breakdowns (max 7 slices; group small ones as "Other")
- **Scatter**: correlations between two numeric variables
- **Horizontal bar (hbar)**: when labels are long text
- **Area chart**: cumulative trends or stacked time series
- Always include a clear title and axis labels.
- Use consistent, readable formatting.
"""

TOOLS = [
    {
        "name": "run_query",
        "description": "Execute a read-only SQL query against the e-commerce SQLite database and return results. Use this to answer any data question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A SELECT SQL query (SQLite dialect). No DDL or DML allowed.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of what this query does, for the user.",
                },
            },
            "required": ["sql", "explanation"],
        },
    },
    {
        "name": "create_chart",
        "description": "Generate a Plotly chart configuration to visualize data. Use after run_query when a visual would help the user understand the results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "hbar", "area", "funnel"],
                    "description": "Type of chart to create",
                },
                "title": {"type": "string", "description": "Chart title"},
                "x_label": {"type": "string"},
                "y_label": {"type": "string"},
                "data": {
                    "type": "object",
                    "description": "Data to plot. Keys are series names, values are objects with 'x' and 'y' arrays. For pie charts, use 'labels' and 'values' arrays.",
                },
            },
            "required": ["chart_type", "title", "data"],
        },
    },
    {
        "name": "explain_schema",
        "description": "Show the user information about the database structure, tables, columns, and relationships. Use when the user asks what data is available, what they can ask about, or needs help understanding the data model.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["overview", "table_detail", "relationships"],
                    "description": "What to explain: 'overview' for all tables summary, 'table_detail' for a specific table, 'relationships' for how tables connect.",
                },
                "table_name": {
                    "type": "string",
                    "description": "Specific table name (only needed for table_detail scope)",
                },
            },
            "required": ["scope"],
        },
    },
]


def _handle_tool_call(tool_name: str, tool_input: dict) -> tuple[str, dict | None, dict | None]:
    """
    Execute a tool call and return (result_text, chart_config, query_info).
    """
    chart_config = None
    query_info = None

    if tool_name == "run_query":
        sql = tool_input.get("sql", "")
        explanation = tool_input.get("explanation", "")
        rows, columns, error = execute_query(sql)
        if error:
            result_text = f"Query error: {error}"
            query_info = {"sql": sql, "explanation": explanation, "row_count": 0}
        else:
            # Format results as a readable table for Claude
            if not rows:
                result_text = "Query returned 0 rows."
            else:
                # Show as JSON-like structure for Claude to interpret
                import json
                result_text = json.dumps(rows[:100], default=str)
                if len(rows) > 100:
                    result_text += f"\n... (showing 100 of {len(rows)} rows)"
            query_info = {"sql": sql, "explanation": explanation, "row_count": len(rows)}

    elif tool_name == "create_chart":
        chart_config = build_plotly_config(tool_input)
        result_text = "Chart created successfully."

    elif tool_name == "explain_schema":
        scope = tool_input.get("scope", "overview")
        if scope == "overview":
            result_text = get_schema_overview_text()
        elif scope == "table_detail":
            table_name = tool_input.get("table_name", "")
            detail = get_table_detail(table_name)
            if detail:
                lines = [f"## {detail['name']} ({detail['row_count']} rows)", detail["description"], ""]
                lines.append("| Column | Type | Description |")
                lines.append("|--------|------|-------------|")
                for c in detail["columns"]:
                    lines.append(f"| {c['name']} | {c['type']} | {c['description']} |")
                result_text = "\n".join(lines)
            else:
                result_text = f"Table '{table_name}' not found."
        elif scope == "relationships":
            result_text = get_relationships_text()
        else:
            result_text = get_schema_overview_text()
    else:
        result_text = f"Unknown tool: {tool_name}"

    return result_text, chart_config, query_info


def chat(user_message: str, history: list[dict]) -> dict:
    """
    Process a user message through the Claude API with tool-use loop.
    Returns dict with reply, chart, query_info, suggestions.
    """
    # Build messages from history
    messages = []
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    chart_config = None
    query_info = None

    # Tool-use loop
    max_iterations = 10
    for _ in range(max_iterations):
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Check if there are tool use blocks
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Final response — extract text
            text_parts = [b.text for b in response.content if b.type == "text"]
            reply = "\n".join(text_parts) if text_parts else "I couldn't generate a response."
            break

        # Process tool calls
        # Add assistant message with all content blocks
        messages.append({"role": "assistant", "content": response.content})

        # Build tool results
        tool_results = []
        for tool_block in tool_use_blocks:
            result_text, tc, qi = _handle_tool_call(tool_block.name, tool_block.input)
            if tc:
                chart_config = tc
            if qi:
                query_info = qi
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_results})
    else:
        reply = "I reached the maximum number of processing steps. Please try rephrasing your question."

    # Extract follow-up suggestions from the reply
    suggestions = _extract_suggestions(reply)

    return {
        "reply": reply,
        "chart": chart_config,
        "query_info": query_info,
        "suggestions": suggestions,
    }


def _extract_suggestions(reply: str) -> list[str]:
    """Generate contextual follow-up suggestions based on the reply content."""
    # Default suggestions if we can't extract specific ones
    defaults = [
        "Show me revenue by category",
        "What are the top 10 customers by spending?",
        "How did sales trend month over month?",
    ]
    return defaults
