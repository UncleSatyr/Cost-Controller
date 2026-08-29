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
            un = a.text_input("Username *", placeholder="Masukkan username")
            pw = b.text_input("Password *", type="password", placeholder="Minimal 8 karakter")
            rr = c.selectbox("Role *", ["Admin","Manager","Finance","Viewer"])
            
            if st.button("Simpan User", type="primary", key="btn_create_usr"):
                if not un.strip() or len(pw) < 8:
                    st.error("Username wajib diisi dan password minimal 8 karakter.")
                else:
                    s, lid, err = execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
                                          (un, hash_pw(pw), rr, now()))
                    if s: 
                        audit("CREATE", "users", "users", lid, un)
                        st.success("User berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(err)
        else: st.info("Anda tidak memiliki hak akses untuk menambah User.")
        
    with tab2:
        if users.empty:
            st.info("Belum ada data user.")
        else:
            psel = st.selectbox("Pilih User", users.id.tolist(), format_func=lambda x: users.loc[users.id==x, "username"].iloc[0], key="sel_usr")
            sel = users.loc[users.id==psel].iloc[0]
            
            if perm("users","edit"):
                a, b, c = st.columns(3)
                e_un = a.text_input("Username *", sel.username, key="eu_un")
                e_rr = b.selectbox("Role *", ["Admin","Manager","Finance","Viewer"], index=["Admin","Manager","Finance","Viewer"].index(sel.role), key="eu_rr")
                e_act = c.checkbox("Akun Aktif (Bisa Login)", value=bool(sel.active), key="eu_act")
                
                if st.button("Update User", type="primary", key="btn_upd_usr"):
                    if not e_un.strip():
                        st.error("Username wajib diisi!")
                    else:
                        s, _, err = execute("UPDATE users SET username=?, role=?, active=? WHERE id=?", 
                                            (e_un, e_rr, int(e_act), psel))
                        if s: 
                            audit("UPDATE", "users", "users", psel, e_un)
                            st.success("User berhasil diperbarui!")
                            st.rerun()
                        else: st.error(err)
                        
            if perm("users","delete"):
                st.write("")
                with st.expander("⚠️ Hapus User"):
                    st.warning("User yang dihapus tidak dapat mengakses sistem lagi.")
                    if st.button("Hapus Secara Permanen", type="primary", key="btn_del_usr"):
                        if sel.username == "admin":
                            st.error("Gagal: Tidak dapat menghapus user admin default.")
                        else:
                            s, _, err = execute("DELETE FROM users WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "users", "users", psel)
                                st.success("User berhasil dihapus!")
                                st.rerun()
                            else: st.error(err)

st.markdown("#### 📋 Daftar Pengguna")
disp = users.copy()
disp = disp.rename(columns={
    "id": "ID", "username": "Username", "role": "Role (Peran)",
    "active": "Status Aktif", "must_change_password": "Harus Ganti Password",
    "created_at": "Tanggal Dibuat"
})
st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("#### 🔐 Matriks Hak Akses Modul")
p = q("SELECT * FROM permissions ORDER BY role,module")
disp_p = p.copy()
disp_p = disp_p.rename(columns={
    "id": "ID", "role": "Role", "module": "Nama Modul",
    "can_read": "Read (Melihat)", "can_create": "Create (Menambah)",
    "can_edit": "Edit (Mengubah)", "can_delete": "Delete (Menghapus)"
})
st.dataframe(disp_p, use_container_width=True, hide_index=True)
