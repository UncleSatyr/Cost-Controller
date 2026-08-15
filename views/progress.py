import streamlit as st
import pandas as pd
import plotly.express as px
from utils import q, execute, audit, require, perm, get_active_project

require("progress")
st.subheader("📈 Progress Proyek")

pid, project = get_active_project()
df = q("SELECT * FROM progress WHERE project_id=? ORDER BY id", (pid,)) if pid else pd.DataFrame()

if project is not None and (perm("progress","create") or perm("progress","edit") or perm("progress","delete")):
    tab1, tab2 = st.tabs(["➕ Tambah Progress", "✏️ Edit / Hapus Progress"])
    with tab1:
        if perm("progress","create"):
            a, b, c = st.columns(3)
            period = a.text_input("Periode", placeholder="Contoh: Minggu 1 / Bulan Jan")
            planned = b.number_input("Planned %", 0., 100., step=1., value=None, placeholder="0 - 100")
            actual = c.number_input("Actual %", 0., 100., step=1., value=None, placeholder="0 - 100")
            weight = st.number_input("Bobot %", 0., 100., step=1., value=None, placeholder="0 - 100")
            if st.button("Tambah Progress", type="primary", key="btn_create_prog"):
                s, lid, e = execute("INSERT INTO progress(project_id,period,planned_pct,actual_pct,weight_pct) VALUES(?,?,?,?,?)", (pid, period, planned or 0, actual or 0, weight or 0))
                if s: 
                    audit("CREATE", "progress", "progress", lid, period)
                    st.rerun()
                else: st.error(e)
        else: st.info("Akses ditolak.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data progress.")
        else:
            psel = st.selectbox("Pilih Progress", df.id.tolist(), key="sel_prog", format_func=lambda x: df.loc[df.id==x,"period"].iloc[0])
            sel = df.loc[df.id==psel].iloc[0]
            if sel.approval_status == 'Approved':
                st.warning("Data sudah diapprove, tidak dapat diubah.")
            else:
                if perm("progress","edit"):
                    e_per = st.text_input("Periode", sel.period, key="epro_per")
                    e_plan = st.number_input("Planned %", 0., 100., float(sel.planned_pct), key="epro_plan")
                    e_act = st.number_input("Actual %", 0., 100., float(sel.actual_pct), key="epro_act")
                    e_w = st.number_input("Bobot %", 0., 100., float(sel.weight_pct), key="epro_w")
                    if st.button("Update Progress", key="btn_upd_prog"):
                        s, _, e = execute("UPDATE progress SET period=?, planned_pct=?, actual_pct=?, weight_pct=? WHERE id=?", (e_per, e_plan, e_act, e_w, psel))
                        if s: 
                            audit("UPDATE", "progress", "progress", psel, e_per)
                            st.rerun()
                        else: st.error(e)
                if perm("progress","delete"):
                    if st.button("Hapus Progress Terpilih", key="btn_del_prog"):
                        s, _, e = execute("DELETE FROM progress WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "progress", "progress", psel)
                            st.rerun()
                        else: st.error(e)

if not df.empty:
    st.markdown("---")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.plotly_chart(px.line(df, x="period", y=["planned_pct","actual_pct"], markers=True, title="Planned vs Actual"), use_container_width=True)
