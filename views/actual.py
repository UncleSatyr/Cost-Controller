import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, now, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("actual")

pid, project = get_active_project()
st.subheader(f"💸 Actual Cost + Approval — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM actual_costs WHERE project_id=%s ORDER BY id DESC", (pid,)) if pid else pd.DataFrame()

user = st.session_state.get("user")
role = user["role"] if user else ""

if perm("actual","create") or perm("actual","edit") or perm("actual","delete") or role in ["Admin","Manager"]:
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Actual Cost", "✏️ Edit / Hapus Actual", "✅ Approval"])
    
    with tab1:
        if perm("actual","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            dt = a.date_input("Tanggal *", date.today())
            cat = b.text_input("Kategori", placeholder="Misal: Operasional")
            vendor = c.text_input("Vendor", placeholder="Nama Toko/Supplier")
            
            d, e, f = st.columns(3)
            desc = d.text_input("Deskripsi *", placeholder="Keterangan pengeluaran")
            amount = e.number_input("Amount (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Contoh: 150000")
            with e: render_live_format(amount)
            
            if st.button("Simpan Actual Cost", type="primary", key="btn_create_act"):
                if not desc.strip():
                    st.error("Deskripsi wajib diisi!")
                else:
                    s, lid, err = execute("INSERT INTO actual_costs(project_id,date,category,description,vendor,amount) VALUES(?,?,?,?,?,?)",
                                          (pid, str(dt), cat, desc, vendor, amount or 0))
                    if s: 
                        audit("CREATE", "actual", "actual_costs", lid, str(amount))
                        st.success("Data Actual Cost berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(err)
        else: st.info("Anda tidak memiliki hak akses untuk menambah actual cost.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data Actual Cost untuk proyek ini.")
        else:
            psel = st.selectbox("Pilih Actual Cost", df.id.tolist(), key="sel_act", format_func=lambda x: f"{df.loc[df.id==x,'date'].iloc[0]} - {df.loc[df.id==x,'description'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            
            if sel.approval_status == 'Approved':
                st.warning("Data ini sudah disetujui (Approved) dan tidak dapat diubah lagi.")
            else:
                if perm("actual","edit"):
                    st.info(FORM_INSTRUCTION)
                    a, b, c = st.columns(3)
                    e_dt = a.date_input("Tanggal *", datetime.strptime(sel.date, "%Y-%m-%d").date() if sel.date else date.today(), key="ea_d")
                    e_cat = b.text_input("Kategori", sel.category if pd.notna(sel.category) else "", key="ea_c")
                    e_ven = c.text_input("Vendor", sel.vendor if pd.notna(sel.vendor) else "", key="ea_v")
                    
                    d, e, f = st.columns(3)
                    e_desc = d.text_input("Deskripsi *", sel.description, key="ea_de")
                    e_amt = e.number_input("Amount (Rp)", 0., value=float(sel.amount), help=CURRENCY_HELP, key="ea_a")
                    with e: render_live_format(e_amt)
                    
                    if st.button("Update Actual Cost", type="primary", key="btn_upd_act"):
                        if not e_desc.strip():
                            st.error("Deskripsi wajib diisi!")
                        else:
                            s, _, err = execute("UPDATE actual_costs SET date=?, category=?, vendor=?, description=?, amount=? WHERE id=?", 
                                                (str(e_dt), e_cat, e_ven, e_desc, e_amt, psel))
                            if s: 
                                audit("UPDATE", "actual", "actual_costs", psel, str(e_amt))
                                st.success("Data Actual Cost berhasil diperbarui!")
                                st.rerun()
                            else: st.error(err)
                            
                if perm("actual","delete"):
                    st.write("")
                    with st.expander("⚠️ Hapus Actual Cost"):
                        st.warning("Data Actual Cost yang dihapus tidak dapat dikembalikan.")
                        if st.button("Hapus Secara Permanen", type="primary", key="btn_del_act"):
                            s, _, err = execute("DELETE FROM actual_costs WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "actual", "actual_costs", psel)
                                st.success("Actual Cost berhasil dihapus!")
                                st.rerun()
                            else: st.error(err)
                            
    with tab3:
        if role in ["Admin","Manager"]:
            if df.empty or df[df.approval_status != 'Approved'].empty:
                st.success("Tidak ada Actual Cost yang menunggu persetujuan.")
            else:
                rid = st.selectbox("Pilih Actual Cost untuk disetujui", df[df.approval_status != 'Approved'].id.tolist(), key="sel_appr_act", format_func=lambda x: f"{df.loc[df.id==x,'date'].iloc[0]} - {df.loc[df.id==x,'description'].iloc[0]}")
                if rid and st.button("Approve Actual Cost", type="primary", key="btn_appr_act"):
                    s, _, err = execute("UPDATE actual_costs SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?", (user["username"], now(), rid))
                    if s: 
                        audit("APPROVE", "actual", "actual_costs", rid)
                        st.success("Actual Cost berhasil disetujui!")
                        st.rerun()
                    else: st.error(err)
        else: 
            st.info("Hanya Admin atau Manager yang dapat memberikan persetujuan.")

if not df.empty:
    st.markdown("#### 📋 Daftar Actual Cost")
    disp = df.copy()
    disp["amount"] = disp["amount"].apply(lambda x: money(x))
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "date": "Tanggal",
        "category": "Kategori", "vendor": "Vendor", "description": "Deskripsi",
        "amount": "Total Amount", "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    st.dataframe(disp, hide_index=True)
    st.metric("Grand Total Actual Cost", money(df.amount.sum()))
