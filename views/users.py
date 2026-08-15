import streamlit as st
from utils import q, execute, audit, now, hash_pw, require, perm

require("users")
st.subheader("👥 User & Module Permissions")

users = q("SELECT id,username,role,active,must_change_password,created_at FROM users")

if perm("users","create") or perm("users","edit") or perm("users","delete"):
    tab1, tab2 = st.tabs(["➕ Tambah User", "✏️ Edit / Hapus User"])
    with tab1:
        if perm("users","create"):
            a, b, c = st.columns(3)
            un = a.text_input("Username", placeholder="Masukkan username")
            pw = b.text_input("Password", type="password", placeholder="Minimal 8 karakter")
            rr = c.selectbox("Role", ["Admin","Manager","Finance","Viewer"])
            if st.button("Tambah User", type="primary", key="btn_create_usr"):
                if not un.strip() or len(pw) < 8:
                    st.error("Username wajib diisi dan password minimal 8 karakter.")
                else:
                    s, lid, err = execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
                                          (un, hash_pw(pw), rr, now()))
                    if s: 
                        audit("CREATE", "users", "users", lid, un)
                        st.rerun()
                    else: st.error(err)
        else: st.info("Akses ditolak.")
        
    with tab2:
        if users.empty:
            st.info("Belum ada user.")
        else:
            psel = st.selectbox("Pilih User", users.id.tolist(), format_func=lambda x: users.loc[users.id==x, "username"].iloc[0], key="sel_usr")
            sel = users.loc[users.id==psel].iloc[0]
            if perm("users","edit"):
                e_un = st.text_input("Username", sel.username, key="eu_un")
                e_rr = st.selectbox("Role", ["Admin","Manager","Finance","Viewer"], index=["Admin","Manager","Finance","Viewer"].index(sel.role), key="eu_rr")
                e_act = st.checkbox("Active", value=bool(sel.active), key="eu_act")
                if st.button("Update User", key="btn_upd_usr"):
                    s, _, err = execute("UPDATE users SET username=?, role=?, active=? WHERE id=?", 
                                        (e_un, e_rr, int(e_act), psel))
                    if s: 
                        audit("UPDATE", "users", "users", psel, e_un)
                        st.rerun()
                    else: st.error(err)
            if perm("users","delete"):
                if st.button("Hapus User Terpilih", key="btn_del_usr"):
                    if sel.username == "admin":
                        st.error("Tidak dapat menghapus user admin default.")
                    else:
                        s, _, err = execute("DELETE FROM users WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "users", "users", psel)
                            st.rerun()
                        else: st.error(err)

st.markdown("---")
st.dataframe(users, use_container_width=True, hide_index=True)

st.markdown("### Hak Akses Modul")
p = q("SELECT * FROM permissions ORDER BY role,module")
st.dataframe(p, use_container_width=True, hide_index=True)
