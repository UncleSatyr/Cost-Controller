import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, now, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("invoice")

pid, project = get_active_project()
st.subheader(f"🧮 Invoice & Termin + Approval — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM invoices WHERE project_id=? ORDER BY id DESC", (pid,)) if pid else pd.DataFrame()

user = st.session_state.get("user")
role = user["role"] if user else ""

if perm("invoice","create") or perm("invoice","edit") or perm("invoice","delete") or role in ["Admin","Manager"]:
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Invoice", "✏️ Edit / Hapus Invoice", "✅ Approval"])
    
    with tab1:
        if perm("invoice","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            no = a.text_input("Nomor Invoice/Termin *", placeholder="Misal: INV-001")
            cust = b.text_input("Customer *", placeholder="Nama Klien")
            inv_date = c.date_input("Tanggal Invoice *", date.today())
            
            d, e, f = st.columns(3)
            due_date = d.date_input("Jatuh Tempo (Due Date) *", date.today())
            amount = e.number_input("Nilai Invoice (Rp) *", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Total Tagihan")
            with e: render_live_format(amount)
            paid = f.number_input("Sudah Dibayar (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Opsional")
            with f: render_live_format(paid)
            
            if st.button("Simpan Invoice", type="primary", key="btn_create_inv"):
                if not no.strip() or not cust.strip() or amount is None:
                    st.error("Nomor Invoice, Customer, dan Nilai Invoice wajib diisi!")
                else:
                    s, lid, err = execute("INSERT INTO invoices(project_id,invoice_no,customer,invoice_date,due_date,amount,paid_amount) VALUES(?,?,?,?,?,?,?)",
                                          (pid, no, cust, str(inv_date), str(due_date), amount or 0, paid or 0))
                    if s: 
                        audit("CREATE", "invoice", "invoices", lid, no)
                        st.success("Data Invoice berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(err)
        else: st.info("Anda tidak memiliki hak akses untuk menambah Invoice.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data Invoice untuk proyek ini.")
        else:
            psel = st.selectbox("Pilih Invoice", df.id.tolist(), key="sel_inv", format_func=lambda x: f"{df.loc[df.id==x,'invoice_no'].iloc[0]} - {df.loc[df.id==x,'customer'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            
            if sel.approval_status == 'Approved':
                st.warning("Data ini sudah disetujui (Approved) dan tidak dapat diubah lagi.")
            else:
                if perm("invoice","edit"):
                    st.info(FORM_INSTRUCTION)
                    a, b, c = st.columns(3)
                    e_no = a.text_input("Nomor Invoice/Termin *", sel.invoice_no, key="einv_no")
                    e_cust = b.text_input("Customer *", sel.customer if pd.notna(sel.customer) else "", key="einv_c")
                    e_inv = c.date_input("Tanggal Invoice *", datetime.strptime(sel.invoice_date, "%Y-%m-%d").date() if sel.invoice_date else date.today(), key="einv_d1")
                    
                    d, e, f = st.columns(3)
                    e_due = d.date_input("Jatuh Tempo (Due Date) *", datetime.strptime(sel.due_date, "%Y-%m-%d").date() if sel.due_date else date.today(), key="einv_d2")
                    e_amt = e.number_input("Nilai Invoice (Rp) *", 0., value=float(sel.amount), help=CURRENCY_HELP, key="einv_a")
                    with e: render_live_format(e_amt)
                    e_paid = f.number_input("Sudah Dibayar (Rp)", 0., value=float(sel.paid_amount), help=CURRENCY_HELP, key="einv_p")
                    with f: render_live_format(e_paid)
                    
                    if st.button("Update Invoice", type="primary", key="btn_upd_inv"):
                        if not e_no.strip() or not e_cust.strip():
                            st.error("Nomor Invoice dan Customer wajib diisi!")
                        else:
                            s, _, err = execute("UPDATE invoices SET invoice_no=?, customer=?, invoice_date=?, due_date=?, amount=?, paid_amount=? WHERE id=?", 
                                                (e_no, e_cust, str(e_inv), str(e_due), e_amt, e_paid, psel))
                            if s: 
                                audit("UPDATE", "invoice", "invoices", psel, e_no)
                                st.success("Data Invoice berhasil diperbarui!")
                                st.rerun()
                            else: st.error(err)
                            
                if perm("invoice","delete"):
                    st.write("")
                    with st.expander("⚠️ Hapus Invoice"):
                        st.warning("Data Invoice yang dihapus tidak dapat dikembalikan.")
                        if st.button("Hapus Secara Permanen", type="primary", key="btn_del_inv"):
                            s, _, err = execute("DELETE FROM invoices WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "invoice", "invoices", psel)
                                st.success("Invoice berhasil dihapus!")
                                st.rerun()
                            else: st.error(err)
                            
    with tab3:
        if role in ["Admin","Manager"]:
            if df.empty or df[df.approval_status != 'Approved'].empty:
                st.success("Tidak ada Invoice yang menunggu persetujuan.")
            else:
                rid = st.selectbox("Pilih Invoice untuk disetujui", df[df.approval_status != 'Approved'].id.tolist(), key="sel_appr_inv", format_func=lambda x: f"{df.loc[df.id==x,'invoice_no'].iloc[0]} - {df.loc[df.id==x,'customer'].iloc[0]}")
                if rid and st.button("Approve Invoice", type="primary", key="btn_appr_inv"):
                    s, _, err = execute("UPDATE invoices SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?", (user["username"], now(), rid))
                    if s: 
                        audit("APPROVE", "invoice", "invoices", rid)
                        st.success("Invoice berhasil disetujui!")
                        st.rerun()
                    else: st.error(err)
        else: 
            st.info("Hanya Admin atau Manager yang dapat memberikan persetujuan.")

if not df.empty:
    st.markdown("#### 📋 Daftar Invoice & Termin")
    disp = df.copy()
    disp["outstanding"] = disp.amount - disp.paid_amount
    
    # Format Currency
    disp["amount"] = disp["amount"].apply(lambda x: money(x))
    disp["paid_amount"] = disp["paid_amount"].apply(lambda x: money(x))
    disp["outstanding"] = disp["outstanding"].apply(lambda x: money(x))
    
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "invoice_no": "No. Invoice",
        "customer": "Klien / Customer", "invoice_date": "Tgl Invoice", "due_date": "Jatuh Tempo",
        "amount": "Nilai Invoice", "paid_amount": "Sudah Dibayar",
        "outstanding": "Outstanding / Sisa", "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    
    st.dataframe(disp, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Grand Total Tagihan (Invoice)", money(df.amount.sum()))
    c2.metric("Total Diterima (Paid)", money(df.paid_amount.sum()))
    c3.metric("Total Outstanding Piutang", money((df.amount - df.paid_amount).sum()))
