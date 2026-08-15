import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("po")
st.subheader("🧾 PO / Procurement + Approval")

pid, project = get_active_project()
df = q("SELECT * FROM purchase_orders WHERE project_id=?", (pid,)) if pid else pd.DataFrame()

if project is not None and (perm("po","create") or perm("po","edit") or perm("po","delete")):
    tab1, tab2 = st.tabs(["➕ Tambah PO", "✏️ Edit / Hapus PO"])
    with tab1:
        if perm("po","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            no = a.text_input("PO No", placeholder="Nomor PO")
            vendor = b.text_input("Vendor", placeholder="Nama Vendor")
            dt = c.date_input("Tanggal", date.today())
            desc = a.text_input("Deskripsi", placeholder="Keterangan")
            value = b.number_input("Nilai PO (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Total PO")
            with b: render_live_format(value)
            paid = c.number_input("Paid (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Sudah Dibayar")
            with c: render_live_format(paid)
            if st.button("Tambah PO", type="primary", key="btn_create_po"):
                s, lid, err = execute("INSERT INTO purchase_orders(project_id,po_no,vendor,date,description,po_value,paid_value) VALUES(?,?,?,?,?,?,?)",
                                      (pid, no, vendor, str(dt), desc, value or 0, paid or 0))
                if s: 
                    audit("CREATE", "po", "purchase_orders", lid, no)
                    st.rerun()
                else: st.error(err)
        else: st.info("Akses ditolak.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data PO.")
        else:
            psel = st.selectbox("Pilih PO", df.id.tolist(), key="sel_po", format_func=lambda x: f"{df.loc[df.id==x,'po_no'].iloc[0]} - {df.loc[df.id==x,'vendor'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            if sel.approval_status == 'Approved':
                st.warning("Data sudah diapprove, tidak dapat diubah.")
            else:
                if perm("po","edit"):
                    st.info(FORM_INSTRUCTION)
                    e_no = st.text_input("PO No", sel.po_no, key="epo_no")
                    e_ven = st.text_input("Vendor", sel.vendor, key="epo_ven")
                    e_dt = st.date_input("Tanggal", datetime.strptime(sel.date, "%Y-%m-%d").date() if sel.date else date.today(), key="epo_dt")
                    e_desc = st.text_input("Deskripsi", sel.description, key="epo_d")
                    e_val = st.number_input("Nilai PO (Rp)", 0., value=float(sel.po_value), help=CURRENCY_HELP, key="epo_v")
                    render_live_format(e_val)
                    e_paid = st.number_input("Paid (Rp)", 0., value=float(sel.paid_value), help=CURRENCY_HELP, key="epo_p")
                    render_live_format(e_paid)
                    if st.button("Update PO", key="btn_upd_po"):
                        s, _, err = execute("UPDATE purchase_orders SET po_no=?, vendor=?, date=?, description=?, po_value=?, paid_value=? WHERE id=?", 
                                            (e_no, e_ven, str(e_dt), e_desc, e_val, e_paid, psel))
                        if s: 
                            audit("UPDATE", "po", "purchase_orders", psel, e_no)
                            st.rerun()
                        else: st.error(err)
                if perm("po","delete"):
                    if st.button("Hapus PO Terpilih", key="btn_del_po"):
                        s, _, err = execute("DELETE FROM purchase_orders WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "po", "purchase_orders", psel)
                            st.rerun()
                        else: st.error(err)

if not df.empty:
    st.markdown("---")
    df["outstanding"] = df.po_value - df.paid_value
    st.dataframe(df, use_container_width=True, hide_index=True)
