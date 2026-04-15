# Atlas — Chart your data

*Powered by Avvale*

A full-stack data chatbot that lets users ask natural language questions about an e-commerce database and receive SQL-powered answers with auto-generated interactive charts.

**Stack:** Python, FastAPI, SQLite, Plotly, Anthropic Claude API, vanilla HTML/CSS/JS

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Seed the database:**
   ```bash
   python seed_database.py
   ```
   This creates `ecommerce.db` with ~5000 orders, ~500 customers, ~100 products, and more.

3. **Configure your API key:**
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
   Or copy `.env.example` to `.env` and fill in your key.

4. **Run the app:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

5. **Open in browser:**
   [http://localhost:8000](http://localhost:8000)

## Features

- **Natural language queries** — Ask questions in plain English, get SQL-powered answers
- **Interactive charts** — Auto-generated Plotly visualizations (bar, line, pie, scatter, etc.)
- **Schema explorer** — Browse the data model in the sidebar
- **Suggested questions** — Clickable examples to get started quickly
- **Dark/light mode** — Toggle between themes
- **SQL transparency** — Collapsible SQL viewer shows exactly what was executed
- **Safe by design** — Read-only queries, SQL injection prevention, query timeout

## Database Schema

| Table | Rows | Description |
|-------|------|-------------|
| customers | ~500 | Customer accounts across 9 countries |
| categories | 5 | Product categories |
| products | 100 | Product catalog with pricing and ratings |
| orders | ~5000 | Orders from 2023–2025 with seasonality |
| order_items | ~12000 | Individual line items per order |
| reviews | ~2000 | Verified purchase reviews |
| campaigns | 20 | Marketing campaigns with ROI data |

## Example Questions

- "What were the total sales by country last year?"
- "Show me the top 10 best-selling products"
- "How did revenue trend month over month in 2024?"
- "Which customer segment is most profitable?"
- "Compare marketing campaign ROI"
- "What data do you have?"
