"""Seed script to create and populate the e-commerce SQLite database."""

import sqlite3
import random
import math
from datetime import date, timedelta
from faker import Faker

random.seed(42)
fake = Faker()
Faker.seed(42)

DB_PATH = "ecommerce.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    brand TEXT,
    unit_price REAL,
    cost_price REAL,
    stock_quantity INTEGER,
    rating REAL,
    created_at DATE
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    country TEXT,
    city TEXT,
    segment TEXT,
    registration_date DATE,
    lifetime_value REAL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date DATE,
    status TEXT,
    shipping_cost REAL,
    discount_pct REAL,
    payment_method TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER,
    unit_price REAL,
    total_price REAL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    customer_id INTEGER REFERENCES customers(id),
    rating INTEGER,
    review_text TEXT,
    review_date DATE
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY,
    name TEXT,
    channel TEXT,
    start_date DATE,
    end_date DATE,
    budget REAL,
    revenue_attributed REAL
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def seasonal_order_date() -> date:
    """Generate an order date with seasonality and YoY growth."""
    # Pick a year with growth weighting: 2023=1x, 2024=1.3x, 2025=1.6x
    year = random.choices([2023, 2024, 2025], weights=[1.0, 1.3, 1.6])[0]
    month = _pick_month()
    day = random.randint(1, 28)
    return date(year, month, day)


def _pick_month() -> int:
    """Monthly weights with Nov-Dec spike and Jan-Feb dip."""
    weights = [0.6, 0.55, 0.8, 0.85, 0.9, 0.95, 0.9, 0.85, 0.95, 1.0, 1.4, 1.5]
    return random.choices(range(1, 13), weights=weights)[0]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------
COUNTRIES_WEIGHTS = [
    ("Italy", 0.25), ("Germany", 0.15), ("France", 0.13), ("USA", 0.12),
    ("UK", 0.10), ("Spain", 0.10), ("Japan", 0.08), ("Canada", 0.04),
    ("Australia", 0.03),
]
COUNTRIES = [c for c, _ in COUNTRIES_WEIGHTS]
COUNTRY_WEIGHTS = [w for _, w in COUNTRIES_WEIGHTS]

SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SEGMENT_WEIGHTS = [0.52, 0.30, 0.18]

CITY_MAP = {
    "Italy": ["Rome", "Milan", "Naples", "Turin", "Florence"],
    "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"],
    "France": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice"],
    "USA": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
    "UK": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow"],
    "Spain": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao"],
    "Japan": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
}

CATEGORIES = [
    (1, "Electronics", "Computers, phones, gadgets, and electronic accessories"),
    (2, "Clothing", "Apparel, shoes, and fashion accessories"),
    (3, "Home & Kitchen", "Furniture, appliances, and home decor"),
    (4, "Books", "Physical and digital books across all genres"),
    (5, "Sports", "Sports equipment, outdoor gear, and fitness accessories"),
]

