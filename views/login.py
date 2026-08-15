import streamlit as st
from streamlit_cookies_controller import CookieController
from utils import q, hp, audit, execute, init_db

init_db()

controller = CookieController()

if "user" not in st.session_state:
    st.session_state.user = None

cookie_user = controller.get("auth_username")

if st.session_state.user is None and cookie_user:
    r = q("SELECT * FROM users WHERE username=? AND active=1", (cookie_user,))
    if not r.empty:
        st.session_state.user = {"id": int(r.iloc[0].id), "username": r.iloc[0].username, "role": r.iloc[0].role, "must_change": int(r.iloc[0].must_change_password)}
        st.rerun()

st.title("🔐 Project Cost Control System V3 Production")

if st.session_state.user is None:
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login", type="primary"):
            r = q("SELECT * FROM users WHERE username=? AND password_hash=? AND active=1", (u, hp(p)))
            if not r.empty:
                st.session_state.user = {"id": int(r.iloc[0].id), "username": r.iloc[0].username, "role": r.iloc[0].role, "must_change": int(r.iloc[0].must_change_password)}
                controller.set("auth_username", r.iloc[0].username, max_age=86400*7)
                audit("LOGIN", "auth", detail="Successful login")
                st.rerun()
            else: 
                st.error("Username atau password salah.")
    st.info("Default: admin / admin123. Sistem akan meminta penggantian password pada login pertama.")
else:
    user = st.session_state.user
    if user.get("must_change"):
        st.warning("⚠️ Anda wajib mengganti password sebelum melanjutkan.")
        with st.form("change_pw"):
            old = st.text_input("Password lama", type="password")
            new = st.text_input("Password baru", type="password")
            confirm = st.text_input("Konfirmasi password", type="password")
            if st.form_submit_button("Ubah Password", type="primary"):
                r = q("SELECT password_hash FROM users WHERE id=?", (user["id"],))
                if r.empty or r.iloc[0].password_hash != hp(old): 
                    st.error("Password lama salah.")
                elif len(new) < 8: 
                    st.error("Password minimal 8 karakter.")
                elif new != confirm: 
                    st.error("Konfirmasi password tidak sama.")
                else:
                    s, _, err = execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?", (hp(new), user["id"]))
                    if s:
                        audit("PASSWORD_CHANGE", "auth", "users", user["id"], "Initial password changed")
                        st.session_state.user["must_change"] = 0
                        st.success("Password berhasil diubah. Silakan masuk ke Dashboard.")
                        st.rerun()
                    else: 
                        st.error(err)
    else:
        st.success("Anda sudah login. Mengalihkan...")
        st.rerun()
