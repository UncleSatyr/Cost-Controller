import streamlit as st
import shutil
from datetime import datetime
from utils import require, audit, DB, BACKUP_DIR

require("backup")
st.subheader("💾 Backup & Restore Database")

st.write(f"Database: `{DB.name}`")
if st.button("📦 Buat Backup Sekarang", type="primary"):
    fn = BACKUP_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB, fn)
    audit("BACKUP", "backup", detail=fn.name)
    st.success(f"Backup dibuat: {fn.name}")

backups = sorted(BACKUP_DIR.glob("*.db"), reverse=True)
if backups:
    st.markdown("### Backup tersedia")
    for b in backups[:20]:
        st.write(f"• {b.name} — {b.stat().st_size:,} bytes")
        with open(b, "rb") as f: 
            st.download_button(f"Download {b.name}", f.read(), b.name, "application/octet-stream", key=b.name)

st.warning("Restore otomatis belum diaktifkan pada v3 untuk mencegah overwrite database aktif secara tidak sengaja. Restore dapat dilakukan dengan mengganti file DB saat aplikasi berhenti.")
