import streamlit as st
import pandas as pd
from utils import q, require, money, get_active_project

require("forecast")
st.subheader("🔮 EAC / ETC & Forecast Laba")

pid, project = get_active_project()

if project is not None:
    rab = q("SELECT * FROM rab WHERE project_id=?", (pid,))
    ac = q("SELECT * FROM actual_costs WHERE project_id=?", (pid,))
    pr = q("SELECT * FROM progress WHERE project_id=? ORDER BY id", (pid,))
    
    bac = float(rab.budget.sum()) if not rab.empty else 0
    actual = float(ac.amount.sum()) if not ac.empty else 0
    progress = float(pr.actual_pct.iloc[-1] / 100) if not pr.empty else 0
    
    cpi = (bac * progress) / actual if actual and bac else 0
    eac = actual + (bac - actual) / cpi if cpi > 0 else actual
    etc = eac - actual
    contract = float(project.contract_value)
    profit = contract - eac
    
    a, b, c, d = st.columns(4)
    a.metric("BAC", money(bac))
    b.metric("AC", money(actual))
    c.metric("EAC", money(eac))
    d.metric("ETC", money(etc))
    
    st.metric("Forecast Laba Akhir", money(profit))
    st.metric("Forecast Margin", f"{profit/contract:.2%}" if contract else "0.00%")
