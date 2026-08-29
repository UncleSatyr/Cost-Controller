import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL tidak ditemukan di file .env")
    exit(1)

# Fix URL for SQLAlchemy if it uses 'postgres://' instead of 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("Menghubungkan ke PostgreSQL (Supabase)...")
try:
    pg_engine = create_engine(DATABASE_URL)
    # Test connection
    with pg_engine.connect() as conn:
        print("Terhubung ke PostgreSQL.")
except Exception as e:
    print(f"Gagal terhubung ke PostgreSQL: {e}")
    exit(1)

print("Menghubungkan ke SQLite lokal...")
sl_conn = sqlite3.connect("project_cost_control_v3.db")

tables = [
    "users", "permissions", "projects", "rab", "actual_costs", 
    "progress", "purchase_orders", "invoices", "vendor_payables", 
    "cashflow", "audit_logs"
]

from utils import init_db
from sqlalchemy import text

print("Membuat skema tabel di PostgreSQL...")
# We must ensure PostgreSQL connection in utils is ready. 
init_db()

print("Membersihkan data lama di PostgreSQL (TRUNCATE)...")
try:
    with pg_engine.connect() as conn:
        table_list = ", ".join(tables)
        conn.execute(text(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"))
        conn.commit()
except Exception as e:
    print(f"Peringatan TRUNCATE: {e}")

for table in tables:
    print(f"Memigrasi tabel: {table}...")
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", sl_conn)
        if not df.empty:
            # Jika tabel users, paksa reset password semua user lama dengan Bcrypt
            if table == "users":
                from utils import hash_pw
                print("   Mereset seluruh password user menjadi 'admin123' dengan Bcrypt...")
                hashed_pw = hash_pw("admin123")
                df['password_hash'] = hashed_pw
                df['must_change_password'] = 1
            
            df.to_sql(table, pg_engine, if_exists="append", index=False)
            print(f"   {len(df)} baris dipindahkan.")
        else:
            print(f"   Tabel kosong, dilewati.")
    except Exception as e:
        print(f"   Gagal memigrasi tabel {table}: {e}")

print("Migrasi selesai!")
sl_conn.close()
