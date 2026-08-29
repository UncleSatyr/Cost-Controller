import streamlit as st
import pandas as pd
from utils import q, require, money, get_active_project

require("receivable")

pid, project = get_active_project()
st.subheader(f"💰 Piutang Outstanding — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM invoices WHERE project_id=%s AND amount>paid_amount ORDER BY due_date", (pid,))

if df.empty: 
    st.success("Tidak ada piutang outstanding. Semua invoice telah lunas!")
else:
    st.markdown("Berikut adalah daftar Invoice/Termin yang belum dibayar lunas oleh Customer:")
    disp = df.copy()
    disp["outstanding"] = disp.amount - disp.paid_amount
    
    # Format Currency
    disp["amount"] = disp["amount"].apply(lambda x: money(x))
    disp["paid_amount"] = disp["paid_amount"].apply(lambda x: money(x))
    disp["outstanding"] = disp["outstanding"].apply(lambda x: money(x))
    
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "invoice_no": "No. Invoice",
        "customer": "Klien / Customer", "invoice_date": "Tgl Invoice", "due_date": "Jatuh Tempo",
        "amount": "Nilai Tagihan", "paid_amount": "Telah Dibayar",
        "outstanding": "Sisa Piutang", "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    
    st.dataframe(disp, hide_index=True)
    st.metric("Total Outstanding Piutang", money((df.amount - df.paid_amount).sum()))
