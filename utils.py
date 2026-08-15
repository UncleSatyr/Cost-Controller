import sqlite3, hashlib, os
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

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

# Helper text for forms
FORM_INSTRUCTION = "💡 **Instruksi:** Nominal uang otomatis terformat di bawah saat mengetik."
CURRENCY_HELP = "Ketik angka tanpa titik/koma."

def money(x): return f"Rp {x:,.0f}".replace(",", ".") if x is not None else "Rp 0"

def render_live_format(val):
    if val is not None and val > 0:
        st.markdown(f"<span style='color: #4CAF50; font-weight: bold;'>Terbaca: {money(val)}</span>", unsafe_allow_html=True)

def conn():
    c = sqlite3.connect(DB, timeout=10.0)
    return c

def hp(p): return hashlib.sha256(p.encode()).hexdigest()
def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def q(sql, params=()):
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params)

def execute(sql, params=()):
    try:
        with conn() as c:
            cursor = c.cursor()
            cursor.execute(sql, params)
            return True, cursor.lastrowid, None
    except sqlite3.Error as e:
        return False, None, str(e)

def audit(action, module, table_name="", record_id=None, detail=""):
    if st.session_state.get("user"):
        try:
            with conn() as c:
                c.execute("""INSERT INTO audit_logs(username,role,action,module,table_name,record_id,detail,created_at)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (st.session_state.user["username"],st.session_state.user["role"],action,module,table_name,record_id,detail,now()))
        except sqlite3.Error:
            pass

def init_db():
    with conn() as c:
        c.execute('PRAGMA journal_mode=WAL;')
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER DEFAULT 1,
            must_change_password INTEGER DEFAULT 1, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS permissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, module TEXT, can_view INTEGER DEFAULT 0,
            can_create INTEGER DEFAULT 0, can_edit INTEGER DEFAULT 0, can_delete INTEGER DEFAULT 0,
            UNIQUE(role,module))""")
        c.execute("""CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, customer TEXT,
            contract_value REAL DEFAULT 0, start_date TEXT, end_date TEXT, pic TEXT,
            status TEXT DEFAULT 'Active', created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS rab(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, code TEXT, category TEXT,
            description TEXT, qty REAL DEFAULT 0, unit TEXT, unit_price REAL DEFAULT 0,
            budget REAL DEFAULT 0, approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS actual_costs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, date TEXT, category TEXT,
            description TEXT, vendor TEXT, amount REAL DEFAULT 0, approval_status TEXT DEFAULT 'Draft',
            approved_by TEXT, approved_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS progress(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, period TEXT,
            planned_pct REAL DEFAULT 0, actual_pct REAL DEFAULT 0, weight_pct REAL DEFAULT 0,
            approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS purchase_orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, po_no TEXT, vendor TEXT,
            date TEXT, description TEXT, po_value REAL DEFAULT 0, paid_value REAL DEFAULT 0,
            status TEXT DEFAULT 'Open', approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, invoice_no TEXT, customer TEXT,
            invoice_date TEXT, due_date TEXT, amount REAL DEFAULT 0, paid_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'Outstanding', approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS vendor_payables(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, vendor TEXT, bill_no TEXT,
            bill_date TEXT, due_date TEXT, amount REAL DEFAULT 0, paid_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'Outstanding', approval_status TEXT DEFAULT 'Draft', approved_by TEXT, approved_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS cashflow(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, period TEXT,
            cash_in REAL DEFAULT 0, cash_out REAL DEFAULT 0, approval_status TEXT DEFAULT 'Draft',
            approved_by TEXT, approved_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, action TEXT,
            module TEXT, table_name TEXT, record_id INTEGER, detail TEXT, created_at TEXT)""")
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            c.execute("INSERT INTO users(username,password_hash,role,active,must_change_password,created_at) VALUES(?,?,?,?,?,?)",
                      ("admin",hp("admin123"),"Admin",1,1,now()))
        for role, mods in ROLE_DEFAULTS.items():
            for m in MODULES:
                c.execute("""INSERT OR IGNORE INTO permissions(role,module,can_view,can_create,can_edit,can_delete)
                             VALUES(?,?,?,?,?,?)""",
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
