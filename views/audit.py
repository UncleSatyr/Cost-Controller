import streamlit as st
import shutil
from datetime import datetime
from utils import q, require, audit, DB, BACKUP_DIR

require("audit")
st.subheader("🕵️ Audit Trail — Log Aktivitas Sistem")

st.markdown("Halaman ini mencatat seluruh rekam jejak aktivitas tambah, ubah, hapus, dan persetujuan (approval) yang terjadi di dalam sistem Cost Controller.")

df = q("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200")
if df.empty:
    st.info("Belum ada log aktivitas.")
else:
    disp = df.copy()
    disp = disp.rename(columns={
        "id": "ID", "timestamp": "Waktu Kejadian", "user": "Pengguna",
        "action": "Aktivitas", "module": "Modul", "table_name": "Tabel Target",
        "record_id": "ID Record", "detail": "Detail Perubahan"
    })
    st.dataframe(disp, use_container_width=True, hide_index=True)
