"""
Legacy Inventory Management System — InventoryPro v2.3
Built: 2019 | Maintained by: Dave (left company 2022)
Flask + raw SQL + SQLAlchemy ORM hybrid
"""

import hashlib
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, g, jsonify, request, session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # FIXME: hardcoded secret

engine = create_engine("postgresql://inventory:inv_pass@localhost/inventorypro")
Session = sessionmaker(bind=engine)


# ════════════════════════════════════════════════════════
# Authentication & Authorization
# ════════════════════════════════════════════════════════

ROLES = {"admin": 3, "manager": 2, "viewer": 1}
MAX_LOGIN_ATTEMPTS = 5  # Lock after 5 failures
LOCKOUT_MINUTES = 60  # BRD says 30 minutes but Dave set this to 60


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def require_role(min_role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = session.get("user")
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            role_level = ROLES.get(user.get("role", ""), 0)
            if role_level < min_role:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    db = Session()
    user = db.execute(
        text("SELECT * FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if user.failed_attempts >= MAX_LOGIN_ATTEMPTS:
        locked_until = user.last_failed_at + timedelta(minutes=LOCKOUT_MINUTES)
        if datetime.utcnow() < locked_until:
            return jsonify({"error": "Account locked"}), 423
        # Reset counter after lockout period
        db.execute(
            text("UPDATE users SET failed_attempts = 0 WHERE id = :id"),
            {"id": user.id},
        )
        db.commit()

    if hash_password(password) != user.password_hash:
        db.execute(
            text(
                "UPDATE users SET failed_attempts = failed_attempts + 1, "
                "last_failed_at = NOW() WHERE id = :id"
            ),
            {"id": user.id},
        )
        db.commit()
        return jsonify({"error": "Invalid credentials"}), 401

    # Reset failed attempts on success
    db.execute(
        text("UPDATE users SET failed_attempts = 0, last_login = NOW() WHERE id = :id"),
        {"id": user.id},
    )
    db.commit()

    session["user"] = {"id": user.id, "username": user.username, "role": user.role}
    return jsonify({"message": "Login successful", "role": user.role})


@app.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


# ════════════════════════════════════════════════════════
# Inventory CRUD
# ════════════════════════════════════════════════════════

LOW_STOCK_THRESHOLD = 10  # magic number — should be configurable per product
AUTO_REORDER_QUANTITY = 50  # magic number — always reorders 50 units


@app.route("/api/products", methods=["GET"])
@require_role(1)  # viewer+
def list_products():
    db = Session()
    products = db.execute(text("SELECT * FROM products ORDER BY name")).fetchall()
    return jsonify([dict(row._mapping) for row in products])


@app.route("/api/products/<int:product_id>", methods=["GET"])
@require_role(1)
def get_product(product_id):
    db = Session()
    product = db.execute(
        text("SELECT * FROM products WHERE id = :id"), {"id": product_id}
    ).fetchone()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(dict(product._mapping))


@app.route("/api/products", methods=["POST"])
@require_role(2)  # manager+
def create_product():
    data = request.json
    db = Session()
    db.execute(
        text(
            "INSERT INTO products (name, sku, price, quantity, category, "
            "min_stock, supplier_id, created_at) "
            "VALUES (:name, :sku, :price, :qty, :cat, :min, :sup, NOW())"
        ),
        {
            "name": data["name"],
            "sku": data["sku"],
            "price": data["price"],
            "qty": data.get("quantity", 0),
            "cat": data.get("category", "general"),
            "min": data.get("min_stock", LOW_STOCK_THRESHOLD),
            "sup": data.get("supplier_id"),
        },
    )
    db.commit()
    return jsonify({"message": "Product created"}), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@require_role(2)
def update_product(product_id):
    data = request.json
    db = Session()
    db.execute(
        text(
            "UPDATE products SET name = :name, price = :price, "
            "quantity = :qty, category = :cat, min_stock = :min, "
            "updated_at = NOW() WHERE id = :id"
        ),
        {
            "name": data["name"],
            "price": data["price"],
            "qty": data["quantity"],
            "cat": data.get("category", "general"),
            "min": data.get("min_stock", LOW_STOCK_THRESHOLD),
            "id": product_id,
        },
    )
    db.commit()
    return jsonify({"message": "Product updated"})


# ════════════════════════════════════════════════════════
# Order Processing — GOD FUNCTION (code smell)
# This single function handles validation, stock check,
# approval routing, order creation, stock update, and
# auto-reorder — all in one place.
# ════════════════════════════════════════════════════════

@app.route("/api/orders", methods=["POST"])
@require_role(2)  # manager+
def create_order():
    """Process a new purchase order. Contains ALL business logic inline."""
    data = request.json
    db = Session()
    user = session["user"]

    items = data.get("items", [])
    if not items:
        return jsonify({"error": "Order must have at least one item"}), 400

    total = 0
    order_lines = []

    for item in items:
        product = db.execute(
            text("SELECT * FROM products WHERE id = :id"),
            {"id": item["product_id"]},
        ).fetchone()

        if not product:
            return jsonify({"error": f"Product {item['product_id']} not found"}), 404

        if product.quantity < item["quantity"]:
            return jsonify({
                "error": f"Insufficient stock for {product.name}: "
                         f"available={product.quantity}, requested={item['quantity']}"
            }), 400

        line_total = product.price * item["quantity"]
        total += line_total
        order_lines.append({
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price": float(product.price),
            "line_total": float(line_total),
        })

    # BUSINESS RULE: Orders over $10,000 require admin approval
    # (Note: BRD says $5,000 but management changed it to $10K in 2021)
    needs_approval = total > 10000
    status = "pending_approval" if needs_approval else "confirmed"

    # BUSINESS RULE: Discount for bulk orders > 100 units total
    total_units = sum(item["quantity"] for item in items)
    if total_units > 100:
        discount = total * 0.05  # 5% bulk discount
        total -= discount
    else:
        discount = 0

    # Create order
    result = db.execute(
        text(
            "INSERT INTO orders (user_id, status, total_amount, discount, "
            "notes, created_at) VALUES (:uid, :status, :total, :disc, :notes, NOW()) "
            "RETURNING id"
        ),
        {
            "uid": user["id"],
            "status": status,
            "total": total,
            "disc": discount,
            "notes": data.get("notes", ""),
        },
    )
    order_id = result.fetchone()[0]

    # Create order lines
    for line in order_lines:
        db.execute(
            text(
                "INSERT INTO order_items (order_id, product_id, quantity, "
                "unit_price, line_total) VALUES (:oid, :pid, :qty, :price, :lt)"
            ),
            {
                "oid": order_id,
                "pid": line["product_id"],
                "qty": line["quantity"],
                "price": line["unit_price"],
                "lt": line["line_total"],
            },
        )

    # Update stock and check for auto-reorder
    for line in order_lines:
        db.execute(
            text(
                "UPDATE products SET quantity = quantity - :qty, "
                "updated_at = NOW() WHERE id = :pid"
            ),
            {"qty": line["quantity"], "pid": line["product_id"]},
        )

        # Check low stock
        updated = db.execute(
            text("SELECT quantity, min_stock, supplier_id FROM products WHERE id = :id"),
            {"id": line["product_id"]},
        ).fetchone()

        if updated.quantity <= updated.min_stock:
            # AUTO-REORDER: create a reorder request
            db.execute(
                text(
                    "INSERT INTO reorder_requests (product_id, supplier_id, "
                    "quantity, status, created_at) "
                    "VALUES (:pid, :sid, :qty, 'pending', NOW())"
                ),
                {
                    "pid": line["product_id"],
                    "sid": updated.supplier_id,
                    "qty": AUTO_REORDER_QUANTITY,  # always 50 — not smart
                },
            )

    db.commit()

    return jsonify({
        "order_id": order_id,
        "status": status,
        "total": float(total),
        "discount": float(discount),
        "needs_approval": needs_approval,
    }), 201


@app.route("/api/orders/<int:order_id>/approve", methods=["POST"])
@require_role(3)  # admin only
def approve_order(order_id):
    db = Session()
    db.execute(
        text("UPDATE orders SET status = 'confirmed', approved_by = :uid, "
             "approved_at = NOW() WHERE id = :oid AND status = 'pending_approval'"),
        {"uid": session["user"]["id"], "oid": order_id},
    )
    db.commit()
    return jsonify({"message": "Order approved"})


# ════════════════════════════════════════════════════════
# Reports — Another oversized function
# ════════════════════════════════════════════════════════

@app.route("/api/reports/monthly", methods=["GET"])
@require_role(2)
def monthly_report():
    """Generate monthly summary. Lots of raw SQL and magic numbers."""
    db = Session()
    month = request.args.get("month", datetime.utcnow().strftime("%Y-%m"))

    # Total sales
    sales = db.execute(
        text(
            "SELECT COALESCE(SUM(total_amount), 0) as total_sales, "
            "COUNT(*) as order_count "
            "FROM orders WHERE status IN ('confirmed', 'shipped', 'delivered') "
            "AND TO_CHAR(created_at, 'YYYY-MM') = :month"
        ),
        {"month": month},
    ).fetchone()

    # Top products
    top_products = db.execute(
        text(
            "SELECT p.name, SUM(oi.quantity) as units_sold, "
            "SUM(oi.line_total) as revenue "
            "FROM order_items oi "
            "JOIN orders o ON oi.order_id = o.id "
            "JOIN products p ON oi.product_id = p.id "
            "WHERE o.status IN ('confirmed', 'shipped', 'delivered') "
            "AND TO_CHAR(o.created_at, 'YYYY-MM') = :month "
            "GROUP BY p.name ORDER BY revenue DESC LIMIT 10"
        ),
        {"month": month},
    ).fetchall()

    # Low stock alerts (magic number: 10)
    low_stock = db.execute(
        text("SELECT name, quantity, min_stock FROM products WHERE quantity <= min_stock")
    ).fetchall()

    # Pending approvals
    pending = db.execute(
        text("SELECT COUNT(*) FROM orders WHERE status = 'pending_approval'")
    ).fetchone()

    return jsonify({
        "month": month,
        "total_sales": float(sales.total_sales),
        "order_count": sales.order_count,
        "top_products": [
            {"name": r.name, "units_sold": r.units_sold, "revenue": float(r.revenue)}
            for r in top_products
        ],
        "low_stock_alerts": [
            {"name": r.name, "quantity": r.quantity, "min_stock": r.min_stock}
            for r in low_stock
        ],
        "pending_approvals": pending[0],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
