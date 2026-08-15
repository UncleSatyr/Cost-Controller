import sqlite3, os
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from db_config import DATABASE_URL

DB = Path(__file__).parent / "project_cost_control_v3.db"
BACKUP_DIR = Path(__file__).parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

MODULES = ["dashboard","projects","progress","rab","actual","po","invoice","receivable","payable","cashflow","forecast","kpi","reports","users","audit","backup"]
ROLE_DEFAULTS = {
    "Admin": set(MODULES),
    "Manager": {"dashboard","projects","progress","rab","actual","po","invoice","receivable","payable","cashflow","forecast","kpi","reports","audit"},
    "Finance": {"dashboard","projects","actual","invoice","receivable","payable","cashflow","forecast","reports"},
    "Viewer": {"dashboard","progress","rab","invoice","receivable","payable","cashflow","forecast","kpi","reports"},
}
ROLE_WRITE = {"Admin","Manager","Finance"}

FORM_INSTRUCTION = "💡 **Instruksi:** Nominal uang otomatis terformat di bawah saat mengetik."
CURRENCY_HELP = "Ketik angka tanpa titik/koma."

def money(x): return f"Rp {x:,.0f}".replace(",", ".") if x is not None else "Rp 0"

def render_live_format(val):
    if val is not None and val > 0:
        st.markdown(f"<span style='color: #4CAF50; font-weight: bold;'>Terbaca: {money(val)}</span>", unsafe_allow_html=True)

def conn():
    if DATABASE_URL:
        c = psycopg2.connect(DATABASE_URL)
        return c
    else:
        # Fallback to local SQLite if no DB URL is provided
        c = sqlite3.connect(DB, timeout=10.0)
        c.row_factory = sqlite3.Row
        return c

def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode('utf-8')

def check_pw(p, hashed):
    try:
        return bcrypt.checkpw(p.encode(), hashed.encode('utf-8'))
    except:
        return False # Fallback if hash is old SHA-256

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def trans(sql):
    # Auto translate SQLite `?` to PostgreSQL `%s` if using Postgres
    if DATABASE_URL:
        return sql.replace("?", "%s")
    return sql

def q(sql, params=()):
    sql = trans(sql)
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params)

def execute(sql, params=()):
    sql = trans(sql)
    try:
        with conn() as c:
            cursor = c.cursor()
            cursor.execute(sql, params)
            if DATABASE_URL:
                # PostgreSQL needs explicit commit and FETCH for id if RETURNING is used
                c.commit()
                # If we need lastrowid, we would use RETURNING id. We assume it's not strictly needed here for standard queries
                return True, None, None
            else:
                return True, cursor.lastrowid, None
    except Exception as e:
        return False, None, str(e)

def audit(action, module, table_name="", record_id=None, detail=""):
    if st.session_state.get("user"):
        try:
            execute("INSERT INTO audit_logs(username,role,action,module,table_name,record_id,detail,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (st.session_state.user["username"],st.session_state.user["role"],action,module,table_name,record_id,detail,now()))
        except:
            pass

def init_db():
    pk = "SERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    queries = [
        f"CREATE TABLE IF NOT EXISTS users(id {pk}, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER DEFAULT 1, must_change_password INTEGER DEFAULT 1, created_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS permissions(id {pk}, role TEXT, module TEXT, can_view INTEGER DEFAULT 0, can_create INTEGER DEFAULT 0, can_edit INTEGER DEFAULT 0, can_delete INTEGER DEFAULT 0, UNIQUE(role,module))",
        f"CREATE TABLE IF NOT EXISTS projects(id {pk}, name TEXT NOT NULL, customer TEXT, contract_value REAL DEFAULT 0, start_date TEXT, end_date TEXT, pic TEXT, status TEXT DEFAULT 'Active', created_at TEXT, updated_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS rab(id {pk}, project_id INTEGER, code TEXT, category TEXT, description TEXT, qty REAL DEFAULT 0, unit TEXT, unit_price REAL DEFAULT 0, budget REAL DEFAULT 0, approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS actual_costs(id {pk}, project_id INTEGER, date TEXT, category TEXT, description TEXT, vendor TEXT, amount REAL DEFAULT 0, approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS progress(id {pk}, project_id INTEGER, period TEXT, planned_pct REAL DEFAULT 0, actual_pct REAL DEFAULT 0, weight_pct REAL DEFAULT 0, approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS purchase_orders(id {pk}, project_id INTEGER, po_no TEXT, vendor TEXT, date TEXT, description TEXT, po_value REAL DEFAULT 0, paid_value REAL DEFAULT 0, status TEXT DEFAULT 'Open', approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS invoices(id {pk}, project_id INTEGER, invoice_no TEXT, customer TEXT, invoice_date TEXT, due_date TEXT, amount REAL DEFAULT 0, paid_amount REAL DEFAULT 0, status TEXT DEFAULT 'Outstanding', approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS vendor_payables(id {pk}, project_id INTEGER, vendor TEXT, bill_no TEXT, bill_date TEXT, due_date TEXT, amount REAL DEFAULT 0, paid_amount REAL DEFAULT 0, status TEXT DEFAULT 'Outstanding', approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS cashflow(id {pk}, project_id INTEGER, period TEXT, cash_in REAL DEFAULT 0, cash_out REAL DEFAULT 0, approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS audit_logs(id {pk}, username TEXT, role TEXT, action TEXT, module TEXT, table_name TEXT, record_id INTEGER, detail TEXT, created_at TEXT)"
    ]
    with conn() as c:
        if not DATABASE_URL:
            c.execute('PRAGMA journal_mode=WAL;')
        cursor = c.cursor()
        for q in queries:
            cursor.execute(q)
        if DATABASE_URL: c.commit()
    
    # Init default user and permissions
    df_users = q("SELECT COUNT(*) as count FROM users")
    if df_users.iloc[0]["count"] == 0:
        execute("INSERT INTO users(username,password_hash,role,active,must_change_password,created_at) VALUES(?,?,?,?,?,?)",
                  ("admin",hash_pw("admin123"),"Admin",1,1,now()))
    
    for role, mods in ROLE_DEFAULTS.items():
        for m in MODULES:
            if DATABASE_URL:
                execute("INSERT INTO permissions(role,module,can_view,can_create,can_edit,can_delete) VALUES(?,?,?,?,?,?) ON CONFLICT(role,module) DO NOTHING",
                          (role,m,int(m in mods),int(role in ROLE_WRITE and m in mods),int(role in ROLE_WRITE and m in mods),int(role=="Admin" and m in mods)))
            else:
                execute("INSERT OR IGNORE INTO permissions(role,module,can_view,can_create,can_edit,can_delete) VALUES(?,?,?,?,?,?)",
                          (role,m,int(m in mods),int(role in ROLE_WRITE and m in mods),int(role in ROLE_WRITE and m in mods),int(role=="Admin" and m in mods)))

def perm(module, action="view"):
    user = st.session_state.get("user")
    if not user: return False
    r=q("SELECT * FROM permissions WHERE role=? AND module=?",(user["role"],module))
    if r.empty: return False
    col={"view":"can_view","create":"can_create","edit":"can_edit","delete":"can_delete"}[action]
    return bool(r.iloc[0][col])

def require(module, action="view"):
    if not perm(module,action):
        st.error(f"Anda tidak memiliki hak {action} untuk modul ini.")
        st.stop()

def get_active_project():
    pid = st.session_state.get("active_project_selector")
    if pid is None: return None, None
    projects = q("SELECT * FROM projects WHERE id=?", (pid,))
    if projects.empty: return None, None
    return int(pid), projects.iloc[0]
