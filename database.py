"""Database connection, query execution, and schema introspection."""

import sqlite3
import threading
import re
from config import DATABASE_PATH, QUERY_TIMEOUT_SECONDS, MAX_QUERY_ROWS

# Thread-local storage for connections (SQLite connections aren't thread-safe)
_local = threading.local()

# Schema metadata for the explorer and system prompt
TABLE_DESCRIPTIONS = {
    "customers": "Customer accounts with demographic and value data",
    "categories": "Product category definitions",
    "products": "Product catalog with pricing, cost, and ratings",
    "orders": "Customer orders with status and payment details",
    "order_items": "Individual line items within each order",
    "reviews": "Product reviews written by customers",
    "campaigns": "Marketing campaigns with budget and attributed revenue",
}

COLUMN_DESCRIPTIONS = {
    "customers": {
        "id": "Unique customer identifier",
        "name": "Customer full name",
        "email": "Unique email address",
        "country": "Country of residence (Italy, Germany, France, USA, UK, Spain, Japan, Canada, Australia)",
        "city": "City of residence",
        "segment": "Business segment: Consumer, Corporate, or Home Office",
        "registration_date": "Date the customer registered",
        "lifetime_value": "Total spending by this customer on completed/shipped orders",
    },
    "categories": {
        "id": "Unique category identifier",
        "name": "Category name (Electronics, Clothing, Home & Kitchen, Books, Sports)",
        "description": "Description of the category",
    },
    "products": {
        "id": "Unique product identifier",
        "name": "Product name",
        "category_id": "Links to categories.id",
        "brand": "Product brand name",
        "unit_price": "Current retail price",
        "cost_price": "Cost to the business (for margin calculations)",
        "stock_quantity": "Current inventory level",
        "rating": "Average product rating (1.0 to 5.0)",
        "created_at": "Date product was added to catalog",
    },
    "orders": {
        "id": "Unique order identifier",
        "customer_id": "Links to customers.id",
        "order_date": "Date the order was placed (ranges 2023-01-01 to 2025-12-31)",
        "status": "Order status: completed, shipped, processing, cancelled, or returned",
        "shipping_cost": "Shipping fee charged",
        "discount_pct": "Discount percentage applied (0 to 30)",
        "payment_method": "Payment type: credit_card, paypal, bank_transfer, or crypto",
    },
    "order_items": {
        "id": "Unique line item identifier",
        "order_id": "Links to orders.id",
        "product_id": "Links to products.id",
        "quantity": "Number of units ordered",
        "unit_price": "Price per unit at time of sale (may differ from current price)",
        "total_price": "Line total: quantity × unit_price × (1 - discount/100)",
    },
    "reviews": {
        "id": "Unique review identifier",
        "product_id": "Links to products.id",
        "customer_id": "Links to customers.id",
        "rating": "Review rating (1 to 5 stars)",
        "review_text": "Written review content",
        "review_date": "Date the review was posted",
    },
    "campaigns": {
        "id": "Unique campaign identifier",
        "name": "Campaign name (e.g., 'Black Friday 2024')",
        "channel": "Marketing channel: email, social_media, google_ads, or influencer",
        "start_date": "Campaign start date",
        "end_date": "Campaign end date",
        "budget": "Campaign budget in dollars",
        "revenue_attributed": "Revenue attributed to this campaign",
    },
}


def get_connection() -> sqlite3.Connection:
    """Get a thread-local read-only SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(
            f"file:{DATABASE_PATH}?mode=ro",
            uri=True,
            check_same_thread=False,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def validate_query(sql: str) -> tuple[bool, str]:
    """Validate that a SQL query is a safe SELECT statement."""
    cleaned = sql.strip().rstrip(";").strip()
    # Must start with SELECT or WITH (for CTEs)
    if not re.match(r"^\s*(SELECT|WITH)\s", cleaned, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    # Block dangerous keywords
    blocked = r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|GRANT|REVOKE|ATTACH|DETACH|PRAGMA)\b"
    if re.search(blocked, cleaned, re.IGNORECASE):
        return False, "DDL and DML statements are not allowed. Only SELECT queries are permitted."

    return True, ""


def execute_query(sql: str) -> tuple[list[dict], list[str], str | None]:
    """
    Execute a validated SELECT query.
    Returns (rows_as_dicts, column_names, error_message).
    """
    valid, err = validate_query(sql)
    if not valid:
        return [], [], err

    conn = get_connection()
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(MAX_QUERY_ROWS)
        result = [dict(zip(columns, row)) for row in rows]
        return result, columns, None
    except sqlite3.OperationalError as e:
        return [], [], f"SQL error: {e}"
    except Exception as e:
        return [], [], f"Query execution failed: {e}"


def get_schema_info() -> list[dict]:
    """Return full schema metadata for all tables."""
    conn = get_connection()
    tables = []

    for table_name in TABLE_DESCRIPTIONS:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in cursor:
            col_name = row[1]
            col_type = row[2]
            not_null = bool(row[3])
            col_desc = COLUMN_DESCRIPTIONS.get(table_name, {}).get(col_name, "")
            ref = None
            if "Links to" in col_desc:
                ref = col_desc.split("Links to ")[1]
                col_desc = f"Foreign key → {ref}"
            columns.append({
                "name": col_name,
                "type": col_type,
                "description": col_desc,
                "nullable": not not_null,
                "references": ref,
            })

        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        tables.append({
            "name": table_name,
            "description": TABLE_DESCRIPTIONS[table_name],
            "columns": columns,
            "row_count": count,
        })

    return tables


def get_table_detail(table_name: str) -> dict | None:
    """Get detailed info about a specific table."""
    tables = get_schema_info()
    for t in tables:
        if t["name"] == table_name:
            return t
    return None


def get_schema_overview_text() -> str:
    """Generate a text summary of the schema for the explain_schema tool."""
    tables = get_schema_info()
    lines = ["## E-Commerce Database Schema\n"]
    for t in tables:
        lines.append(f"### {t['name']} ({t['row_count']} rows)")
        lines.append(f"{t['description']}\n")
        lines.append("| Column | Type | Description |")
        lines.append("|--------|------|-------------|")
        for c in t["columns"]:
            lines.append(f"| {c['name']} | {c['type']} | {c['description']} |")
        lines.append("")
    return "\n".join(lines)


def get_relationships_text() -> str:
    """Generate text describing table relationships."""
    return """## Table Relationships

- **orders.customer_id** → customers.id (each order belongs to one customer)
- **order_items.order_id** → orders.id (each line item belongs to one order)
- **order_items.product_id** → products.id (each line item references a product)
- **products.category_id** → categories.id (each product belongs to one category)
- **reviews.product_id** → products.id (each review is about one product)
- **reviews.customer_id** → customers.id (each review is written by one customer)

### Common Join Patterns
- Orders + Customers: `orders o JOIN customers c ON o.customer_id = c.id`
- Orders + Items + Products: `order_items oi JOIN orders o ON oi.order_id = o.id JOIN products p ON oi.product_id = p.id`
- Products + Categories: `products p JOIN categories cat ON p.category_id = cat.id`
- Revenue by Product: SUM(order_items.total_price) grouped by product
- Revenue by Category: JOIN products → categories, SUM total_price
"""
