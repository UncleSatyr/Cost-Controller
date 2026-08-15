import streamlit as st
import pandas as pd
import plotly.express as px
from utils import q, require, get_active_project, money

require("dashboard")
pid, project = get_active_project()

st.subheader(f"📊 Executive Management Dashboard — {project['name'] if project is not None else 'No Project'}")
if project is None:
    st.info("Belum ada proyek.")
    st.stop()

rab = q("SELECT * FROM rab WHERE project_id=?", (pid,))
ac = q("SELECT * FROM actual_costs WHERE project_id=?", (pid,))
pr = q("SELECT * FROM progress WHERE project_id=? ORDER BY id", (pid,))
inv = q("SELECT * FROM invoices WHERE project_id=?", (pid,))
pay = q("SELECT * FROM vendor_payables WHERE project_id=?", (pid,))
cf = q("SELECT * FROM cashflow WHERE project_id=?", (pid,))

contract = float(project.contract_value)
bac = float(rab.budget.sum()) if not rab.empty else 0
actual = float(ac.amount.sum()) if not ac.empty else 0
progress = float(pr.actual_pct.iloc[-1]) if not pr.empty else 0
planned = float(pr.planned_pct.iloc[-1]) if not pr.empty else 0
profit = contract - actual
margin = profit / contract if contract else 0
receiv = float((inv.amount - inv.paid_amount).sum()) if not inv.empty else 0
payable = float((pay.amount - pay.paid_amount).sum()) if not pay.empty else 0
netcash = float((cf.cash_in - cf.cash_out).sum()) if not cf.empty else 0

a, b, c, d = st.columns(4)
a.metric("Contract", money(contract))
b.metric("BAC / RAB", money(bac))
c.metric("Actual Cost", money(actual))
d.metric("Current Profit", money(profit))

a, b, c, d = st.columns(4)
a.metric("Progress", f"{progress:.1f}%", f"{progress-planned:.1f}% vs plan")
b.metric("Margin", f"{margin:.2%}")
c.metric("Piutang", money(receiv))
d.metric("Hutang", money(payable))

st.metric("Net Cash Flow", money(netcash))

if margin >= .15:
    st.success("🟢 HEALTHY — margin di atas 15%")
elif margin >= .05:
    st.warning("🟡 WATCH — perlu monitoring")
else:
    st.error("🔴 CRITICAL — margin rendah")

if not pr.empty:
    st.plotly_chart(px.line(pr, x="period", y=["planned_pct", "actual_pct"], markers=True, title="Progress Plan vs Actual"), use_container_width=True)
if not rab.empty:
    st.plotly_chart(px.bar(rab.groupby("category")["budget"].sum().reset_index(), x="category", y="budget", title="RAB per Kategori"), use_container_width=True)
