import streamlit as st
import pandas as pd
import plotly.express as px
from utils import q, execute, audit, now, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("cashflow")

pid, project = get_active_project()
st.subheader(f"💵 Cash Flow + Approval — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM cashflow WHERE project_id=%s ORDER BY id", (pid,)) if pid else pd.DataFrame()

user = st.session_state.get("user")
role = user["role"] if user else ""

if perm("cashflow","create") or perm("cashflow","edit") or perm("cashflow","delete") or role in ["Admin","Manager"]:
    tab1, tab2, tab3 = st.tabs(["➕ Tambah Cash Flow", "✏️ Edit / Hapus Cash Flow", "✅ Approval"])
    
    with tab1:
        if perm("cashflow","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            period = a.text_input("Periode *", placeholder="Misal: Jan 2026 / Minggu 1")
            cin = b.number_input("Cash In (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Pemasukan")
            with b: render_live_format(cin)
            cout = c.number_input("Cash Out (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Pengeluaran")
            with c: render_live_format(cout)
            
            if st.button("Simpan Cash Flow", type="primary", key="btn_create_cf"):
                if not period.strip():
                    st.error("Periode wajib diisi!")
                else:
                    s, lid, err = execute("INSERT INTO cashflow(project_id,period,cash_in,cash_out) VALUES(?,?,?,?)",
                                          (pid, period, cin or 0, cout or 0))
                    if s: 
                        audit("CREATE", "cashflow", "cashflow", lid, period)
                        st.success("Data Cash Flow berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(err)
        else: st.info("Anda tidak memiliki hak akses untuk menambah Cash Flow.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data Cash Flow untuk proyek ini.")
        else:
            psel = st.selectbox("Pilih Cash Flow", df.id.tolist(), key="sel_cf", format_func=lambda x: df.loc[df.id==x,"period"].iloc[0])
            sel = df.loc[df.id==psel].iloc[0]
            
            if sel.approval_status == 'Approved':
                st.warning("Data ini sudah disetujui (Approved) dan tidak dapat diubah lagi.")
            else:
                if perm("cashflow","edit"):
                    st.info(FORM_INSTRUCTION)
                    a, b, c = st.columns(3)
                    e_per = a.text_input("Periode *", sel.period, key="ecf_per")
                    e_cin = b.number_input("Cash In (Rp)", 0., value=float(sel.cash_in), help=CURRENCY_HELP, key="ecf_in")
                    with b: render_live_format(e_cin)
                    e_cout = c.number_input("Cash Out (Rp)", 0., value=float(sel.cash_out), help=CURRENCY_HELP, key="ecf_out")
                    with c: render_live_format(e_cout)
                    
                    if st.button("Update Cash Flow", type="primary", key="btn_upd_cf"):
                        if not e_per.strip():
                            st.error("Periode wajib diisi!")
                        else:
                            s, _, err = execute("UPDATE cashflow SET period=?, cash_in=?, cash_out=? WHERE id=?", 
                                                (e_per, e_cin, e_cout, psel))
                            if s: 
                                audit("UPDATE", "cashflow", "cashflow", psel, e_per)
                                st.success("Data Cash Flow berhasil diperbarui!")
                                st.rerun()
                            else: st.error(err)
                            
                if perm("cashflow","delete"):
                    st.write("")
                    with st.expander("⚠️ Hapus Cash Flow"):
                        st.warning("Data Cash Flow yang dihapus tidak dapat dikembalikan.")
                        if st.button("Hapus Secara Permanen", type="primary", key="btn_del_cf"):
                            s, _, err = execute("DELETE FROM cashflow WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "cashflow", "cashflow", psel)
                                st.success("Cash Flow berhasil dihapus!")
                                st.rerun()
                            else: st.error(err)
                            
    with tab3:
        if role in ["Admin","Manager"]:
            if df.empty or df[df.approval_status != 'Approved'].empty:
                st.success("Tidak ada Cash Flow yang menunggu persetujuan.")
            else:
                rid = st.selectbox("Pilih Cash Flow untuk disetujui", df[df.approval_status != 'Approved'].id.tolist(), key="sel_appr_cf", format_func=lambda x: df.loc[df.id==x,"period"].iloc[0])
                if rid and st.button("Approve Cash Flow", type="primary", key="btn_appr_cf"):
                    s, _, err = execute("UPDATE cashflow SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?", (user["username"], now(), rid))
                    if s: 
                        audit("APPROVE", "cashflow", "cashflow", rid)
                        st.success("Cash Flow berhasil disetujui!")
                        st.rerun()
                    else: st.error(err)
        else: 
            st.info("Hanya Admin atau Manager yang dapat memberikan persetujuan.")

if not df.empty:
    st.markdown("#### 📋 Daftar Cash Flow & Grafik")
    df["net"] = df.cash_in - df.cash_out
    df["cumulative"] = df.net.cumsum()
    
    disp = df.copy()
    
    # Format Currency
    disp["cash_in"] = disp["cash_in"].apply(lambda x: money(x))
    disp["cash_out"] = disp["cash_out"].apply(lambda x: money(x))
    disp["net"] = disp["net"].apply(lambda x: money(x))
    disp["cumulative"] = disp["cumulative"].apply(lambda x: money(x))
    
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "period": "Periode",
        "cash_in": "Cash In (Masuk)", "cash_out": "Cash Out (Keluar)", 
        "net": "Net Cash", "cumulative": "Kumulatif Cash Flow",
        "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    
    st.dataframe(disp, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cash In", money(df.cash_in.sum()))
    c2.metric("Total Cash Out", money(df.cash_out.sum()))
    c3.metric("Net Cash Flow (Akhir)", money(df.cumulative.iloc[-1]))
    
    fig = px.line(df, x="period", y="cumulative", markers=True, title="Grafik Kumulatif Cash Flow")
    fig.update_layout(yaxis_title="Rupiah (Rp)", xaxis_title="Periode", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
