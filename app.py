import sqlite3, io, hashlib, secrets, shutil, os
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import streamlit as st
import plotly.express as px

DB = Path(__file__).with_name("project_cost_control_v3.db")
BACKUP_DIR = Path(__file__).with_name("backups")
BACKUP_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Project Cost Control System v3", page_icon="🏗️", layout="wide")

MODULES = ["dashboard","projects","progress","rab","actual","po","invoice","receivable","payable","cashflow","forecast","kpi","reports","users","audit","backup"]
ROLE_DEFAULTS = {
    "Admin": set(MODULES),
    "Manager": {"dashboard","projects","progress","rab","actual","po","invoice","receivable","payable","cashflow","forecast","kpi","reports","audit"},
    "Finance": {"dashboard","projects","actual","invoice","receivable","payable","cashflow","forecast","reports"},
    "Viewer": {"dashboard","progress","rab","invoice","receivable","payable","cashflow","forecast","kpi","reports"},
}
ROLE_WRITE = {"Admin","Manager","Finance"}

def conn():
    c = sqlite3.connect(DB, timeout=10.0)
    return c

def hp(p): return hashlib.sha256(p.encode()).hexdigest()
def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def money(x): return f"Rp {x:,.0f}".replace(",", ".")

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
        c.execute("""CREATE TABLE IF NOT EXISTS app_settings(
            key TEXT PRIMARY KEY, value TEXT)""")
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            c.execute("INSERT INTO users(username,password_hash,role,active,must_change_password,created_at) VALUES(?,?,?,?,?,?)",
                      ("admin",hp("admin123"),"Admin",1,1,now()))
        for role, mods in ROLE_DEFAULTS.items():
            for m in MODULES:
                c.execute("""INSERT OR IGNORE INTO permissions(role,module,can_view,can_create,can_edit,can_delete)
                             VALUES(?,?,?,?,?,?)""",
                          (role,m,int(m in mods),int(role in ROLE_WRITE and m in mods),int(role in ROLE_WRITE and m in mods),int(role=="Admin" and m in mods)))

init_db()

# ---------- AUTH ----------
if "user" not in st.session_state: st.session_state.user=None

if st.session_state.user is None:
    st.title("🔐 Project Cost Control System V3 Production")
    with st.form("login"):
        u=st.text_input("Username"); p=st.text_input("Password",type="password")
        if st.form_submit_button("Login",type="primary"):
            r=q("SELECT * FROM users WHERE username=? AND password_hash=? AND active=1",(u,hp(p)))
            if not r.empty:
                st.session_state.user={"id":int(r.iloc[0].id),"username":r.iloc[0].username,"role":r.iloc[0].role,"must_change":int(r.iloc[0].must_change_password)}
                audit("LOGIN","auth",detail="Successful login")
                st.rerun()
            else: st.error("Username atau password salah.")
    st.info("Default: admin / admin123. Sistem akan meminta penggantian password pada login pertama.")
    st.stop()

user=st.session_state.user
role=user["role"]

if user.get("must_change"):
    st.warning("⚠️ Anda wajib mengganti password sebelum melanjutkan.")
    with st.form("change_pw"):
        old=st.text_input("Password lama",type="password")
        new=st.text_input("Password baru",type="password")
        confirm=st.text_input("Konfirmasi password",type="password")
        if st.form_submit_button("Ubah Password",type="primary"):
            r=q("SELECT password_hash FROM users WHERE id=?",(user["id"],))
            if r.empty or r.iloc[0].password_hash != hp(old): st.error("Password lama salah.")
            elif len(new)<8: st.error("Password minimal 8 karakter.")
            elif new!=confirm: st.error("Konfirmasi password tidak sama.")
            else:
                s, _, e = execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?",(hp(new),user["id"]))
                if s:
                    audit("PASSWORD_CHANGE","auth","users",user["id"],"Initial password changed")
                    st.session_state.user["must_change"]=0
                    st.success("Password berhasil diubah.")
                    st.rerun()
                else: st.error(e)
    st.stop()

def perm(module, action="view"):
    r=q("SELECT * FROM permissions WHERE role=? AND module=?",(role,module))
    if r.empty: return False
    col={"view":"can_view","create":"can_create","edit":"can_edit","delete":"can_delete"}[action]
    return bool(r.iloc[0][col])

def require(module, action="view"):
    if not perm(module,action):
        st.error(f"Anda tidak memiliki hak {action} untuk modul ini.")
        st.stop()

st.sidebar.success(f"👤 {user['username']} • {role}")
if st.sidebar.button("Logout"):
    audit("LOGOUT","auth")
    st.session_state.user=None
    st.rerun()

