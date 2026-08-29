import streamlit as st
from streamlit_cookies_controller import CookieController
from utils import perm, audit

st.set_page_config(page_title="Project Cost Control System v3", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

hide_github_icon = """
<style>
/* Sembunyikan header bawaan Streamlit (termasuk icon GitHub) seperti permintaan User */
header {visibility: hidden !important;}

/* Sembunyikan tombol "X" atau "<" untuk menutup sidebar agar user tidak terjebak */
[data-testid="stSidebarCollapseButton"] {display: none !important;}
section[data-testid="stSidebar"] button[kind="header"] {display: none !important;}

/* Perkecil ukuran font angka di st.metric agar tidak terpotong */
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
}
</style>
"""
st.markdown(hide_github_icon, unsafe_allow_html=True)

controller = CookieController()
st.session_state["cookie_controller"] = controller

# Mencegah glitch render halaman login selama sepersekian detik
# saat komponen CookieController sedang membaca cookie di latar belakang
if "app_loaded" not in st.session_state:
    st.session_state.app_loaded = True
    st.markdown("<div style='text-align: center; margin-top: 20vh;'><h3>Memuat sistem...</h3></div>", unsafe_allow_html=True)
    import time
    time.sleep(0.5)
    st.rerun()

if "user" not in st.session_state:
    st.session_state.user = None

cookie_user = None
if st.session_state.user is None:
    try:
        cookie_user = controller.get("auth_username")
    except TypeError:
        cookie_user = None

if st.session_state.user is None and cookie_user:
    from utils import q
    r = q("SELECT * FROM users WHERE username=%s AND active=1", (cookie_user,))
    
    if not r.empty:
        st.session_state.user = {"id": int(r.iloc[0].id), "username": r.iloc[0].username, "role": r.iloc[0].role, "must_change": int(r.iloc[0].must_change_password)}
        st.rerun()
if st.session_state.user is None:
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
    st.logo("logo-01.webp")
    st.sidebar.success(f"👤 {user['username']} • {role}")
    
    from utils import q
    projects = q("SELECT * FROM projects ORDER BY id DESC")
    if not projects.empty:
        st.sidebar.selectbox("PROYEK AKTIF", projects.id.tolist(), key="active_project_selector", format_func=lambda x: projects.loc[projects.id==x,"name"].iloc[0])
        
    if st.sidebar.button("Logout"):
        audit("LOGOUT", "auth")
        controller.remove("auth_username")
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.markdown("<div style='text-align: center; color: gray; font-size: 0.85em; margin-top: 10px; margin-bottom: 20px;'>✨ Upscaled & Enhanced by <br><b>UncleSatyr</b></div>", unsafe_allow_html=True)
        
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