PRODUCTS_BY_CATEGORY = {
    1: [  # Electronics
        ("Wireless Earbuds Pro", "SoundTech", 79.99, 35.0),
        ("4K Ultra Monitor 27\"", "ViewMax", 449.99, 280.0),
        ("Mechanical Keyboard RGB", "KeyMaster", 129.99, 55.0),
        ("Smartphone X200", "TechCorp", 899.99, 520.0),
        ("Laptop UltraSlim 15", "TechCorp", 1299.99, 780.0),
        ("Bluetooth Speaker", "SoundTech", 49.99, 22.0),
        ("USB-C Hub 7-in-1", "ConnectPro", 39.99, 15.0),
        ("Wireless Mouse Ergonomic", "KeyMaster", 34.99, 14.0),
        ("Tablet Pro 11", "TechCorp", 599.99, 340.0),
        ("Smart Watch Sport", "FitGear", 249.99, 120.0),
        ("Noise Cancelling Headphones", "SoundTech", 199.99, 85.0),
        ("Portable SSD 1TB", "DataVault", 89.99, 45.0),
        ("Webcam HD 1080p", "ViewMax", 59.99, 25.0),
        ("Wireless Charger Pad", "ConnectPro", 29.99, 10.0),
        ("Gaming Controller", "PlayTech", 54.99, 24.0),
        ("E-Reader Lite", "ReadWell", 119.99, 65.0),
        ("Mini Drone Camera", "SkyView", 199.99, 95.0),
        ("Power Bank 20000mAh", "ConnectPro", 44.99, 18.0),
        ("Smart Home Hub", "HomeTech", 129.99, 60.0),
        ("Action Camera 4K", "SkyView", 179.99, 80.0),
    ],
    2: [  # Clothing
        ("Classic Denim Jacket", "UrbanStyle", 89.99, 38.0),
        ("Running Shoes Air", "SpeedStep", 119.99, 48.0),
        ("Wool Blend Sweater", "CozyWear", 69.99, 28.0),
        ("Slim Fit Chinos", "UrbanStyle", 49.99, 20.0),
        ("Waterproof Rain Jacket", "OutdoorPro", 129.99, 55.0),
        ("Cotton T-Shirt Pack (3)", "BasicWear", 24.99, 8.0),
        ("Leather Belt Premium", "ClassicCraft", 39.99, 15.0),
        ("Hiking Boots Pro", "OutdoorPro", 159.99, 70.0),
        ("Summer Dress Floral", "ElegantWear", 59.99, 22.0),
        ("Winter Parka Down", "OutdoorPro", 199.99, 85.0),
        ("Sneakers Classic White", "SpeedStep", 79.99, 32.0),
        ("Linen Shirt Casual", "UrbanStyle", 44.99, 18.0),
        ("Sports Leggings", "FitWear", 34.99, 12.0),
        ("Cashmere Scarf", "CozyWear", 59.99, 24.0),
        ("Formal Dress Shirt", "ClassicCraft", 54.99, 22.0),
        ("Canvas Backpack", "UrbanStyle", 44.99, 18.0),
        ("Polarized Sunglasses", "ShadeStyle", 69.99, 25.0),
        ("Yoga Pants Flex", "FitWear", 39.99, 14.0),
        ("Leather Wallet Slim", "ClassicCraft", 34.99, 12.0),
        ("Down Vest Lightweight", "OutdoorPro", 89.99, 38.0),
    ],
    3: [  # Home & Kitchen
        ("Air Fryer Digital 5L", "KitchenPro", 99.99, 45.0),
        ("Espresso Machine Pro", "BrewMaster", 299.99, 150.0),
        ("Robot Vacuum Smart", "CleanBot", 349.99, 180.0),
        ("Memory Foam Pillow Set", "SleepWell", 49.99, 18.0),
        ("Cast Iron Skillet 12\"", "KitchenPro", 44.99, 18.0),
        ("LED Desk Lamp Touch", "BrightHome", 39.99, 15.0),
        ("Stainless Knife Set (8pc)", "KitchenPro", 79.99, 35.0),
        ("Bamboo Cutting Board", "EcoHome", 24.99, 9.0),
        ("Stand Mixer 600W", "KitchenPro", 249.99, 120.0),
        ("Scented Candle Set (4)", "CozyHome", 29.99, 10.0),
        ("Blender High Speed", "KitchenPro", 69.99, 30.0),
        ("Throw Blanket Sherpa", "CozyHome", 34.99, 12.0),
        ("Water Filter Pitcher", "PureLife", 29.99, 12.0),
        ("Plant Pot Set Ceramic", "EcoHome", 39.99, 15.0),
        ("Toaster 4-Slice", "KitchenPro", 49.99, 22.0),
        ("Wall Art Canvas Set", "ArtDecor", 59.99, 20.0),
        ("Electric Kettle 1.7L", "BrewMaster", 34.99, 14.0),
        ("Storage Containers (10pc)", "EcoHome", 27.99, 10.0),
        ("Bath Towel Set Luxury", "CozyHome", 44.99, 16.0),
        ("Smart Thermostat", "HomeTech", 149.99, 70.0),
    ],
    4: [  # Books
        ("The Art of Data Science", "TechPress", 34.99, 12.0),
        ("Modern Italian Cooking", "FoodBooks", 29.99, 10.0),
        ("World History Atlas", "EduBooks", 49.99, 20.0),
        ("Python Programming Guide", "TechPress", 44.99, 16.0),
        ("Mindfulness & Meditation", "WellBooks", 19.99, 7.0),
        ("Space Exploration 2025", "SciBooks", 39.99, 15.0),
        ("Financial Freedom Plan", "BizBooks", 24.99, 9.0),
        ("The Great Novel Collection", "LitPress", 29.99, 11.0),
        ("Digital Marketing Mastery", "BizBooks", 34.99, 13.0),
        ("Gardening for Beginners", "GreenBooks", 22.99, 8.0),
        ("AI and the Future", "TechPress", 29.99, 11.0),
        ("Travel Europe Guide", "TravelBooks", 27.99, 10.0),
        ("Healthy Meal Prep", "FoodBooks", 24.99, 9.0),
        ("Photography Masterclass", "ArtBooks", 39.99, 15.0),
        ("Leadership Principles", "BizBooks", 27.99, 10.0),
        ("Science Fiction Anthology", "LitPress", 19.99, 7.0),
        ("Home Workout Bible", "FitBooks", 22.99, 8.0),
        ("Blockchain Explained", "TechPress", 32.99, 12.0),
        ("Children's Story Collection", "KidsBooks", 16.99, 6.0),
        ("Architecture & Design", "ArtBooks", 44.99, 18.0),
    ],
    5: [  # Sports
        ("Yoga Mat Premium", "FitGear", 29.99, 10.0),
        ("Resistance Band Set (5)", "FitGear", 24.99, 8.0),
        ("Running Watch GPS", "SpeedTech", 199.99, 90.0),
        ("Dumbbell Set Adjustable", "IronForce", 149.99, 70.0),
        ("Tennis Racket Pro", "GamePoint", 89.99, 38.0),
        ("Cycling Helmet Aero", "SpeedTech", 79.99, 35.0),
        ("Camping Tent 4-Person", "WildTrail", 199.99, 90.0),
        ("Soccer Ball Official", "GamePoint", 34.99, 14.0),
        ("Foam Roller Recovery", "FitGear", 24.99, 9.0),
        ("Ski Goggles Polarized", "SnowPeak", 69.99, 28.0),
        ("Basketball Indoor/Outdoor", "GamePoint", 29.99, 12.0),
        ("Jump Rope Speed", "FitGear", 14.99, 5.0),
        ("Trekking Poles Carbon", "WildTrail", 59.99, 25.0),
        ("Swimming Goggles Pro", "AquaSpeed", 19.99, 7.0),
        ("Boxing Gloves 12oz", "FightFit", 49.99, 20.0),
        ("Fishing Rod Combo", "CatchPro", 79.99, 35.0),
        ("Skateboard Complete", "StreetRide", 69.99, 28.0),
        ("Climbing Harness", "WildTrail", 59.99, 25.0),
        ("Golf Club Set Starter", "SwingPro", 299.99, 140.0),
        ("Surfboard Shortboard", "WaveRider", 349.99, 160.0),
    ],
}

PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer", "crypto"]
PAYMENT_WEIGHTS = [0.45, 0.30, 0.18, 0.07]

ORDER_STATUSES = ["completed", "shipped", "processing", "cancelled", "returned"]
STATUS_WEIGHTS = [0.65, 0.12, 0.08, 0.10, 0.05]

REVIEW_TEXTS_POSITIVE = [
    "Excellent product, highly recommend!",
    "Great quality for the price.",
    "Exceeded my expectations, very happy with this purchase.",
    "Fast delivery and the product is amazing.",
    "Perfect! Exactly what I was looking for.",
    "Very satisfied, would buy again.",
    "Outstanding quality and great customer service.",
    "Love it! Works perfectly.",
    "Best purchase I've made this year.",
    "Fantastic product, five stars!",
]

REVIEW_TEXTS_NEUTRAL = [
    "Decent product, does what it says.",
    "It's okay, nothing special.",
    "Good enough for the price point.",
    "Average quality, meets expectations.",
    "Works fine but nothing extraordinary.",
]

REVIEW_TEXTS_NEGATIVE = [
    "Disappointed with the quality.",
    "Not worth the price.",
    "Product arrived damaged.",
    "Below expectations, wouldn't recommend.",
    "Poor quality, returning this.",
]

CAMPAIGNS_DATA = [
    ("New Year Sale 2023", "email", "2023-01-05", "2023-01-15", 8000),
    ("Spring Collection 2023", "social_media", "2023-03-15", "2023-04-05", 12000),
    ("Easter Deals 2023", "google_ads", "2023-04-01", "2023-04-10", 6000),
    ("Summer Sale 2023", "social_media", "2023-06-15", "2023-07-15", 20000),
    ("Back to School 2023", "email", "2023-08-20", "2023-09-10", 10000),
    ("Black Friday 2023", "google_ads", "2023-11-20", "2023-11-30", 35000),
    ("Holiday Season 2023", "influencer", "2023-12-01", "2023-12-25", 25000),
    ("Valentine's Day 2024", "social_media", "2024-02-01", "2024-02-14", 9000),
    ("Spring Refresh 2024", "email", "2024-03-20", "2024-04-10", 11000),
    ("Summer Blowout 2024", "google_ads", "2024-06-20", "2024-07-20", 22000),
    ("Prime Days 2024", "social_media", "2024-07-10", "2024-07-17", 18000),
    ("Fall Fashion 2024", "influencer", "2024-09-15", "2024-10-05", 14000),
    ("Black Friday 2024", "google_ads", "2024-11-22", "2024-12-02", 40000),
    ("Cyber Monday 2024", "email", "2024-12-02", "2024-12-05", 15000),
    ("Holiday Gift Guide 2024", "influencer", "2024-12-05", "2024-12-24", 28000),
    ("New Year Kickoff 2025", "email", "2025-01-02", "2025-01-12", 10000),
    ("Spring Sale 2025", "social_media", "2025-03-10", "2025-04-01", 15000),
    ("Summer Fest 2025", "google_ads", "2025-06-15", "2025-07-15", 25000),
    ("Back to School 2025", "influencer", "2025-08-15", "2025-09-05", 13000),
    ("Black Friday 2025", "google_ads", "2025-11-21", "2025-12-01", 45000),
]