# ---------- MENU ----------
labels = {
"dashboard":"📊 Dashboard","projects":"🏗️ Proyek","progress":"📈 Progress","rab":"📋 RAB",
"actual":"💸 Actual Cost","po":"🧾 PO / Procurement","invoice":"🧮 Invoice & Termin",
"receivable":"💰 Piutang","payable":"🏦 Hutang Vendor","cashflow":"💵 Cash Flow",
"forecast":"🔮 EAC / ETC","kpi":"📐 CPI / SPI","reports":"📥 Reports",
"users":"👥 Users & Permissions","audit":"🕵️ Audit Trail","backup":"💾 Backup Database"}

allowed=[m for m in MODULES if perm(m,"view")]
menu=st.sidebar.radio("MENU",[labels[m] for m in allowed])
module=next(m for m in allowed if labels[m]==menu)

projects=q("SELECT * FROM projects ORDER BY id DESC")
pid=None; project=None
if not projects.empty:
    pid=st.sidebar.selectbox("PROYEK AKTIF",projects.id.tolist(),format_func=lambda x:projects.loc[projects.id==x,"name"].iloc[0])
    project=projects.loc[projects.id==pid].iloc[0]

# Helper text for forms
FORM_INSTRUCTION = "💡 **Instruksi Input Nominal:** Streamlit form tidak memisahkan ribuan saat mengetik. Masukkan angka *murni* tanpa titik atau koma (contoh: untuk Rp 1.500.000 ketik `1500000`)."
CURRENCY_HELP = "Ketik angka tanpa titik/koma."

