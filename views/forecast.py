import streamlit as st
import pandas as pd
from utils import q, require, money, get_active_project

require("forecast")

pid, project = get_active_project()
st.subheader(f"🔮 EAC / ETC & Forecast Laba — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

rab = q("SELECT * FROM rab WHERE project_id=%s", (pid,))
ac = q("SELECT * FROM actual_costs WHERE project_id=%s", (pid,))
pr = q("SELECT * FROM progress WHERE project_id=%s ORDER BY id", (pid,))

bac = float(rab.budget.sum()) if not rab.empty else 0
actual = float(ac.amount.sum()) if not ac.empty else 0
progress = float(pr.actual_pct.iloc[-1] / 100) if not pr.empty else 0

cpi = (bac * progress) / actual if actual and bac else 0
eac = actual + (bac - actual) / cpi if cpi > 0 else actual
etc = eac - actual
contract = float(project.contract_value) if project.contract_value else 0
profit = contract - eac

with st.expander("ℹ️ Panduan Membaca Analisis"):
    st.markdown("""
    * **BAC (Budget at Completion):** Total Anggaran Proyek (Total RAB).
    * **AC (Actual Cost):** Total Pengeluaran Riil saat ini.
    * **EAC (Estimate at Completion):** Prediksi Total Biaya saat proyek selesai berdasarkan performa (CPI) saat ini.
    * **ETC (Estimate to Complete):** Prediksi Sisa Biaya yang masih dibutuhkan untuk menyelesaikan proyek.
    """)

st.markdown("### 📊 Analisis Biaya")
a, b, c, d = st.columns(4)
a.metric("BAC (Total Anggaran)", money(bac))
b.metric("AC (Pengeluaran Saat Ini)", money(actual))
c.metric("EAC (Prediksi Total Biaya)", money(eac))
d.metric("ETC (Prediksi Sisa Biaya)", money(etc))

st.markdown("---")
st.markdown("### 📈 Forecast Profitabilitas")
p1, p2 = st.columns(2)
p1.metric("Nilai Kontrak", money(contract))
p1.metric("Forecast Laba Akhir", money(profit))
p2.metric("Forecast Margin (%)", f"{profit/contract:.2%}" if contract else "0.00%")
