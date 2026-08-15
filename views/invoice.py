import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("invoice")
st.subheader("🧮 Invoice & Termin + Approval")

pid, project = get_active_project()
df = q("SELECT * FROM invoices WHERE project_id=?", (pid,)) if pid else pd.DataFrame()

if project is not None and (perm("invoice","create") or perm("invoice","edit") or perm("invoice","delete")):
    tab1, tab2 = st.tabs(["➕ Tambah Invoice", "✏️ Edit / Hapus Invoice"])
    with tab1:
        if perm("invoice","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            no = a.text_input("Invoice/Termin", placeholder="Nomor Invoice")
            cust = b.text_input("Customer", placeholder="Klien")
            inv = a.date_input("Invoice Date", date.today())
            due = c.date_input("Due Date", date.today())
            amount = b.number_input("Amount (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Nilai Invoice")
            with b: render_live_format(amount)
            paid = c.number_input("Paid (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Telah Dibayar")
            with c: render_live_format(paid)
            if st.button("Tambah Invoice", type="primary", key="btn_create_inv"):
                s, lid, err = execute("INSERT INTO invoices(project_id,invoice_no,customer,invoice_date,due_date,amount,paid_amount) VALUES(?,?,?,?,?,?,?)",
                                      (pid, no, cust, str(inv), str(due), amount or 0, paid or 0))
                if s: 
                    audit("CREATE", "invoice", "invoices", lid, no)
                    st.rerun()
                else: st.error(err)
        else: st.info("Akses ditolak.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data invoice.")
        else:
            psel = st.selectbox("Pilih Invoice", df.id.tolist(), key="sel_inv", format_func=lambda x: df.loc[df.id==x,"invoice_no"].iloc[0])
            sel = df.loc[df.id==psel].iloc[0]
            if sel.approval_status == 'Approved':
                st.warning("Data sudah diapprove, tidak dapat diubah.")
            else:
                if perm("invoice","edit"):
                    st.info(FORM_INSTRUCTION)
                    e_no = st.text_input("Invoice/Termin", sel.invoice_no, key="einv_no")
                    e_cust = st.text_input("Customer", sel.customer, key="einv_c")
                    e_inv = st.date_input("Invoice Date", datetime.strptime(sel.invoice_date, "%Y-%m-%d").date() if sel.invoice_date else date.today(), key="einv_d1")
                    e_due = st.date_input("Due Date", datetime.strptime(sel.due_date, "%Y-%m-%d").date() if sel.due_date else date.today(), key="einv_d2")
                    e_amt = st.number_input("Amount (Rp)", 0., value=float(sel.amount), help=CURRENCY_HELP, key="einv_a")
                    render_live_format(e_amt)
                    e_paid = st.number_input("Paid (Rp)", 0., value=float(sel.paid_amount), help=CURRENCY_HELP, key="einv_p")
                    render_live_format(e_paid)
                    if st.button("Update Invoice", key="btn_upd_inv"):
                        s, _, err = execute("UPDATE invoices SET invoice_no=?, customer=?, invoice_date=?, due_date=?, amount=?, paid_amount=? WHERE id=?", 
                                            (e_no, e_cust, str(e_inv), str(e_due), e_amt, e_paid, psel))
                        if s: 
                            audit("UPDATE", "invoice", "invoices", psel, e_no)
                            st.rerun()
                        else: st.error(err)
                if perm("invoice","delete"):
                    if st.button("Hapus Invoice Terpilih", key="btn_del_inv"):
                        s, _, err = execute("DELETE FROM invoices WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "invoice", "invoices", psel)
                            st.rerun()
                        else: st.error(err)

if not df.empty:
    st.markdown("---")
    df["outstanding"] = df.amount - df.paid_amount
    st.dataframe(df, use_container_width=True, hide_index=True)
