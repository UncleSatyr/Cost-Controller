import streamlit as st
import pandas as pd
from utils import q, require, money, get_active_project

require("kpi")
st.subheader("📐 Earned Value KPI — CPI / SPI")

pid, project = get_active_project()

if project is not None:
    rab = q("SELECT * FROM rab WHERE project_id=?", (pid,))
    ac = q("SELECT * FROM actual_costs WHERE project_id=?", (pid,))
    pr = q("SELECT * FROM progress WHERE project_id=? ORDER BY id", (pid,))
    
    bac = float(rab.budget.sum()) if not rab.empty else 0
    acv = float(ac.amount.sum()) if not ac.empty else 0
    planned = float(pr.planned_pct.iloc[-1] / 100) if not pr.empty else 0
    actualp = float(pr.actual_pct.iloc[-1] / 100) if not pr.empty else 0
    
    pv = bac * planned
    ev = bac * actualp
    cpi = ev / acv if acv else 0
    spi = ev / pv if pv else 0
    
    a, b, c, d = st.columns(4)
    a.metric("PV", money(pv))
    b.metric("EV", money(ev))
    c.metric("AC", money(acv))
    d.metric("CPI", f"{cpi:.2f}")
    
    st.metric("SPI", f"{spi:.2f}")
    st.info("CPI > 1 = efisien biaya; CPI < 1 = cost overrun. SPI > 1 = lebih cepat; SPI < 1 = terlambat.")
