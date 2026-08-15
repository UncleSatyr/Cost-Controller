import streamlit as st
import shutil
from datetime import datetime
from utils import q, require, audit, DB, BACKUP_DIR

require("audit")
st.subheader("🕵️ Audit Trail")
df = q("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200")
st.dataframe(df, use_container_width=True, hide_index=True)
