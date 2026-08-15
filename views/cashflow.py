import streamlit as st
import pandas as pd
import plotly.express as px
from utils import q, execute, audit, require, perm, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("cashflow")
st.subheader("💵 Cash Flow")

pid, project = get_active_project()
df = q("SELECT * FROM cashflow WHERE project_id=?", (pid,)) if pid else pd.DataFrame()

if project is not None and (perm("cashflow","create") or perm("cashflow","edit") or perm("cashflow","delete")):
    tab1, tab2 = st.tabs(["➕ Tambah Cash Flow", "✏️ Edit / Hapus Cash Flow"])
    with tab1:
        if perm("cashflow","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            period = a.text_input("Periode", placeholder="Bulan / Minggu")
            cin = b.number_input("Cash In (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Pemasukan")
            with b: render_live_format(cin)
            cout = c.number_input("Cash Out (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Pengeluaran")
            with c: render_live_format(cout)
            if st.button("Tambah", type="primary", key="btn_create_cf"):
                s, lid, err = execute("INSERT INTO cashflow(project_id,period,cash_in,cash_out) VALUES(?,?,?,?)",
                                      (pid, period, cin or 0, cout or 0))
                if s: 
                    audit("CREATE", "cashflow", "cashflow", lid, period)
                    st.rerun()
                else: st.error(err)
        else: st.info("Akses ditolak.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data cash flow.")
        else:
            psel = st.selectbox("Pilih Cash Flow", df.id.tolist(), key="sel_cf", format_func=lambda x: df.loc[df.id==x,"period"].iloc[0])
            sel = df.loc[df.id==psel].iloc[0]
            if sel.approval_status == 'Approved':
                st.warning("Data sudah diapprove, tidak dapat diubah.")
            else:
                if perm("cashflow","edit"):
                    st.info(FORM_INSTRUCTION)
                    e_per = st.text_input("Periode", sel.period, key="ecf_per")
                    e_cin = st.number_input("Cash In (Rp)", 0., value=float(sel.cash_in), help=CURRENCY_HELP, key="ecf_in")
                    render_live_format(e_cin)
                    e_cout = st.number_input("Cash Out (Rp)", 0., value=float(sel.cash_out), help=CURRENCY_HELP, key="ecf_out")
                    render_live_format(e_cout)
                    if st.button("Update Cash Flow", key="btn_upd_cf"):
                        s, _, err = execute("UPDATE cashflow SET period=?, cash_in=?, cash_out=? WHERE id=?", 
                                            (e_per, e_cin, e_cout, psel))
                        if s: 
                            audit("UPDATE", "cashflow", "cashflow", psel, e_per)
                            st.rerun()
                        else: st.error(err)
                if perm("cashflow","delete"):
                    if st.button("Hapus Cash Flow Terpilih", key="btn_del_cf"):
                        s, _, err = execute("DELETE FROM cashflow WHERE id=?", (psel,))
                        if s: 
                            audit("DELETE", "cashflow", "cashflow", psel)
                            st.rerun()
                        else: st.error(err)

if not df.empty:
    st.markdown("---")
    df["net"] = df.cash_in - df.cash_out
    df["cumulative"] = df.net.cumsum()
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.plotly_chart(px.line(df, x="period", y="cumulative", markers=True, title="Cumulative Cash Flow"), use_container_width=True)
