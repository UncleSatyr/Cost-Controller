import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("payable")
st.subheader("🏦 Hutang Vendor")

pid, project = get_active_project()
df = q("SELECT * FROM vendor_payables WHERE project_id=?", (pid,)) if pid else pd.DataFrame()

if project is not None and (perm("payable","create") or perm("payable","edit") or perm("payable","delete")):
    tab1, tab2 = st.tabs(["➕ Tambah Hutang", "✏️ Edit / Hapus Hutang"])
    with tab1:
        if perm("payable","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            vendor = a.text_input("Vendor", placeholder="Nama Vendor")
            bill = b.text_input("No Tagihan", placeholder="Nomor Tagihan/Kwitansi")
            bd = c.date_input("Bill Date", date.today())
            due = a.date_input("Due Date", date.today())
            amount = b.number_input("Amount (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Total Hutang")
            with b: render_live_format(amount)
            paid = c.number_input("Paid (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Telah Dibayar")
            with c: render_live_format(paid)
            if st.button("Tambah Hutang", type="primary", key="btn_create_pay"):
                s, lid, err = execute("INSERT INTO vendor_payables(project_id,vendor,bill_no,bill_date,due_date,amount,paid_amount) VALUES(?,?,?,?,?,?,?)",
                                      (pid, vendor, bill, str(bd), str(due), amount or 0, paid or 0))
                if s: 
                    audit("CREATE", "payable", "vendor_payables", lid, bill)
                    st.rerun()
                else: st.error(err)
        else: st.info("Akses ditolak.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data hutang.")
        else:
            psel = st.selectbox("Pilih Hutang", df.id.tolist(), key="sel_pay", format_func=lambda x: f"{df.loc[df.id==x,'bill_no'].iloc[0]} - {df.loc[df.id==x,'vendor'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            if sel.approval_status == 'Approved':
                st.warning("Data sudah diapprove, tidak dapat diubah.")
            else:
                if perm("payable","edit"):
                    st.info(FORM_INSTRUCTION)
                    e_ven = st.text_input("Vendor", sel.vendor, key="epay_v")
                    e_bill = st.text_input("No Tagihan", sel.bill_no, key="epay_b")
                    e_bd = st.date_input("Bill Date", datetime.strptime(sel.bill_date, "%Y-%m-%d").date() if sel.bill_date else date.today(), key="epay_d1")
                    e_due = st.date_input("Due Date", datetime.strptime(sel.due_date, "%Y-%m-%d").date() if sel.due_date else date.today(), key="epay_d2")
                    e_amt = st.number_input("Amount (Rp)", 0., value=float(sel.amount), help=CURRENCY_HELP, key="epay_a")
                    render_live_format(e_amt)
                    e_paid = st.number_input("Paid (Rp)", 0., value=float(sel.paid_amount), help=CURRENCY_HELP, key="epay_p")
                    render_live_format(e_paid)
                    if st.button("Update Hutang", key="btn_upd_pay"):
                        s, _, err = execute("UPDATE vendor_payables SET vendor=?, bill_no=?, bill_date=?, due_date=?, amount=?, paid_amount=? WHERE id=?", 
                                            (e_ven, e_bill, str(e_bd), str(e_due), e_amt, e_paid, psel))
                        if s: 
                            audit("UPDATE", "payable", "vendor_payables", psel, e_bill)
                            st.rerun()
                        else: st.error(err)
                if perm("payable","delete"):
                    if st.button("Hapus Hutang Terpilih", key="btn_del_pay"):
                        s, _, err = execute("DELETE FROM vendor_payables WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "payable", "vendor_payables", psel)
                            st.rerun()
                        else: st.error(err)

if not df.empty:
    st.markdown("---")
    df["outstanding"] = df.amount - df.paid_amount
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("Hutang Outstanding", money(df.outstanding.sum()))
