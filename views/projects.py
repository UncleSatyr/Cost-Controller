import streamlit as st
import pandas as pd
from datetime import date
from utils import q, execute, audit, now, require, perm, money, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("projects")
st.subheader("🏗️ Database Proyek")

projects = q("SELECT * FROM projects ORDER BY id DESC")

if perm("projects","create") or perm("projects","edit") or perm("projects","delete"):
    tab1, tab2 = st.tabs(["➕ Tambah Proyek Baru", "✏️ Edit / Hapus Proyek"])
    with tab1:
        if perm("projects","create"):
            st.info(FORM_INSTRUCTION)
            a,b = st.columns(2)
            name = a.text_input("Nama Proyek *", placeholder="Contoh: Pembangunan Gudang")
            customer = b.text_input("Customer", placeholder="Nama Perusahaan/Klien")
            contract = a.number_input("Nilai Kontrak (Rp)", value=None, step=100000.0, help=CURRENCY_HELP, placeholder="Contoh: 15000000")
            with a: render_live_format(contract)
            pic = b.text_input("PIC", placeholder="Nama Penanggung Jawab")
            start = a.date_input("Tanggal Mulai", date.today())
            end = b.date_input("Target Selesai", date.today())
            status = st.selectbox("Status", ["Active","Completed","On Hold","Cancelled"])
            if st.button("Simpan Proyek", type="primary", key="btn_create_proj"):
                if not name.strip():
                    st.error("Nama Proyek wajib diisi!")
                else:
                    s, lid, e = execute("INSERT INTO projects(name,customer,contract_value,start_date,end_date,pic,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                            (name, customer, contract or 0, str(start), str(end), pic, status, now(), now()))
                    if s: 
                        audit("CREATE", "projects", "projects", lid, name)
                        st.rerun()
                    else: st.error(e)
        else: st.info("Anda tidak memiliki hak akses untuk menambah proyek.")
        
    with tab2:
        if projects.empty:
            st.info("Belum ada proyek yang dapat diedit.")
        else:
            psel = st.selectbox("Pilih Proyek", projects.id.tolist(), key="sel_proj", format_func=lambda x: projects.loc[projects.id==x,"name"].iloc[0])
            p = projects.loc[projects.id==psel].iloc[0]
            if perm("projects","edit"):
                st.info(FORM_INSTRUCTION)
                nm = st.text_input("Nama", p.name, key="ep_nm")
                cv = st.number_input("Nilai Kontrak (Rp)", value=float(p.contract_value), help=CURRENCY_HELP, key="ep_cv")
                render_live_format(cv)
                stt = st.selectbox("Status", ["Active","Completed","On Hold","Cancelled"], index=["Active","Completed","On Hold","Cancelled"].index(p.status), key="ep_stt")
                if st.button("Update Proyek", key="btn_upd_proj"):
                    s, _, e = execute("UPDATE projects SET name=?,contract_value=?,status=?,updated_at=? WHERE id=?", (nm, cv, stt, now(), psel))
                    if s: 
                        audit("UPDATE", "projects", "projects", psel, nm)
                        st.rerun()
                    else: st.error(e)
            if perm("projects","delete"):
                if st.button("🗑️ Hapus Proyek Terpilih", key="btn_del_proj"):
                    s, _, e = execute("DELETE FROM projects WHERE id=?", (psel,))
                    if s: 
                        audit("DELETE", "projects", "projects", psel)
                        st.rerun()
                    else: st.error(e)

if not projects.empty:
    st.markdown("---")
    st.dataframe(projects, use_container_width=True, hide_index=True)
