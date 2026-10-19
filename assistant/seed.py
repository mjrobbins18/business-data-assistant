"""Generate the sample database for a fictional bakery. Deterministic: same seed, same data."""
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

FIRST = "Ava Ben Cara Dev Eli Fay Gus Hana Ivan Jo Kai Lena Milo Nia Owen Pia Quinn Rosa Sam Tess Uma Vik Wren Yara Zane".split()
LAST = "Adler Brooks Chen Diaz Ellis Ford Gray Hughes Ito Jensen Kaur Lopez Moss Nolan Ortiz Patel Quist Reyes Shaw Tran Usman Vega Wolfe Young Zhou".split()
CITIES = ["Portland", "Beaverton", "Gresham", "Lake Oswego", "Tigard", "Vancouver"]
PRODUCTS = [  # name, category, price_cents, cost_cents
    ("Sourdough loaf", "Bread", 900, 260), ("Rye loaf", "Bread", 950, 280), ("Baguette", "Bread", 450, 110),
    ("Seeded wheat", "Bread", 850, 250), ("Croissant", "Pastry", 425, 120), ("Pain au chocolat", "Pastry", 475, 140),
    ("Morning bun", "Pastry", 450, 130), ("Kouign-amann", "Pastry", 525, 160), ("Cardamom knot", "Pastry", 500, 150),
    ("Drip coffee", "Coffee", 325, 45), ("Latte", "Coffee", 525, 95), ("Cold brew", "Coffee", 475, 70),
    ("Quiche slice", "Savory", 750, 260), ("Ham & gruyère", "Savory", 1050, 380), ("Tomato toast", "Savory", 950, 300),
    ("Whole pie", "Special order", 3800, 1300), ("Birthday cake", "Special order", 5200, 1700), ("Bread subscription (month)", "Subscription", 3200, 1000),
]
CAFES = ["Fernwood Café", "Parkside Coffee", "The Corner Grocer", "Hilltop Market", "Bluebird Diner", "Union Street Deli"]
EXPENSES = [("Flour & grain", 2600_00), ("Butter & dairy", 1900_00), ("Coffee beans", 900_00), ("Rent", 4200_00),
            ("Utilities", 850_00), ("Payroll", 18500_00), ("Packaging", 400_00), ("Equipment repair", 300_00)]
