"""Database seeding script for SaaS analytics domain."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import random
from datetime import datetime, timedelta, timezone
from faker import Faker
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

fake = Faker()
random.seed(42)
Faker.seed(42)

engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 30})

SCHEMA_SQL = """
-- Drop existing tables (cascade)
DROP TABLE IF EXISTS feature_usage CASCADE;
DROP TABLE IF EXISTS features CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- Organizations
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'starter',
    country VARCHAR(100),
    industry VARCHAR(100),
    employee_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    churned_at TIMESTAMPTZ
);

-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Subscriptions
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    mrr NUMERIC(10,2) NOT NULL DEFAULT 0,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    billing_interval VARCHAR(20) NOT NULL DEFAULT 'monthly',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- Invoices
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id),
    amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    due_date DATE,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Events (user activity)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    page VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Features
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    plan_required VARCHAR(50) NOT NULL DEFAULT 'starter'
);

-- Feature usage
CREATE TABLE feature_usage (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    feature_id INTEGER NOT NULL REFERENCES features(id),
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usage_count INTEGER NOT NULL DEFAULT 1
);

-- Indexes for performance
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_subscriptions_org_id ON subscriptions(org_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_events_org_id ON events(org_id);
CREATE INDEX idx_events_created_at ON events(created_at);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_invoices_org_id ON invoices(org_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_feature_usage_org_id ON feature_usage(org_id);
"""

PLANS = ["starter", "growth", "business", "enterprise"]
PLAN_MRR = {"starter": 29, "growth": 99, "business": 299, "enterprise": 999}
ROLES = ["admin", "member", "viewer", "developer"]
SUB_STATUSES = ["active", "active", "active", "trialing", "cancelled", "past_due"]
EVENT_TYPES = [
    "login", "dashboard_view", "report_created", "report_viewed", "export_csv",
    "settings_updated", "user_invited", "feature_used", "api_call", "logout",
    "subscription_upgraded", "billing_viewed", "integration_connected",
]
INDUSTRIES = ["SaaS", "Fintech", "Healthcare", "E-commerce", "Education", "Marketing", "HR Tech", "Legal Tech"]
INVOICE_STATUSES = ["paid", "paid", "paid", "pending", "failed", "void"]


def now():
    return datetime.now(timezone.utc)


def rand_date(days_back=365):
    return now() - timedelta(days=random.randint(0, days_back))


def seed():
    print("Creating schema...")
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
    print("Schema created.")

    # ── Organizations ─────────────────────────────────────────────────────
    print("Seeding organizations...")
    orgs = []
    with engine.begin() as conn:
        for i in range(50):
            plan = random.choice(PLANS)
            created = rand_date(720)
            churned = rand_date(30) if random.random() < 0.1 else None
            r = conn.execute(text("""
                INSERT INTO organizations (name, plan, country, industry, employee_count, created_at, churned_at)
                VALUES (:name, :plan, :country, :industry, :ec, :ca, :ch) RETURNING id
            """), {
                "name": fake.company(),
                "plan": plan,
                "country": fake.country(),
                "industry": random.choice(INDUSTRIES),
                "ec": random.randint(5, 5000),
                "ca": created,
                "ch": churned,
            })
            orgs.append({"id": r.scalar(), "plan": plan, "created": created})
    print(f"  {len(orgs)} organizations created")

    # ── Users ─────────────────────────────────────────────────────────────
    print("Seeding users...")
    users = []
    with engine.begin() as conn:
        for org in orgs:
            num_users = random.randint(3, 20)
            for j in range(num_users):
                role = "admin" if j == 0 else random.choice(ROLES)
                created = org["created"] + timedelta(days=random.randint(0, 30))
                last_login = created + timedelta(days=random.randint(0, 300)) if random.random() > 0.1 else None
                r = conn.execute(text("""
                    INSERT INTO users (org_id, email, name, role, is_active, created_at, last_login_at)
                    VALUES (:oid, :email, :name, :role, :active, :ca, :ll) RETURNING id
                """), {
                    "oid": org["id"],
                    "email": fake.unique.email(),
                    "name": fake.name(),
                    "role": role,
                    "active": random.random() > 0.1,
                    "ca": created,
                    "ll": last_login,
                })
                users.append({"id": r.scalar(), "org_id": org["id"]})
    print(f"  {len(users)} users created")

    # ── Subscriptions ─────────────────────────────────────────────────────
    print("Seeding subscriptions...")
    subs = []
    with engine.begin() as conn:
        for org in orgs:
            # 1-2 subscriptions per org (history + current)
            for _ in range(random.randint(1, 2)):
                plan = org["plan"]
                base_mrr = PLAN_MRR[plan]
                mrr = round(base_mrr * random.uniform(0.8, 1.3), 2)
                status = random.choice(SUB_STATUSES)
                started = org["created"] + timedelta(days=random.randint(0, 30))
                ended = started + timedelta(days=random.randint(30, 365)) if status == "cancelled" else None
                trial_ends = started + timedelta(days=14) if status == "trialing" else None
                r = conn.execute(text("""
                    INSERT INTO subscriptions (org_id, plan, status, mrr, billing_interval, started_at, ended_at, trial_ends_at)
                    VALUES (:oid, :plan, :status, :mrr, :bi, :sa, :ea, :tea) RETURNING id
                """), {
                    "oid": org["id"], "plan": plan, "status": status, "mrr": mrr,
                    "bi": random.choice(["monthly", "annual"]),
                    "sa": started, "ea": ended, "tea": trial_ends,
                })
                subs.append({"id": r.scalar(), "org_id": org["id"], "mrr": mrr})
    print(f"  {len(subs)} subscriptions created")

    # ── Invoices ──────────────────────────────────────────────────────────
    print("Seeding invoices...")
    invoice_rows = []
    for sub in subs:
        for _ in range(random.randint(1, 12)):
            status = random.choice(INVOICE_STATUSES)
            created = rand_date(365)
            paid_at = created + timedelta(days=random.randint(0, 5)) if status == "paid" else None
            invoice_rows.append({
                "oid": sub["org_id"], "sid": sub["id"],
                "amt": round(sub["mrr"] * random.uniform(0.9, 1.1), 2),
                "status": status,
                "dd": (created + timedelta(days=30)).date(),
                "pa": paid_at, "ca": created,
            })
    with engine.begin() as conn:
        for i in range(0, len(invoice_rows), 500):
            conn.execute(text("""
                INSERT INTO invoices (org_id, subscription_id, amount, status, due_date, paid_at, created_at)
                VALUES (:oid, :sid, :amt, :status, :dd, :pa, :ca)
            """), invoice_rows[i:i+500])
    print(f"  {len(invoice_rows)} invoices created")

    # ── Features ──────────────────────────────────────────────────────────
    print("Seeding features...")
    feature_ids = []
    feature_data = [
        ("Analytics Dashboard", "Advanced analytics and reporting", "starter"),
        ("Custom Reports", "Build custom reports with filters", "growth"),
        ("API Access", "Full REST API access", "growth"),
        ("Team Collaboration", "Multi-user workspaces", "starter"),
        ("SSO Integration", "SAML/OAuth SSO support", "business"),
        ("Data Export", "Export data in CSV/Excel/JSON", "starter"),
        ("Webhooks", "Real-time event webhooks", "business"),
        ("Audit Logs", "Detailed audit trail", "enterprise"),
        ("Custom Integrations", "Build custom integrations", "enterprise"),
        ("Priority Support", "24/7 priority support", "business"),
    ]
    with engine.begin() as conn:
        for name, desc, plan_req in feature_data:
            r = conn.execute(text("""
                INSERT INTO features (name, description, plan_required)
                VALUES (:name, :desc, :pr) RETURNING id
            """), {"name": name, "desc": desc, "pr": plan_req})
            feature_ids.append(r.scalar())
    print(f"  {len(feature_ids)} features created")

    # ── Events ────────────────────────────────────────────────────────────
    print("Seeding events (10,000 rows in batches)...")
    event_rows = [
        {
            "uid": (u := random.choice(users))["id"],
            "oid": u["org_id"],
            "et": random.choice(EVENT_TYPES),
            "page": fake.uri_path(),
            "ca": rand_date(180),
        }
        for _ in range(10000)
    ]
    with engine.begin() as conn:
        for i in range(0, len(event_rows), 1000):
            conn.execute(text("""
                INSERT INTO events (user_id, org_id, event_type, page, created_at)
                VALUES (:uid, :oid, :et, :page, :ca)
            """), event_rows[i:i+1000])
    print("  10,000 events created")

    # ── Feature Usage ─────────────────────────────────────────────────────
    print("Seeding feature_usage (5,000 rows in batches)...")
    usage_rows = [
        {
            "oid": random.choice(orgs)["id"],
            "fid": random.choice(feature_ids),
            "ua": rand_date(90),
            "uc": random.randint(1, 100),
        }
        for _ in range(5000)
    ]
    with engine.begin() as conn:
        for i in range(0, len(usage_rows), 1000):
            conn.execute(text("""
                INSERT INTO feature_usage (org_id, feature_id, used_at, usage_count)
                VALUES (:oid, :fid, :ua, :uc)
            """), usage_rows[i:i+1000])
    print("  5,000 feature_usage rows created")

    print("\n[SUCCESS] Database seeding complete!")
    print(f"   Organizations: 50")
    print(f"   Users: {len(users)}")
    print(f"   Subscriptions: {len(subs)}")
    print(f"   Features: {len(feature_ids)}")
    print(f"   Events: 10,000")
    print(f"   Feature usage: 5,000")


if __name__ == "__main__":
    seed()
