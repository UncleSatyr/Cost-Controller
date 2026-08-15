import streamlit as st
import pandas as pd
import io
from utils import q, require, get_active_project

require("reports")
st.subheader("📥 Project Report")

pid, project = get_active_project()

if project is not None:
    tables = {
        "Project": q("SELECT * FROM projects WHERE id=?", (pid,)),
        "RAB": q("SELECT * FROM rab WHERE project_id=?", (pid,)),
        "Actual_Cost": q("SELECT * FROM actual_costs WHERE project_id=?", (pid,)),
        "Progress": q("SELECT * FROM progress WHERE project_id=?", (pid,)),
        "PO": q("SELECT * FROM purchase_orders WHERE project_id=?", (pid,)),
        "Invoice": q("SELECT * FROM invoices WHERE project_id=?", (pid,)),
        "Hutang": q("SELECT * FROM vendor_payables WHERE project_id=?", (pid,)),
        "Cash_Flow": q("SELECT * FROM cashflow WHERE project_id=?", (pid,)),
        "Audit": q("SELECT * FROM audit_logs ORDER BY id DESC")
    }
    
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        for n, d in tables.items():
            d.to_excel(w, index=False, sheet_name=n[:31])
            
    st.download_button("⬇️ Download Excel", out.getvalue(), f"{project['name']}_V3_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