def create_schema(conn: sqlite3.Connection):
    conn.executescript(SCHEMA_SQL)


def seed_categories(conn: sqlite3.Connection):
    conn.executemany(
        "INSERT INTO categories (id, name, description) VALUES (?, ?, ?)",
        CATEGORIES,
    )


def seed_products(conn: sqlite3.Connection):
    rows = []
    pid = 1
    for cat_id, products in PRODUCTS_BY_CATEGORY.items():
        for name, brand, price, cost in products:
            rating = round(random.uniform(2.5, 5.0), 1)
            stock = random.randint(10, 500)
            created = random_date(date(2022, 6, 1), date(2023, 6, 1))
            rows.append((pid, name, cat_id, brand, price, cost, stock, rating, str(created)))
            pid += 1
    conn.executemany(
        "INSERT INTO products (id, name, category_id, brand, unit_price, cost_price, stock_quantity, rating, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    return rows  # return for later reference


def seed_customers(conn: sqlite3.Connection):
    rows = []
    emails_seen = set()
    for cid in range(1, 501):
        name = fake.name()
        # Ensure unique email
        email = fake.email()
        while email in emails_seen:
            email = fake.email()
        emails_seen.add(email)

        country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
        city = random.choice(CITY_MAP[country])
        segment = random.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
        reg_date = random_date(date(2022, 1, 1), date(2025, 6, 30))
        rows.append((cid, name, email, country, city, segment, str(reg_date), 0.0))

    conn.executemany(
        "INSERT INTO customers (id, name, email, country, city, segment, registration_date, lifetime_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    return rows


def seed_orders_and_items(conn: sqlite3.Connection, customers, products):
    """Generate ~5000 orders with ~12000 order items."""
    product_map = {p[0]: p for p in products}  # id -> product tuple
    product_ids = list(product_map.keys())

    # Weight products by rating (higher rated sell more)
    product_ratings = [product_map[pid][7] for pid in product_ids]
    rating_min = min(product_ratings)
    product_weights = [r - rating_min + 1.0 for r in product_ratings]

    customer_ids = [c[0] for c in customers]
    customer_segments = {c[0]: c[5] for c in customers}

    # Make some customers "returning" (buy more)
    returning_customers = random.sample(customer_ids, k=150)
    customer_order_weights = []
    for cid in customer_ids:
        w = 1.0
        if cid in returning_customers:
            w = 3.0
        if customer_segments[cid] == "Corporate":
            w *= 1.5
        customer_order_weights.append(w)

    order_rows = []
    item_rows = []
    oid = 1
    iid = 1
    customer_spending = {c[0]: 0.0 for c in customers}

    target_orders = 5000
    target_items_per_order = 2.4

    for _ in range(target_orders):
        cust_id = random.choices(customer_ids, weights=customer_order_weights)[0]
        order_date = seasonal_order_date()
        status = random.choices(ORDER_STATUSES, weights=STATUS_WEIGHTS)[0]
        shipping = round(random.choice([0.0, 4.99, 7.99, 9.99, 12.99]), 2)
        discount = round(random.choice([0, 0, 0, 5, 10, 10, 15, 20, 25, 30]), 1)
        payment = random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS)[0]

        order_rows.append((oid, cust_id, str(order_date), status, shipping, discount, payment))

        # Number of items: corporate orders tend to have more
        avg_items = 3.2 if customer_segments[cust_id] == "Corporate" else 2.2
        n_items = max(1, int(random.expovariate(1.0 / avg_items)))
        n_items = min(n_items, 8)

        order_product_ids = random.choices(product_ids, weights=product_weights, k=n_items)
        # Deduplicate to avoid same product twice in one order
        seen = set()
        unique_products = []
        for pid in order_product_ids:
            if pid not in seen:
                seen.add(pid)
                unique_products.append(pid)

        for pid in unique_products:
            qty = random.choices([1, 1, 1, 2, 2, 3, 4, 5], weights=[40, 40, 40, 20, 20, 8, 4, 2])[0]
            base_price = product_map[pid][4]
            # Slight price variation (± 5%) to simulate historical pricing
            unit_price = round(base_price * random.uniform(0.95, 1.05), 2)
            total = round(qty * unit_price * (1 - discount / 100), 2)
            item_rows.append((iid, oid, pid, qty, unit_price, total))
            if status in ("completed", "shipped"):
                customer_spending[cust_id] += total
            iid += 1

        oid += 1

    conn.executemany(
        "INSERT INTO orders (id, customer_id, order_date, status, shipping_cost, discount_pct, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
        order_rows,
    )
    conn.executemany(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?, ?)",
        item_rows,
    )

    # Update lifetime values
    for cid, ltv in customer_spending.items():
        conn.execute("UPDATE customers SET lifetime_value = ? WHERE id = ?", (round(ltv, 2), cid))

    return order_rows, item_rows


