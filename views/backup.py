import streamlit as st
import shutil
import io
import pandas as pd
from datetime import datetime
from utils import q, require, audit, DB, BACKUP_DIR
from db_config import DATABASE_URL

require("backup")
st.subheader("💾 Backup & Restore Database")

if DATABASE_URL:
    st.info("🌐 **Sistem menggunakan PostgreSQL (Cloud/Remote Database).**")
    st.markdown("""
    Karena Anda menggunakan PostgreSQL, *backup* file lokal (`.db`) tidak lagi relevan.
    Untuk mencadangkan data, Anda memiliki dua opsi:
    
    1. **Ekspor Data ke Excel:** Mengunduh seluruh data tabel saat ini ke dalam satu file Excel (`.xlsx`).
    2. **Backup Server:** Menggunakan fitur *backup* bawaan dari penyedia *database* Anda (contoh: Supabase, AWS, pgAdmin) untuk mendapatkan format `.sql` (schema + data).
    """)
    
    if st.button("📦 Generate Backup Data (Excel)", type="primary"):
        tables = ["users", "permissions", "projects", "rab", "actual_costs", "progress", 
                  "purchase_orders", "invoices", "vendor_payables", "cashflow", "audit_logs"]
        
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            for t in tables:
                df = q(f"SELECT * FROM {t}")
                df.to_excel(w, index=False, sheet_name=t[:31])
                
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"Data_Backup_{timestamp}.xlsx"
        audit("BACKUP", "backup", detail=f"Export Excel: {file_name}")
        
        st.success("Data berhasil diekstrak! Klik tombol di bawah untuk mengunduh.")
        st.download_button("⬇️ Download Backup Excel", out.getvalue(), file_name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
else:
    st.info("🗄️ **Sistem menggunakan SQLite (Local Database).**")
    st.write(f"Lokasi Database: `{DB.name}`")
    
    if st.button("📦 Buat Backup Sekarang", type="primary"):
        fn = BACKUP_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(DB, fn)
        audit("BACKUP", "backup", detail=fn.name)
        st.success(f"Backup dibuat: {fn.name}")

    backups = sorted(BACKUP_DIR.glob("*.db"), reverse=True)
    if backups:
        st.markdown("### Backup tersedia")
        for b in backups[:20]:
            c1, c2 = st.columns([3, 1])
            c1.write(f"• {b.name} — {b.stat().st_size:,} bytes")
            with open(b, "rb") as f: 
                c2.download_button("⬇️ Download", f.read(), b.name, "application/octet-stream", key=b.name)

st.warning("Restore otomatis belum diaktifkan pada v3 untuk mencegah overwrite database aktif secara tidak sengaja. Restore harus dilakukan secara manual (impor SQL atau *replace file*).")
