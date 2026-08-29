import streamlit as st
import pandas as pd
import plotly.express as px
from utils import q, execute, audit, require, perm, get_active_project, FORM_INSTRUCTION, now

require("progress")

pid, project = get_active_project()
st.subheader(f"📈 Progress Proyek — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM progress WHERE project_id=%s ORDER BY id", (pid,)) if pid else pd.DataFrame()
user = st.session_state.user
role = user["role"] if user else ""

if perm("progress","create") or perm("progress","edit") or perm("progress","delete") or role in ["Admin", "Manager"]:
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Progress", "✏️ Edit / Hapus Progress", "✅ Approval"])
    
    with tab1:
        if perm("progress","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c, d = st.columns(4)
            period = a.text_input("Periode *", placeholder="Contoh: Minggu 1 / Bulan Jan")
            planned = b.number_input("Planned %", 0., 100., step=1., value=None, placeholder="0 - 100")
            actual = c.number_input("Actual %", 0., 100., step=1., value=None, placeholder="0 - 100")
            weight = d.number_input("Bobot %", 0., 100., step=1., value=None, placeholder="0 - 100")
            
            if st.button("Simpan Progress", type="primary", key="btn_create_prog"):
                if not period.strip():
                    st.error("Periode wajib diisi!")
                else:
                    s, lid, e = execute("INSERT INTO progress(project_id,period,planned_pct,actual_pct,weight_pct) VALUES(?,?,?,?,?)", (pid, period, planned or 0, actual or 0, weight or 0))
                    if s: 
                        audit("CREATE", "progress", "progress", lid, period)
                        st.success("Data progress berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(e)
        else: st.info("Anda tidak memiliki hak akses untuk menambah progress.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data progress untuk proyek ini.")
        else:
            psel = st.selectbox("Pilih Progress", df.id.tolist(), key="sel_prog", format_func=lambda x: df.loc[df.id==x,"period"].iloc[0])
            sel = df.loc[df.id==psel].iloc[0]
            if sel.approval_status == 'Approved':
                st.warning("Data ini sudah disetujui (Approved) dan tidak dapat diubah lagi.")
            else:
                if perm("progress","edit"):
                    st.info(FORM_INSTRUCTION)
                    a, b, c, d = st.columns(4)
                    e_per = a.text_input("Periode *", sel.period, key="epro_per")
                    e_plan = b.number_input("Planned %", 0., 100., float(sel.planned_pct), key="epro_plan")
                    e_act = c.number_input("Actual %", 0., 100., float(sel.actual_pct), key="epro_act")
                    e_w = d.number_input("Bobot %", 0., 100., float(sel.weight_pct), key="epro_w")
                    
                    if st.button("Update Progress", type="primary", key="btn_upd_prog"):
                        if not e_per.strip():
                            st.error("Periode wajib diisi!")
                        else:
                            s, _, e = execute("UPDATE progress SET period=?, planned_pct=?, actual_pct=?, weight_pct=? WHERE id=?", (e_per, e_plan, e_act, e_w, psel))
                            if s: 
                                audit("UPDATE", "progress", "progress", psel, e_per)
                                st.success("Data progress berhasil diperbarui!")
                                st.rerun()
                            else: st.error(e)
                            
                if perm("progress","delete"):
                    st.write("")
                    with st.expander("⚠️ Hapus Progress"):
                        st.warning("Data progress yang dihapus tidak dapat dikembalikan.")
                        if st.button("Hapus Secara Permanen", type="primary", key="btn_del_prog"):
                            s, _, e = execute("DELETE FROM progress WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "progress", "progress", psel)
                                st.success("Data progress berhasil dihapus!")
                                st.rerun()
                            else: st.error(e)
                            
    with tab3:
        if role in ["Admin","Manager"]:
            if df.empty or df[df.approval_status != 'Approved'].empty:
                st.success("Tidak ada data progress yang menunggu persetujuan.")
            else:
                rid = st.selectbox("Pilih Progress untuk disetujui", df[df.approval_status != 'Approved'].id.tolist(), key="sel_appr_prog", format_func=lambda x: df.loc[df.id==x,"period"].iloc[0])
                if rid and st.button("Approve Progress", type="primary", key="btn_appr_prog"):
                    s, _, err = execute("UPDATE progress SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?", (user["username"], now(), rid))
                    if s: 
                        audit("APPROVE", "progress", "progress", rid)
                        st.success("Progress berhasil disetujui!")
                        st.rerun()
                    else: st.error(err)
        else:
            st.info("Hanya Admin atau Manager yang dapat memberikan persetujuan.")

if not df.empty:
    st.markdown("#### 📋 Tabel Progress")
    disp = df.copy()
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "period": "Periode",
        "planned_pct": "Planned (%)", "actual_pct": "Actual (%)",
        "weight_pct": "Bobot (%)", "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    st.dataframe(disp, hide_index=True)
    
    st.markdown("#### 📊 Grafik Planned vs Actual")
    st.plotly_chart(px.line(df, x="period", y=["planned_pct","actual_pct"], markers=True, 
                            labels={"period": "Periode", "value": "Persentase (%)", "variable": "Kategori"},
                            color_discrete_map={"planned_pct": "#636EFA", "actual_pct": "#00CC96"}), 
                    use_container_width=True)