# ---------- PROJECT ----------
if module=="projects":
    require("projects")
    st.subheader("🏗️ Database Proyek")
    if perm("projects","create"):
        with st.form("new_project"):
            st.info(FORM_INSTRUCTION)
            a,b=st.columns(2)
            name=a.text_input("Nama Proyek *"); customer=b.text_input("Customer")
            contract=a.number_input("Nilai Kontrak (Rp)",0.0,step=100000.0, help=CURRENCY_HELP); pic=b.text_input("PIC")
            start=a.date_input("Tanggal Mulai",date.today()); end=b.date_input("Target Selesai",date.today())
            status=st.selectbox("Status",["Active","Completed","On Hold","Cancelled"])
            if st.form_submit_button("Simpan Proyek",type="primary") and name.strip():
                s, lid, e = execute("INSERT INTO projects(name,customer,contract_value,start_date,end_date,pic,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                        (name,customer,contract,str(start),str(end),pic,status,now(),now()))
                if s: audit("CREATE","projects","projects",lid,name); st.rerun()
                else: st.error(e)
    if not projects.empty:
        st.dataframe(projects,use_container_width=True,hide_index=True)
        if perm("projects","edit") or perm("projects","delete"):
            with st.expander("Edit / Hapus Proyek"):
                psel=st.selectbox("Pilih Proyek",projects.id.tolist())
                p=projects.loc[projects.id==psel].iloc[0]
                if perm("projects","edit"):
                    with st.form("edit_project"):
                        st.info(FORM_INSTRUCTION)
                        nm=st.text_input("Nama",p.name); cv=st.number_input("Nilai Kontrak (Rp)",value=float(p.contract_value), help=CURRENCY_HELP)
                        stt=st.selectbox("Status",["Active","Completed","On Hold","Cancelled"],index=["Active","Completed","On Hold","Cancelled"].index(p.status))
                        if st.form_submit_button("Update"):
                            s, _, e = execute("UPDATE projects SET name=?,contract_value=?,status=?,updated_at=? WHERE id=?",(nm,cv,stt,now(),psel))
                            if s: audit("UPDATE","projects","projects",psel,nm); st.rerun()
                            else: st.error(e)
                if perm("projects","delete"):
                    if st.button("🗑️ Hapus Proyek Terpilih"):
                        s, _, e = execute("DELETE FROM projects WHERE id=?",(psel,))
                        if s: audit("DELETE","projects","projects",psel); st.rerun()
                        else: st.error(e)

elif module=="progress":
    require("progress")
    st.subheader("📈 Progress Proyek")
    if not projects.empty and perm("progress","create"):
        with st.form("progress"):
            a,b,c=st.columns(3); period=a.text_input("Periode"); planned=b.number_input("Planned %",0.,100.,step=1.); actual=c.number_input("Actual %",0.,100.,step=1.)
            weight=st.number_input("Bobot %",0.,100.,step=1.)
            if st.form_submit_button("Tambah"):
                s, lid, e = execute("INSERT INTO progress(project_id,period,planned_pct,actual_pct,weight_pct) VALUES(?,?,?,?,?)",(pid,period,planned,actual,weight))
                if s: audit("CREATE","progress","progress",lid,period); st.rerun()
                else: st.error(e)
    df=q("SELECT * FROM progress WHERE project_id=? ORDER BY id",(pid,)) if pid else pd.DataFrame()
    if not df.empty:
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.plotly_chart(px.line(df,x="period",y=["planned_pct","actual_pct"],markers=True,title="Planned vs Actual"),use_container_width=True)
        
        if perm("progress","edit") or perm("progress","delete"):
            with st.expander("Edit / Hapus Progress"):
                psel = st.selectbox("Pilih Progress", df.id.tolist())
                sel = df.loc[df.id==psel].iloc[0]
                if sel.approval_status == 'Approved':
                    st.warning("Data sudah diapprove, tidak dapat diubah.")
                else:
                    if perm("progress","edit"):
                        with st.form("edit_prog"):
                            e_per = st.text_input("Periode", sel.period)
                            e_plan = st.number_input("Planned %", 0., 100., float(sel.planned_pct))
                            e_act = st.number_input("Actual %", 0., 100., float(sel.actual_pct))
                            e_w = st.number_input("Bobot %", 0., 100., float(sel.weight_pct))
                            if st.form_submit_button("Update"):
                                s, _, e = execute("UPDATE progress SET period=?, planned_pct=?, actual_pct=?, weight_pct=? WHERE id=?", (e_per, e_plan, e_act, e_w, psel))
                                if s: audit("UPDATE","progress","progress",psel,e_per); st.rerun()
                                else: st.error(e)
                    if perm("progress","delete"):
                        if st.button("Hapus Progress Terpilih"):
                            s, _, e = execute("DELETE FROM progress WHERE id=?",(psel,))
                            if s: audit("DELETE","progress","progress",psel); st.rerun()
                            else: st.error(e)

elif module=="rab":
    require("rab")
    st.subheader("📋 RAB + Approval Workflow")
    if perm("rab","create"):
        with st.form("rab"):
            st.info(FORM_INSTRUCTION)
            a,b,c=st.columns(3); code=a.text_input("Kode"); cat=b.text_input("Kategori"); desc=c.text_input("Uraian")
            d,e,f=st.columns(3); qty=d.number_input("Qty",0.); unit=e.text_input("Satuan"); price=f.number_input("Harga Satuan (Rp)",0.,step=1000., help=CURRENCY_HELP)
            if st.form_submit_button("Tambah RAB"):
                s, lid, e = execute("INSERT INTO rab(project_id,code,category,description,qty,unit,unit_price,budget) VALUES(?,?,?,?,?,?,?,?)",(pid,code,cat,desc,qty,unit,price,qty*price))
                if s: audit("CREATE","rab","rab",lid,code); st.rerun()
                else: st.error(e)
    df=q("SELECT * FROM rab WHERE project_id=? ORDER BY id",(pid,)) if pid else pd.DataFrame()
    if not df.empty:
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.metric("Total RAB",money(df.budget.sum()))
        if role in ["Admin","Manager"]:
            with st.expander("✅ Approval RAB"):
                rid=st.selectbox("Pilih RAB untuk approval",df[df.approval_status != 'Approved'].id.tolist() if not df[df.approval_status != 'Approved'].empty else [None])
                if rid and st.button("Approve RAB"):
                    s, _, e = execute("UPDATE rab SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?",(user["username"],now(),rid))
                    if s: audit("APPROVE","rab","rab",rid); st.rerun()
                    else: st.error(e)
        
        if perm("rab","edit") or perm("rab","delete"):
            with st.expander("Edit / Hapus RAB"):
                psel = st.selectbox("Pilih RAB", df.id.tolist())
                sel = df.loc[df.id==psel].iloc[0]
                if sel.approval_status == 'Approved':
                    st.warning("Data sudah diapprove, tidak dapat diubah.")
                else:
                    if perm("rab","edit"):
                        with st.form("edit_rab"):
                            st.info(FORM_INSTRUCTION)
                            e_code = st.text_input("Kode", sel.code)
                            e_cat = st.text_input("Kategori", sel.category)
                            e_desc = st.text_input("Uraian", sel.description)
                            e_qty = st.number_input("Qty", 0., value=float(sel.qty))
                            e_unit = st.text_input("Satuan", sel.unit)
                            e_price = st.number_input("Harga Satuan (Rp)", 0., value=float(sel.unit_price), help=CURRENCY_HELP)
                            if st.form_submit_button("Update"):
                                s, _, e = execute("UPDATE rab SET code=?, category=?, description=?, qty=?, unit=?, unit_price=?, budget=? WHERE id=?", (e_code, e_cat, e_desc, e_qty, e_unit, e_price, e_qty*e_price, psel))
                                if s: audit("UPDATE","rab","rab",psel,e_code); st.rerun()
                                else: st.error(e)
                    if perm("rab","delete"):
                        if st.button("Hapus RAB Terpilih"):
                            s, _, e = execute("DELETE FROM rab WHERE id=?",(psel,))
                            if s: audit("DELETE","rab","rab",psel); st.rerun()
                            else: st.error(e)

elif module=="actual":
    require("actual")
    st.subheader("💸 Actual Cost + Approval")
    if perm("actual","create"):
        with st.form("actual"):
            st.info(FORM_INSTRUCTION)
            a,b,c=st.columns(3); dt=a.date_input("Tanggal",date.today()); cat=b.text_input("Kategori"); vendor=c.text_input("Vendor")
            desc=a.text_input("Deskripsi"); amount=b.number_input("Amount (Rp)",0.,step=100000., help=CURRENCY_HELP)
            if st.form_submit_button("Tambah Actual"):
                s, lid, e = execute("INSERT INTO actual_costs(project_id,date,category,description,vendor,amount) VALUES(?,?,?,?,?,?)",(pid,str(dt),cat,desc,vendor,amount))
                if s: audit("CREATE","actual","actual_costs",lid,str(amount)); st.rerun()
                else: st.error(e)
    df=q("SELECT * FROM actual_costs WHERE project_id=? ORDER BY id DESC",(pid,)) if pid else pd.DataFrame()
    if not df.empty:
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.metric("Total Actual",money(df.amount.sum()))
        if perm("actual","edit") or perm("actual","delete"):
            with st.expander("Edit / Hapus Actual Cost"):
                psel = st.selectbox("Pilih Actual Cost", df.id.tolist())
                sel = df.loc[df.id==psel].iloc[0]
                if sel.approval_status == 'Approved':
                    st.warning("Data sudah diapprove, tidak dapat diubah.")
                else:
                    if perm("actual","edit"):
                        with st.form("edit_actual"):
                            st.info(FORM_INSTRUCTION)
                            e_dt = st.date_input("Tanggal", datetime.strptime(sel.date, "%Y-%m-%d").date() if sel.date else date.today())
                            e_cat = st.text_input("Kategori", sel.category)
                            e_ven = st.text_input("Vendor", sel.vendor)
                            e_desc = st.text_input("Deskripsi", sel.description)
                            e_amt = st.number_input("Amount (Rp)", 0., value=float(sel.amount), help=CURRENCY_HELP)
                            if st.form_submit_button("Update"):
                                s, _, e = execute("UPDATE actual_costs SET date=?, category=?, vendor=?, description=?, amount=? WHERE id=?", (str(e_dt), e_cat, e_ven, e_desc, e_amt, psel))
                                if s: audit("UPDATE","actual","actual_costs",psel,str(e_amt)); st.rerun()
                                else: st.error(e)
                    if perm("actual","delete"):
                        if st.button("Hapus Actual Terpilih"):
                            s, _, e = execute("DELETE FROM actual_costs WHERE id=?",(psel,))
                            if s: audit("DELETE","actual","actual_costs",psel); st.rerun()
                            else: st.error(e)

elif module=="po":
    require("po")
    st.subheader("🧾 PO / Procurement + Approval")
    if perm("po","create"):
        with st.form("po"):
            st.info(FORM_INSTRUCTION)
            a,b,c=st.columns(3); no=a.text_input("PO No"); vendor=b.text_input("Vendor"); dt=c.date_input("Tanggal",date.today())
            desc=a.text_input("Deskripsi"); value=b.number_input("Nilai PO (Rp)",0.,step=100000., help=CURRENCY_HELP); paid=c.number_input("Paid (Rp)",0.,step=100000., help=CURRENCY_HELP)
            if st.form_submit_button("Tambah PO"):
                s, lid, e = execute("INSERT INTO purchase_orders(project_id,po_no,vendor,date,description,po_value,paid_value) VALUES(?,?,?,?,?,?,?)",(pid,no,vendor,str(dt),desc,value,paid))
                if s: audit("CREATE","po","purchase_orders",lid,no); st.rerun()
                else: st.error(e)
    df=q("SELECT * FROM purchase_orders WHERE project_id=?",(pid,)) if pid else pd.DataFrame()
    if not df.empty:
        df["outstanding"]=df.po_value-df.paid_value; st.dataframe(df,use_container_width=True,hide_index=True)
        if perm("po","edit") or perm("po","delete"):
            with st.expander("Edit / Hapus PO"):
                psel = st.selectbox("Pilih PO", df.id.tolist())
                sel = df.loc[df.id==psel].iloc[0]
                if sel.approval_status == 'Approved':
                    st.warning("Data sudah diapprove, tidak dapat diubah.")
                else:
                    if perm("po","edit"):
                        with st.form("edit_po"):
                            st.info(FORM_INSTRUCTION)
                            e_no = st.text_input("PO No", sel.po_no)
                            e_ven = st.text_input("Vendor", sel.vendor)
                            e_dt = st.date_input("Tanggal", datetime.strptime(sel.date, "%Y-%m-%d").date() if sel.date else date.today())
                            e_desc = st.text_input("Deskripsi", sel.description)
                            e_val = st.number_input("Nilai PO (Rp)", 0., value=float(sel.po_value), help=CURRENCY_HELP)
                            e_paid = st.number_input("Paid (Rp)", 0., value=float(sel.paid_value), help=CURRENCY_HELP)
                            if st.form_submit_button("Update"):
                                s, _, e = execute("UPDATE purchase_orders SET po_no=?, vendor=?, date=?, description=?, po_value=?, paid_value=? WHERE id=?", (e_no, e_ven, str(e_dt), e_desc, e_val, e_paid, psel))
                                if s: audit("UPDATE","po","purchase_orders",psel,e_no); st.rerun()
                                else: st.error(e)
                    if perm("po","delete"):
                        if st.button("Hapus PO Terpilih"):
                            s, _, e = execute("DELETE FROM purchase_orders WHERE id=?",(psel,))
                            if s: audit("DELETE","po","purchase_orders",psel); st.rerun()
                            else: st.error(e)

elif module=="invoice":
    require("invoice")
    st.subheader("🧮 Invoice & Termin + Approval")
    if perm("invoice","create"):
        with st.form("inv"):
            st.info(FORM_INSTRUCTION)
            a,b,c=st.columns(3); no=a.text_input("Invoice/Termin"); cust=b.text_input("Customer"); inv=a.date_input("Invoice Date",date.today()); due=c.date_input("Due Date",date.today())
            amount=b.number_input("Amount (Rp)",0.,step=100000., help=CURRENCY_HELP); paid=c.number_input("Paid (Rp)",0.,step=100000., help=CURRENCY_HELP)
            if st.form_submit_button("Tambah Invoice"):
                s, lid, e = execute("INSERT INTO invoices(project_id,invoice_no,customer,invoice_date,due_date,amount,paid_amount) VALUES(?,?,?,?,?,?,?)",(pid,no,cust,str(inv),str(due),amount,paid))
                if s: audit("CREATE","invoice","invoices",lid,no); st.rerun()
                else: st.error(e)
    df=q("SELECT * FROM invoices WHERE project_id=?",(pid,)) if pid else pd.DataFrame()
    if not df.empty:
        df["outstanding"]=df.amount-df.paid_amount; st.dataframe(df,use_container_width=True,hide_index=True)
        if perm("invoice","edit") or perm("invoice","delete"):
            with st.expander("Edit / Hapus Invoice"):
                psel = st.selectbox("Pilih Invoice", df.id.tolist())
                sel = df.loc[df.id==psel].iloc[0]
                if sel.approval_status == 'Approved':
                    st.warning("Data sudah diapprove, tidak dapat diubah.")
                else:
                    if perm("invoice","edit"):
                        with st.form("edit_inv"):
                            st.info(FORM_INSTRUCTION)
                            e_no = st.text_input("Invoice/Termin", sel.invoice_no)
                            e_cust = st.text_input("Customer", sel.customer)
                            e_inv = st.date_input("Invoice Date", datetime.strptime(sel.invoice_date, "%Y-%m-%d").date() if sel.invoice_date else date.today())
                            e_due = st.date_input("Due Date", datetime.strptime(sel.due_date, "%Y-%m-%d").date() if sel.due_date else date.today())
                            e_amt = st.number_input("Amount (Rp)", 0., value=float(sel.amount), help=CURRENCY_HELP)
                            e_paid = st.number_input("Paid (Rp)", 0., value=float(sel.paid_amount), help=CURRENCY_HELP)
                            if st.form_submit_button("Update"):
                                s, _, e = execute("UPDATE invoices SET invoice_no=?, customer=?, invoice_date=?, due_date=?, amount=?, paid_amount=? WHERE id=?", (e_no, e_cust, str(e_inv), str(e_due), e_amt, e_paid, psel))
                                if s: audit("UPDATE","invoice","invoices",psel,e_no); st.rerun()
                                else: st.error(e)
                    if perm("invoice","delete"):
                        if st.button("Hapus Invoice Terpilih"):
                            s, _, e = execute("DELETE FROM invoices WHERE id=?",(psel,))
                            if s: audit("DELETE","invoice","invoices",psel); st.rerun()
                            else: st.error(e)

elif module=="receivable":
    require("receivable")
    st.subheader("💰 Piutang")
    df=q("SELECT * FROM invoices WHERE project_id=? AND amount>paid_amount ORDER BY due_date",(pid,)) if pid else pd.DataFrame()
    if df.empty: st.success("Tidak ada piutang outstanding.")
    else:
        df["outstanding"]=df.amount-df.paid_amount; st.dataframe(df,use_container_width=True,hide_index=True); st.metric("Total Piutang",money(df.outstanding.sum()))

elif module=="payable":
    require("payable")
    st.subheader("🏦 Hutang Vendor")
    if perm("payable","create"):
        with st.form("pay"):
            st.info(FORM_INSTRUCTION)
            a,b,c=st.columns(3); vendor=a.text_input("Vendor"); bill=b.text_input("No Tagihan"); bd=c.date_input("Bill Date",date.today()); due=a.date_input("Due Date",date.today())
            amount=b.number_input("Amount (Rp)",0.,step=100000., help=CURRENCY_HELP); paid=c.number_input("Paid (Rp)",0.,step=100000., help=CURRENCY_HELP)
            if st.form_submit_button("Tambah Hutang"):
                s, lid, e = execute("INSERT INTO vendor_payables(project_id,vendor,bill_no,bill_date,due_date,amount,paid_amount) VALUES(?,?,?,?,?,?,?)",(pid,vendor,bill,str(bd),str(due),amount,paid))
                if s: audit("CREATE","payable","vendor_payables",lid,bill); st.rerun()
                else: st.error(e)
    df=q("SELECT * FROM vendor_payables WHERE project_id=?",(pid,)) if pid else pd.DataFrame()
    if not df.empty:
        df["outstanding"]=df.amount-df.paid_amount; st.dataframe(df,use_container_width=True,hide_index=True); st.metric("Hutang Outstanding",money(df.outstanding.sum()))
        if perm("payable","edit") or perm("payable","delete"):
            with st.expander("Edit / Hapus Hutang"):
                psel = st.selectbox("Pilih Hutang", df.id.tolist())
                sel = df.loc[df.id==psel].iloc[0]
                if sel.approval_status == 'Approved':
                    st.warning("Data sudah diapprove, tidak dapat diubah.")
                else:
                    if perm("payable","edit"):
                        with st.form("edit_pay"):
                            st.info(FORM_INSTRUCTION)
                            e_ven = st.text_input("Vendor", sel.vendor)
                            e_bill = st.text_input("No Tagihan", sel.bill_no)
                            e_bd = st.date_input("Bill Date", datetime.strptime(sel.bill_date, "%Y-%m-%d").date() if sel.bill_date else date.today())
                            e_due = st.date_input("Due Date", datetime.strptime(sel.due_date, "%Y-%m-%d").date() if sel.due_date else date.today())
                            e_amt = st.number_input("Amount (Rp)", 0., value=float(sel.amount), help=CURRENCY_HELP)
                            e_paid = st.number_input("Paid (Rp)", 0., value=float(sel.paid_amount), help=CURRENCY_HELP)
                            if st.form_submit_button("Update"):
                                s, _, e = execute("UPDATE vendor_payables SET vendor=?, bill_no=?, bill_date=?, due_date=?, amount=?, paid_amount=? WHERE id=?", (e_ven, e_bill, str(e_bd), str(e_due), e_amt, e_paid, psel))
                                if s: audit("UPDATE","payable","vendor_payables",psel,e_bill); st.rerun()
                                else: st.error(e)
                    if perm("payable","delete"):
                        if st.button("Hapus Hutang Terpilih"):
                            s, _, e = execute("DELETE FROM vendor_payables WHERE id=?",(psel,))
                            if s: audit("DELETE","payable","vendor_payables",psel); st.rerun()
                            else: st.error(e)

elif module=="cashflow":
    require("cashflow")
    st.subheader("💵 Cash Flow")
    if perm("cashflow","create"):
        with st.form("cf"):
            st.info(FORM_INSTRUCTION)
            a,b,c=st.columns(3); period=a.text_input("Periode"); cin=b.number_input("Cash In (Rp)",0.,step=100000., help=CURRENCY_HELP); cout=c.number_input("Cash Out (Rp)",0.,step=100000., help=CURRENCY_HELP)
            if st.form_submit_button("Tambah"):
                s, lid, e = execute("INSERT INTO cashflow(project_id,period,cash_in,cash_out) VALUES(?,?,?,?)",(pid,period,cin,cout))
                if s: audit("CREATE","cashflow","cashflow",lid,period); st.rerun()
                else: st.error(e)
    df=q("SELECT * FROM cashflow WHERE project_id=?",(pid,)) if pid else pd.DataFrame()
    if not df.empty:
        df["net"]=df.cash_in-df.cash_out; df["cumulative"]=df.net.cumsum(); st.dataframe(df,use_container_width=True,hide_index=True)
        st.plotly_chart(px.line(df,x="period",y="cumulative",markers=True,title="Cumulative Cash Flow"),use_container_width=True)
        if perm("cashflow","edit") or perm("cashflow","delete"):
            with st.expander("Edit / Hapus Cash Flow"):
                psel = st.selectbox("Pilih Cash Flow", df.id.tolist())
                sel = df.loc[df.id==psel].iloc[0]
                if sel.approval_status == 'Approved':
                    st.warning("Data sudah diapprove, tidak dapat diubah.")
                else:
                    if perm("cashflow","edit"):
                        with st.form("edit_cf"):
                            st.info(FORM_INSTRUCTION)
                            e_per = st.text_input("Periode", sel.period)
                            e_cin = st.number_input("Cash In (Rp)", 0., value=float(sel.cash_in), help=CURRENCY_HELP)
                            e_cout = st.number_input("Cash Out (Rp)", 0., value=float(sel.cash_out), help=CURRENCY_HELP)
                            if st.form_submit_button("Update"):
                                s, _, e = execute("UPDATE cashflow SET period=?, cash_in=?, cash_out=? WHERE id=?", (e_per, e_cin, e_cout, psel))
                                if s: audit("UPDATE","cashflow","cashflow",psel,e_per); st.rerun()
                                else: st.error(e)
                    if perm("cashflow","delete"):
                        if st.button("Hapus Cash Flow Terpilih"):
                            s, _, e = execute("DELETE FROM cashflow WHERE id=?",(psel,))
                            if s: audit("DELETE","cashflow","cashflow",psel); st.rerun()
                            else: st.error(e)

elif module=="forecast":
    require("forecast")
    st.subheader("🔮 EAC / ETC & Forecast Laba")
    rab=q("SELECT * FROM rab WHERE project_id=?",(pid,)); ac=q("SELECT * FROM actual_costs WHERE project_id=?",(pid,)); pr=q("SELECT * FROM progress WHERE project_id=? ORDER BY id",(pid,))
    bac=float(rab.budget.sum()) if not rab.empty else 0; actual=float(ac.amount.sum()) if not ac.empty else 0; progress=float(pr.actual_pct.iloc[-1]/100) if not pr.empty else 0
    cpi=(bac*progress)/actual if actual and bac else 0
    eac=actual+(bac-actual)/cpi if cpi>0 else actual
    etc=eac-actual; contract=float(project.contract_value); profit=contract-eac
    a,b,c,d=st.columns(4); a.metric("BAC",money(bac)); b.metric("AC",money(actual)); c.metric("EAC",money(eac)); d.metric("ETC",money(etc))
    st.metric("Forecast Laba Akhir",money(profit)); st.metric("Forecast Margin",f"{profit/contract:.2%}" if contract else "0.00%")

elif module=="kpi":
    require("kpi")
    st.subheader("📐 Earned Value KPI — CPI / SPI")
    rab=q("SELECT * FROM rab WHERE project_id=?",(pid,)); ac=q("SELECT * FROM actual_costs WHERE project_id=?",(pid,)); pr=q("SELECT * FROM progress WHERE project_id=? ORDER BY id",(pid,))
    bac=float(rab.budget.sum()) if not rab.empty else 0; acv=float(ac.amount.sum()) if not ac.empty else 0; planned=float(pr.planned_pct.iloc[-1]/100) if not pr.empty else 0; actualp=float(pr.actual_pct.iloc[-1]/100) if not pr.empty else 0
    pv=bac*planned; ev=bac*actualp; cpi=ev/acv if acv else 0; spi=ev/pv if pv else 0
    a,b,c,d=st.columns(4); a.metric("PV",money(pv)); b.metric("EV",money(ev)); c.metric("AC",money(acv)); d.metric("CPI",f"{cpi:.2f}")
    st.metric("SPI",f"{spi:.2f}"); st.info("CPI > 1 = efisien biaya; CPI < 1 = cost overrun. SPI > 1 = lebih cepat; SPI < 1 = terlambat.")

elif module=="dashboard":
    require("dashboard")
    st.subheader(f"📊 Executive Management Dashboard — {project['name'] if project is not None else 'No Project'}")
    if project is None: st.info("Belum ada proyek."); st.stop()
    rab=q("SELECT * FROM rab WHERE project_id=?",(pid,)); ac=q("SELECT * FROM actual_costs WHERE project_id=?",(pid,)); pr=q("SELECT * FROM progress WHERE project_id=? ORDER BY id",(pid,)); inv=q("SELECT * FROM invoices WHERE project_id=?",(pid,)); pay=q("SELECT * FROM vendor_payables WHERE project_id=?",(pid,)); cf=q("SELECT * FROM cashflow WHERE project_id=?",(pid,))
    contract=float(project.contract_value); bac=float(rab.budget.sum()) if not rab.empty else 0; actual=float(ac.amount.sum()) if not ac.empty else 0; progress=float(pr.actual_pct.iloc[-1]) if not pr.empty else 0; planned=float(pr.planned_pct.iloc[-1]) if not pr.empty else 0
    profit=contract-actual; margin=profit/contract if contract else 0; receiv=float((inv.amount-inv.paid_amount).sum()) if not inv.empty else 0; payable=float((pay.amount-pay.paid_amount).sum()) if not pay.empty else 0; netcash=float((cf.cash_in-cf.cash_out).sum()) if not cf.empty else 0
    a,b,c,d=st.columns(4); a.metric("Contract",money(contract)); b.metric("BAC / RAB",money(bac)); c.metric("Actual Cost",money(actual)); d.metric("Current Profit",money(profit))
    a,b,c,d=st.columns(4); a.metric("Progress",f"{progress:.1f}%",f"{progress-planned:.1f}% vs plan"); b.metric("Margin",f"{margin:.2%}"); c.metric("Piutang",money(receiv)); d.metric("Hutang",money(payable))
    st.metric("Net Cash Flow",money(netcash))
    if margin>=.15: st.success("🟢 HEALTHY — margin di atas 15%")
    elif margin>=.05: st.warning("🟡 WATCH — perlu monitoring")
    else: st.error("🔴 CRITICAL — margin rendah")
    if not pr.empty: st.plotly_chart(px.line(pr,x="period",y=["planned_pct","actual_pct"],markers=True,title="Progress Plan vs Actual"),use_container_width=True)
    if not rab.empty: st.plotly_chart(px.bar(rab.groupby("category")["budget"].sum().reset_index(),x="category",y="budget",title="RAB per Kategori"),use_container_width=True)

elif module=="reports":
    require("reports")
    st.subheader("📥 Project Report")
    if project is None: st.stop()
    tables={"Project":q("SELECT * FROM projects WHERE id=?",(pid,)),"RAB":q("SELECT * FROM rab WHERE project_id=?",(pid,)),"Actual_Cost":q("SELECT * FROM actual_costs WHERE project_id=?",(pid,)),"Progress":q("SELECT * FROM progress WHERE project_id=?",(pid,)),"PO":q("SELECT * FROM purchase_orders WHERE project_id=?",(pid,)),"Invoice":q("SELECT * FROM invoices WHERE project_id=?",(pid,)),"Hutang":q("SELECT * FROM vendor_payables WHERE project_id=?",(pid,)),"Cash_Flow":q("SELECT * FROM cashflow WHERE project_id=?",(pid,)),"Audit":q("SELECT * FROM audit_logs ORDER BY id DESC")}
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        for n,d in tables.items(): d.to_excel(w,index=False,sheet_name=n[:31])
    st.download_button("⬇️ Download Excel",out.getvalue(),f"{project['name']}_V3_Report.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")

elif module=="users":
    require("users")
    st.subheader("👥 User & Module Permissions")
    users=q("SELECT id,username,role,active,must_change_password,created_at FROM users")
    st.dataframe(users,use_container_width=True,hide_index=True)
    if perm("users","create"):
        with st.form("newuser"):
            a,b,c=st.columns(3); un=a.text_input("Username"); pw=b.text_input("Password",type="password"); rr=c.selectbox("Role",["Admin","Manager","Finance","Viewer"])
            if st.form_submit_button("Tambah User"):
                s, lid, e = execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",(un,hp(pw),rr,now()))
                if s: audit("CREATE","users","users",lid,un); st.rerun()
                else: st.error(e)
    if not users.empty and (perm("users","edit") or perm("users","delete")):
        with st.expander("Edit / Hapus User"):
            psel = st.selectbox("Pilih User", users.id.tolist(), format_func=lambda x: users.loc[users.id==x, "username"].iloc[0])
            sel = users.loc[users.id==psel].iloc[0]
            if perm("users","edit"):
                with st.form("edit_user"):
                    e_un = st.text_input("Username", sel.username)
                    e_rr = st.selectbox("Role", ["Admin","Manager","Finance","Viewer"], index=["Admin","Manager","Finance","Viewer"].index(sel.role))
                    e_act = st.checkbox("Active", value=bool(sel.active))
                    if st.form_submit_button("Update"):
                        s, _, e = execute("UPDATE users SET username=?, role=?, active=? WHERE id=?", (e_un, e_rr, int(e_act), psel))
                        if s: audit("UPDATE","users","users",psel,e_un); st.rerun()
                        else: st.error(e)
            if perm("users","delete"):
                if st.button("Hapus User Terpilih"):
                    if sel.username == "admin":
                        st.error("Tidak dapat menghapus user admin default.")
                    else:
                        s, _, e = execute("DELETE FROM users WHERE id=?",(psel,))
                        if s: audit("DELETE","users","users",psel); st.rerun()
                        else: st.error(e)
                        
    st.markdown("### Hak Akses Modul")
    p=q("SELECT * FROM permissions ORDER BY role,module")
    st.dataframe(p,use_container_width=True,hide_index=True)

elif module=="audit":
    require("audit")
    st.subheader("🕵️ Audit Trail")
    df=q("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200")
    st.dataframe(df,use_container_width=True,hide_index=True)

elif module=="backup":
    require("backup")
    st.subheader("💾 Backup & Restore Database")
    st.write(f"Database: `{DB.name}`")
    if st.button("📦 Buat Backup Sekarang",type="primary"):
        fn=BACKUP_DIR/f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(DB,fn); audit("BACKUP","backup",detail=fn.name); st.success(f"Backup dibuat: {fn.name}")
    backups=sorted(BACKUP_DIR.glob("*.db"),reverse=True)
    if backups:
        st.markdown("### Backup tersedia")
        for b in backups[:20]:
            st.write(f"• {b.name} — {b.stat().st_size:,} bytes")
            with open(b,"rb") as f: st.download_button(f"Download {b.name}",f.read(),b.name,"application/octet-stream",key=b.name)
    st.warning("Restore otomatis belum diaktifkan pada v3 untuk mencegah overwrite database aktif secara tidak sengaja. Restore dapat dilakukan dengan mengganti file DB saat aplikasi berhenti.")
