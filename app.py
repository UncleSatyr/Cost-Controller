import streamlit as st
from streamlit_cookies_controller import CookieController
from utils import perm, audit, init_db

st.set_page_config(page_title="Project Cost Control System v3", page_icon="🏗️", layout="wide")

init_db()

controller = CookieController()
st.session_state["cookie_controller"] = controller

# Mencegah glitch render halaman login selama sepersekian detik
# saat komponen CookieController sedang membaca cookie di latar belakang
if "app_loaded" not in st.session_state:
    st.session_state.app_loaded = True
    st.markdown("<div style='text-align: center; margin-top: 20vh;'><h3>Memuat sistem...</h3></div>", unsafe_allow_html=True)
    st.stop()

if "user" not in st.session_state:
    st.session_state.user = None

cookie_user = controller.get("auth_username")
# Handle auto-login routing
if st.session_state.user is None and cookie_user:
    # Just render login page, it will handle auto-hydration and rerun
    pg = st.navigation([st.Page("views/login.py", title="Login", icon="🔐")])
    pg.run()
    st.stop()

# Build Navigation
pages = {}
user = st.session_state.user

if user is None or user.get("must_change"):
    pg = st.navigation([st.Page("views/login.py", title="Login", icon="🔐")])
else:
    # Build sidebar based on permissions
    role = user["role"]
    st.sidebar.success(f"👤 {user['username']} • {role}")
    if st.sidebar.button("Logout"):
        audit("LOGOUT", "auth")
        controller.remove("auth_username")
        st.session_state.user = None
        st.rerun()
        
    pages["Utama"] = []
    if perm("dashboard", "view"): pages["Utama"].append(st.Page("views/dashboard.py", title="Dashboard", icon="📊"))
    if perm("projects", "view"): pages["Utama"].append(st.Page("views/projects.py", title="Proyek", icon="🏗️"))
    if perm("progress", "view"): pages["Utama"].append(st.Page("views/progress.py", title="Progress", icon="📈"))
    
    pages["Keuangan"] = []
    if perm("rab", "view"): pages["Keuangan"].append(st.Page("views/rab.py", title="RAB", icon="📋"))
    if perm("actual", "view"): pages["Keuangan"].append(st.Page("views/actual.py", title="Actual Cost", icon="💸"))
    if perm("po", "view"): pages["Keuangan"].append(st.Page("views/po.py", title="PO / Procurement", icon="🧾"))
    if perm("invoice", "view"): pages["Keuangan"].append(st.Page("views/invoice.py", title="Invoice & Termin", icon="🧮"))
    if perm("receivable", "view"): pages["Keuangan"].append(st.Page("views/receivable.py", title="Piutang", icon="💰"))
    if perm("payable", "view"): pages["Keuangan"].append(st.Page("views/payable.py", title="Hutang Vendor", icon="🏦"))
    if perm("cashflow", "view"): pages["Keuangan"].append(st.Page("views/cashflow.py", title="Cash Flow", icon="💵"))
    
    pages["Analisis"] = []
    if perm("forecast", "view"): pages["Analisis"].append(st.Page("views/forecast.py", title="EAC / ETC", icon="🔮"))
    if perm("kpi", "view"): pages["Analisis"].append(st.Page("views/kpi.py", title="CPI / SPI", icon="📐"))
    
    pages["Sistem"] = []
    if perm("reports", "view"): pages["Sistem"].append(st.Page("views/reports.py", title="Reports", icon="📥"))
    if perm("users", "view"): pages["Sistem"].append(st.Page("views/users.py", title="Users & Permissions", icon="👥"))
    if perm("audit", "view"): pages["Sistem"].append(st.Page("views/audit.py", title="Audit Trail", icon="🕵️"))
    if perm("backup", "view"): pages["Sistem"].append(st.Page("views/backup.py", title="Backup Database", icon="💾"))
    
    # Filter empty categories
    pages = {k: v for k, v in pages.items() if v}
    
    if pages:
        pg = st.navigation(pages)
    else:
        st.error("Anda tidak memiliki akses ke modul mana pun.")
        st.stop()

pg.run()