def seed_reviews(conn: sqlite3.Connection, order_items, customers):
    """Generate ~2000 reviews from customers who bought the product."""
    # Build mapping: customer_id -> set of product_ids they bought
    # First need order->customer mapping
    customer_products = {}
    order_customer = {}

    cursor = conn.execute("SELECT id, customer_id FROM orders WHERE status IN ('completed', 'shipped')")
    for row in cursor:
        order_customer[row[0]] = row[1]

    for item in order_items:
        oid = item[1]
        pid = item[2]
        cid = order_customer.get(oid)
        if cid:
            customer_products.setdefault(cid, set()).add(pid)

    # Flatten to list of (customer_id, product_id) pairs
    pairs = []
    for cid, pids in customer_products.items():
        for pid in pids:
            pairs.append((cid, pid))

    random.shuffle(pairs)
    selected = pairs[:2000]

    rows = []
    rid = 1
    for cid, pid in selected:
        # Higher-rated products tend to get higher review ratings
        cursor = conn.execute("SELECT rating FROM products WHERE id = ?", (pid,))
        prod_rating = cursor.fetchone()[0]
        # Review rating influenced by product rating
        base = max(1, min(5, int(prod_rating + random.gauss(0, 1))))
        rating = max(1, min(5, base))

        if rating >= 4:
            text = random.choice(REVIEW_TEXTS_POSITIVE)
        elif rating == 3:
            text = random.choice(REVIEW_TEXTS_NEUTRAL)
        else:
            text = random.choice(REVIEW_TEXTS_NEGATIVE)

        review_date = random_date(date(2023, 2, 1), date(2025, 12, 31))
        rows.append((rid, pid, cid, rating, text, str(review_date)))
        rid += 1

    conn.executemany(
        "INSERT INTO reviews (id, product_id, customer_id, rating, review_text, review_date) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_campaigns(conn: sqlite3.Connection):
    rows = []
    for i, (name, channel, start, end, budget) in enumerate(CAMPAIGNS_DATA, 1):
        # Revenue attributed is 1.5x to 5x budget for realistic ROI
        roi_mult = random.uniform(1.5, 5.0)
        revenue = round(budget * roi_mult, 2)
        rows.append((i, name, channel, start, end, budget, revenue))

    conn.executemany(
        "INSERT INTO campaigns (id, name, channel, start_date, end_date, budget, revenue_attributed) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def main():
    import os
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    print("Creating schema...")
    create_schema(conn)

    print("Seeding categories...")
    seed_categories(conn)

    print("Seeding products...")
    products = seed_products(conn)

    print("Seeding customers...")
    customers = seed_customers(conn)

    conn.commit()

    print("Seeding orders and order items...")
    orders, items = seed_orders_and_items(conn, customers, products)
    conn.commit()

    print("Seeding reviews...")
    seed_reviews(conn, items, customers)

    print("Seeding campaigns...")
    seed_campaigns(conn)
    conn.commit()

    # Print summary
    tables = ["categories", "products", "customers", "orders", "order_items", "reviews", "campaigns"]
    print("\n--- Database Summary ---")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} rows")

    conn.close()
    print(f"\nDatabase created: {DB_PATH}")


if __name__ == "__main__":
    main()
