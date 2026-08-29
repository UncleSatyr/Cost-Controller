import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, now, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("payable")

pid, project = get_active_project()
st.subheader(f"🏦 Hutang Vendor + Approval — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM vendor_payables WHERE project_id=? ORDER BY id DESC", (pid,)) if pid else pd.DataFrame()

user = st.session_state.get("user")
role = user["role"] if user else ""

if perm("payable","create") or perm("payable","edit") or perm("payable","delete") or role in ["Admin","Manager"]:
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Hutang", "✏️ Edit / Hapus Hutang", "✅ Approval"])
    
    with tab1:
        if perm("payable","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            vendor = a.text_input("Vendor *", placeholder="Nama Vendor")
            bill = b.text_input("No Tagihan *", placeholder="Nomor Tagihan/Kwitansi")
            bd = c.date_input("Tanggal Tagihan (Bill Date) *", date.today())
            
            d, e, f = st.columns(3)
            due = d.date_input("Jatuh Tempo (Due Date) *", date.today())
            amount = e.number_input("Total Hutang (Rp) *", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Nilai Hutang")
            with e: render_live_format(amount)
            paid = f.number_input("Telah Dibayar (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Opsional")
            with f: render_live_format(paid)
            
            if st.button("Simpan Hutang", type="primary", key="btn_create_pay"):
                if not vendor.strip() or not bill.strip() or amount is None:
                    st.error("Vendor, No Tagihan, dan Total Hutang wajib diisi!")
                else:
                    s, lid, err = execute("INSERT INTO vendor_payables(project_id,vendor,bill_no,bill_date,due_date,amount,paid_amount) VALUES(?,?,?,?,?,?,?)",
                                          (pid, vendor, bill, str(bd), str(due), amount or 0, paid or 0))
                    if s: 
                        audit("CREATE", "payable", "vendor_payables", lid, bill)
                        st.success("Data Hutang Vendor berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(err)
        else: st.info("Anda tidak memiliki hak akses untuk menambah Hutang.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data Hutang untuk proyek ini.")
        else:
            psel = st.selectbox("Pilih Hutang", df.id.tolist(), key="sel_pay", format_func=lambda x: f"{df.loc[df.id==x,'bill_no'].iloc[0]} - {df.loc[df.id==x,'vendor'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            
            if sel.approval_status == 'Approved':
                st.warning("Data ini sudah disetujui (Approved) dan tidak dapat diubah lagi.")
            else:
                if perm("payable","edit"):
                    st.info(FORM_INSTRUCTION)
                    a, b, c = st.columns(3)
                    e_ven = a.text_input("Vendor *", sel.vendor, key="epay_v")
                    e_bill = b.text_input("No Tagihan *", sel.bill_no, key="epay_b")
                    e_bd = c.date_input("Tanggal Tagihan (Bill Date) *", datetime.strptime(sel.bill_date, "%Y-%m-%d").date() if sel.bill_date else date.today(), key="epay_d1")
                    
                    d, e, f = st.columns(3)
                    e_due = d.date_input("Jatuh Tempo (Due Date) *", datetime.strptime(sel.due_date, "%Y-%m-%d").date() if sel.due_date else date.today(), key="epay_d2")
                    e_amt = e.number_input("Total Hutang (Rp) *", 0., value=float(sel.amount), help=CURRENCY_HELP, key="epay_a")
                    with e: render_live_format(e_amt)
                    e_paid = f.number_input("Telah Dibayar (Rp)", 0., value=float(sel.paid_amount), help=CURRENCY_HELP, key="epay_p")
                    with f: render_live_format(e_paid)
                    
                    if st.button("Update Hutang", type="primary", key="btn_upd_pay"):
                        if not e_ven.strip() or not e_bill.strip():
                            st.error("Vendor dan No Tagihan wajib diisi!")
                        else:
                            s, _, err = execute("UPDATE vendor_payables SET vendor=?, bill_no=?, bill_date=?, due_date=?, amount=?, paid_amount=? WHERE id=?", 
                                                (e_ven, e_bill, str(e_bd), str(e_due), e_amt, e_paid, psel))
                            if s: 
                                audit("UPDATE", "payable", "vendor_payables", psel, e_bill)
                                st.success("Data Hutang berhasil diperbarui!")
                                st.rerun()
                            else: st.error(err)
                            
                if perm("payable","delete"):
                    st.write("")
                    with st.expander("⚠️ Hapus Hutang"):
                        st.warning("Data Hutang yang dihapus tidak dapat dikembalikan.")
                        if st.button("Hapus Secara Permanen", type="primary", key="btn_del_pay"):
                            s, _, err = execute("DELETE FROM vendor_payables WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "payable", "vendor_payables", psel)
                                st.success("Hutang berhasil dihapus!")
                                st.rerun()
                            else: st.error(err)
                            
    with tab3:
        if role in ["Admin","Manager"]:
            if df.empty or df[df.approval_status != 'Approved'].empty:
                st.success("Tidak ada Hutang yang menunggu persetujuan.")
            else:
                rid = st.selectbox("Pilih Hutang untuk disetujui", df[df.approval_status != 'Approved'].id.tolist(), key="sel_appr_pay", format_func=lambda x: f"{df.loc[df.id==x,'bill_no'].iloc[0]} - {df.loc[df.id==x,'vendor'].iloc[0]}")
                if rid and st.button("Approve Hutang", type="primary", key="btn_appr_pay"):
                    s, _, err = execute("UPDATE vendor_payables SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?", (user["username"], now(), rid))
                    if s: 
                        audit("APPROVE", "payable", "vendor_payables", rid)
                        st.success("Hutang berhasil disetujui!")
                        st.rerun()
                    else: st.error(err)
        else: 
            st.info("Hanya Admin atau Manager yang dapat memberikan persetujuan.")

if not df.empty:
    st.markdown("#### 📋 Daftar Hutang Vendor")
    disp = df.copy()
    disp["outstanding"] = disp.amount - disp.paid_amount
    
    # Format Currency
    disp["amount"] = disp["amount"].apply(lambda x: money(x))
    disp["paid_amount"] = disp["paid_amount"].apply(lambda x: money(x))
    disp["outstanding"] = disp["outstanding"].apply(lambda x: money(x))
    
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "vendor": "Vendor",
        "bill_no": "No. Tagihan", "bill_date": "Tanggal Tagihan", "due_date": "Jatuh Tempo",
        "amount": "Nilai Hutang", "paid_amount": "Sudah Dibayar",
        "outstanding": "Outstanding / Sisa", "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    
    st.dataframe(disp, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Grand Total Hutang", money(df.amount.sum()))
    c2.metric("Total Dibayar", money(df.paid_amount.sum()))
    c3.metric("Total Outstanding Hutang", money((df.amount - df.paid_amount).sum()))
