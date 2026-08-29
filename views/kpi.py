import streamlit as st
import pandas as pd
from utils import q, require, money, get_active_project

require("kpi")

pid, project = get_active_project()
st.subheader(f"📐 Earned Value KPI — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

rab = q("SELECT * FROM rab WHERE project_id=%s", (pid,))
ac = q("SELECT * FROM actual_costs WHERE project_id=%s", (pid,))
pr = q("SELECT * FROM progress WHERE project_id=%s ORDER BY id", (pid,))

bac = float(rab.budget.sum()) if not rab.empty else 0
acv = float(ac.amount.sum()) if not ac.empty else 0
planned = float(pr.planned_pct.iloc[-1] / 100) if not pr.empty else 0
actualp = float(pr.actual_pct.iloc[-1] / 100) if not pr.empty else 0

pv = bac * planned
ev = bac * actualp
cpi = ev / acv if acv else 0
spi = ev / pv if pv else 0

with st.expander("ℹ️ Panduan Membaca KPI"):
    st.markdown("""
    * **PV (Planned Value):** Nilai pekerjaan yang seharusnya sudah selesai sesuai jadwal.
    * **EV (Earned Value):** Nilai pekerjaan yang benar-benar sudah selesai di lapangan.
    * **AC (Actual Cost):** Pengeluaran riil untuk mencapai EV tersebut.
    * **CPI (Cost Performance Index):** Efisiensi Biaya. **> 1 = Hemat**; **< 1 = Boros (Overrun)**.
    * **SPI (Schedule Performance Index):** Efisiensi Jadwal. **> 1 = Cepat**; **< 1 = Terlambat**.
    """)

st.markdown("### 📊 Indikator Kinerja Proyek")
a, b, c = st.columns(3)
a.metric("PV (Planned Value)", money(pv))
b.metric("EV (Earned Value)", money(ev))
c.metric("AC (Actual Cost)", money(acv))

st.markdown("---")
d, e = st.columns(2)
d.metric("CPI (Cost Performance Index)", f"{cpi:.2f}", delta="Efisien (Hemat)" if cpi >= 1 else "Overrun (Boros)", delta_color="normal" if cpi >= 1 else "inverse")
e.metric("SPI (Schedule Performance Index)", f"{spi:.2f}", delta="Lebih Cepat" if spi >= 1 else "Terlambat", delta_color="normal" if spi >= 1 else "inverse")
