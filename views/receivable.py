import streamlit as st
import pandas as pd
from utils import q, require, money, get_active_project

require("receivable")
st.subheader("💰 Piutang")

pid, project = get_active_project()

if project is not None:
    df = q("SELECT * FROM invoices WHERE project_id=? AND amount>paid_amount ORDER BY due_date", (pid,))
    if df.empty: 
        st.success("Tidak ada piutang outstanding.")
    else:
        df["outstanding"] = df.amount - df.paid_amount
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Total Piutang", money(df.outstanding.sum()))