START, END = date(2025, 1, 1), date(2026, 9, 30)

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, city TEXT, joined_on DATE, loyalty_member INTEGER);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price_cents INTEGER, unit_cost_cents INTEGER);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), ordered_at TIMESTAMP, channel TEXT, total_cents INTEGER);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id), product_id INTEGER REFERENCES products(id), quantity INTEGER, unit_price_cents INTEGER);
CREATE TABLE payments (id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id), processor_ref TEXT, method TEXT, amount_cents INTEGER, fee_cents INTEGER, status TEXT, paid_at TIMESTAMP);
CREATE TABLE wholesale_accounts (id INTEGER PRIMARY KEY, business_name TEXT, contact_name TEXT, contact_email TEXT, terms_days INTEGER);
CREATE TABLE invoices (id INTEGER PRIMARY KEY, account_id INTEGER REFERENCES wholesale_accounts(id), issued_on DATE, due_on DATE, amount_cents INTEGER, paid_on DATE);
CREATE TABLE expenses (id INTEGER PRIMARY KEY, incurred_on DATE, category TEXT, amount_cents INTEGER, vendor TEXT);
"""


def build(path, seed=7):
    rng = random.Random(seed)
    path = Path(path); path.unlink(missing_ok=True)
    db = sqlite3.connect(path); db.executescript(SCHEMA)
    for i in range(1, 451):
        f, l = rng.choice(FIRST), rng.choice(LAST)
        db.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?)", (i, f"{f} {l}", f"{f.lower()}.{l.lower()}{i}@example.com",
                   f"555-{rng.randint(100,999)}-{rng.randint(1000,9999)}", rng.choice(CITIES),
                   (START + timedelta(days=rng.randint(0, 600))).isoformat(), int(rng.random() < .35)))
    db.executemany("INSERT INTO products VALUES (?,?,?,?,?)", [(i, *p) for i, p in enumerate(PRODUCTS, 1)])
    order_id = item_id = pay_id = 0
    d = START
    while d <= END:
        season = 1.25 if d.month in (11, 12) else 0.85 if d.month in (1, 2) else 1.0
        growth = 1 + 0.18 * ((d - START).days / 365)   # the business is growing
        weekend = 1.6 if d.weekday() >= 5 else 1.0
        for _ in range(int(rng.gauss(26, 4) * season * growth * weekend)):
            order_id += 1
            cust = rng.randint(1, 450) if rng.random() < .55 else None   # walk-ins have no customer record
            channel = rng.choices(["counter", "online", "phone"], [70, 25, 5])[0]
            at = f"{d.isoformat()} {rng.randint(7,15):02d}:{rng.randint(0,59):02d}:00"
            total = 0
            for _ in range(rng.choices([1, 2, 3, 4], [40, 35, 18, 7])[0]):
                pid = rng.choices(range(1, len(PRODUCTS) + 1), [9,5,6,4,9,7,6,4,4,10,9,5,4,3,3,.6,.4,.5])[0]
                qty = rng.choices([1, 2, 3], [75, 20, 5])[0]
                price = PRODUCTS[pid - 1][2] + (25 if d >= date(2026, 3, 1) else 0)   # March 2026 price increase
                item_id += 1; total += qty * price
                db.execute("INSERT INTO order_items VALUES (?,?,?,?,?)", (item_id, order_id, pid, qty, price))
            db.execute("INSERT INTO orders VALUES (?,?,?,?,?)", (order_id, cust, at, channel, total))
            method = rng.choices(["card", "card_present", "cash", "wallet"], [30, 45, 15, 10])[0]
            fee = 0 if method == "cash" else round(total * .029 + 30) if method in ("card", "wallet") else round(total * .027 + 5)
            status = "refunded" if rng.random() < .012 else "succeeded"
            pay_id += 1
            db.execute("INSERT INTO payments VALUES (?,?,?,?,?,?,?,?)", (pay_id, order_id, None if method == "cash" else f"ch_{rng.getrandbits(48):012x}",
                       method, total, fee, status, at))
        d += timedelta(days=1)
    for i, cafe in enumerate(CAFES, 1):
        first = rng.choice(FIRST)
        db.execute("INSERT INTO wholesale_accounts VALUES (?,?,?,?,?)", (i, cafe, f"{first} {rng.choice(LAST)}",
                   f"{first.lower()}@{cafe.lower().replace(' ', '').replace('é','e')}.example.com", rng.choice([15, 30])))
    inv = 0; d = START
    while d <= END:
        for acct in range(1, len(CAFES) + 1):
            inv += 1
            terms = 15 if acct % 2 else 30
            amount = rng.randint(800, 2600) * 100
            late = rng.random() < (0.35 if acct == 5 else 0.08)   # one account pays late
            paid = d + timedelta(days=terms + (rng.randint(10, 40) if late else rng.randint(-7, 0)))
            db.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?)", (inv, acct, d.isoformat(), (d + timedelta(days=terms)).isoformat(),
                       amount, paid.isoformat() if paid <= END else None))
        d += timedelta(days=14)
    exp = 0; m = START
    while m <= END:
        for cat, base in EXPENSES:
            exp += 1
            bump = 1.22 if cat == "Butter & dairy" and m >= date(2026, 4, 1) else 1.0   # a supplier price jump
            db.execute("INSERT INTO expenses VALUES (?,?,?,?,?)", (exp, m.isoformat(), cat, round(base * bump * rng.uniform(.9, 1.1)), f"{cat} supplier"))
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    db.commit(); db.close()
    return path


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[1] / "data" / "bakery.sqlite"))
