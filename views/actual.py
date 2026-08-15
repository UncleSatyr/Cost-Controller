import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("actual")
st.subheader("💸 Actual Cost + Approval")

pid, project = get_active_project()
df = q("SELECT * FROM actual_costs WHERE project_id=? ORDER BY id DESC", (pid,)) if pid else pd.DataFrame()

if project is not None and (perm("actual","create") or perm("actual","edit") or perm("actual","delete")):
    tab1, tab2 = st.tabs(["➕ Tambah Actual Cost", "✏️ Edit / Hapus Actual"])
    with tab1:
        if perm("actual","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            dt = a.date_input("Tanggal", date.today())
            cat = b.text_input("Kategori", placeholder="Misal: Operasional")
            vendor = c.text_input("Vendor", placeholder="Nama Toko/Supplier")
            desc = a.text_input("Deskripsi", placeholder="Keterangan pengeluaran")
            amount = b.number_input("Amount (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Contoh: 150000")
            with b: render_live_format(amount)
            if st.button("Tambah Actual", type="primary", key="btn_create_act"):
                s, lid, err = execute("INSERT INTO actual_costs(project_id,date,category,description,vendor,amount) VALUES(?,?,?,?,?,?)",
                                      (pid, str(dt), cat, desc, vendor, amount or 0))
                if s: 
                    audit("CREATE", "actual", "actual_costs", lid, str(amount))
                    st.rerun()
                else: st.error(err)
        else: st.info("Akses ditolak.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data actual cost.")
        else:
            psel = st.selectbox("Pilih Actual Cost", df.id.tolist(), key="sel_act", format_func=lambda x: f"{df.loc[df.id==x,'date'].iloc[0]} - {df.loc[df.id==x,'description'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            if sel.approval_status == 'Approved':
                st.warning("Data sudah diapprove, tidak dapat diubah.")
            else:
                if perm("actual","edit"):
                    st.info(FORM_INSTRUCTION)
                    e_dt = st.date_input("Tanggal", datetime.strptime(sel.date, "%Y-%m-%d").date() if sel.date else date.today(), key="ea_d")
                    e_cat = st.text_input("Kategori", sel.category, key="ea_c")
                    e_ven = st.text_input("Vendor", sel.vendor, key="ea_v")
                    e_desc = st.text_input("Deskripsi", sel.description, key="ea_de")
                    e_amt = st.number_input("Amount (Rp)", 0., value=float(sel.amount), help=CURRENCY_HELP, key="ea_a")
                    render_live_format(e_amt)
                    if st.button("Update Actual", key="btn_upd_act"):
                        s, _, err = execute("UPDATE actual_costs SET date=?, category=?, vendor=?, description=?, amount=? WHERE id=?", 
                                            (str(e_dt), e_cat, e_ven, e_desc, e_amt, psel))
                        if s: 
                            audit("UPDATE", "actual", "actual_costs", psel, str(e_amt))
                            st.rerun()
                        else: st.error(err)
                if perm("actual","delete"):
                    if st.button("Hapus Actual Terpilih", key="btn_del_act"):
                        s, _, err = execute("DELETE FROM actual_costs WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "actual", "actual_costs", psel)
                            st.rerun()
                        else: st.error(err)

if not df.empty:
    st.markdown("---")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("Total Actual", money(df.amount.sum()))
