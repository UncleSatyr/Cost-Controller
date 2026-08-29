import streamlit as st
import pandas as pd
from datetime import date
from utils import q, execute, audit, now, require, perm, money, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("projects")
st.subheader("🏗️ Manajemen Proyek")

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
                        st.success("Proyek berhasil ditambahkan!")
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
                a,b = st.columns(2)
                nm = a.text_input("Nama Proyek *", p.name, key="ep_nm")
                cust = b.text_input("Customer", p.customer if pd.notna(p.customer) else "", key="ep_cust")
                
                cv = a.number_input("Nilai Kontrak (Rp)", value=float(p.contract_value), help=CURRENCY_HELP, key="ep_cv")
                with a: render_live_format(cv)
                p_pic = b.text_input("PIC", p.pic if pd.notna(p.pic) else "", key="ep_pic")
                
                try: s_date = pd.to_datetime(p.start_date).date() if pd.notna(p.start_date) else date.today()
                except: s_date = date.today()
                st_date = a.date_input("Tanggal Mulai", s_date, key="ep_start")
                
                try: e_date = pd.to_datetime(p.end_date).date() if pd.notna(p.end_date) else date.today()
                except: e_date = date.today()
                en_date = b.date_input("Target Selesai", e_date, key="ep_end")
                
                stt = st.selectbox("Status", ["Active","Completed","On Hold","Cancelled"], index=["Active","Completed","On Hold","Cancelled"].index(p.status) if p.status in ["Active","Completed","On Hold","Cancelled"] else 0, key="ep_stt")
                
                c1, c2 = st.columns([1,4])
                with c1:
                    if st.button("Update Proyek", type="primary", key="btn_upd_proj"):
                        if not nm.strip():
                            st.error("Nama Proyek wajib diisi!")
                        else:
                            s, _, e = execute("UPDATE projects SET name=?, customer=?, contract_value=?, start_date=?, end_date=?, pic=?, status=?, updated_at=? WHERE id=?", 
                                (nm, cust, cv, str(st_date), str(en_date), p_pic, stt, now(), psel))
                            if s: 
                                audit("UPDATE", "projects", "projects", psel, nm)
                                st.success("Proyek berhasil diupdate!")
                                st.rerun()
                            else: st.error(e)
            
            if perm("projects","delete"):
                st.write("") # spacer
                with st.expander("⚠️ Hapus Proyek (Berbahaya)"):
                    st.warning("Menghapus proyek akan menghilangkan seluruh data yang terhubung ke proyek ini (RAB, Actual Cost, dll) jika database tidak dikonfigurasi dengan relasi pelindung.")
                    if st.button("Hapus Proyek Secara Permanen", type="primary", key="btn_del_proj"):
                        s, _, e = execute("DELETE FROM projects WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "projects", "projects", psel)
                            st.success("Proyek berhasil dihapus!")
                            st.rerun()
                        else: st.error(e)

if not projects.empty:
    st.markdown("#### 📋 Daftar Proyek")
    disp = projects.copy()
    disp["contract_value"] = disp["contract_value"].apply(lambda x: money(x))
    disp = disp.rename(columns={
        "id": "ID", "name": "Nama Proyek", "customer": "Customer",
        "contract_value": "Nilai Kontrak", "start_date": "Tgl Mulai",
        "end_date": "Target Selesai", "pic": "PIC", "status": "Status",
        "created_at": "Dibuat", "updated_at": "Diupdate"
    })
    st.dataframe(disp, hide_index=True)
