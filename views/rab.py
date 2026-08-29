import streamlit as st
import pandas as pd
from utils import q, execute, audit, now, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("rab")

pid, project = get_active_project()
st.subheader(f"📋 RAB (Rencana Anggaran Biaya) — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM rab WHERE project_id=%s ORDER BY id", (pid,)) if pid else pd.DataFrame()

user = st.session_state.get("user")
role = user["role"] if user else ""

if perm("rab","create") or perm("rab","edit") or perm("rab","delete") or role in ["Admin","Manager"]:
    tab1, tab2, tab3 = st.tabs(["➕ Tambah RAB", "✏️ Edit / Hapus RAB", "✅ Approval"])
    
    with tab1:
        if perm("rab","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            code = a.text_input("Kode *", placeholder="Misal: A.1")
            cat = b.text_input("Kategori", placeholder="Misal: Material")
            desc = c.text_input("Uraian *", placeholder="Misal: Semen")
            
            d, e, f = st.columns(3)
            qty = d.number_input("Qty", 0., value=None, placeholder="Jumlah")
            unit = e.text_input("Satuan", placeholder="Misal: Sak / Kg")
            price = f.number_input("Harga Satuan (Rp)", 0., step=1000., help=CURRENCY_HELP, value=None, placeholder="Contoh: 50000")
            with f: render_live_format(price)
            
            if st.button("Simpan RAB", type="primary", key="btn_create_rab"):
                if not code.strip() or not desc.strip():
                    st.error("Kode dan Uraian wajib diisi!")
                else:
                    s, lid, err = execute("INSERT INTO rab(project_id,code,category,description,qty,unit,unit_price,budget) VALUES(?,?,?,?,?,?,?,?)",
                                          (pid, code, cat, desc, qty or 0, unit, price or 0, (qty or 0)*(price or 0)))
                    if s: 
                        audit("CREATE", "rab", "rab", lid, code)
                        st.success("RAB berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(err)
        else: st.info("Anda tidak memiliki hak akses untuk menambah RAB.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data RAB untuk proyek ini.")
        else:
            psel = st.selectbox("Pilih RAB", df.id.tolist(), key="sel_rab", format_func=lambda x: f"{df.loc[df.id==x,'code'].iloc[0]} - {df.loc[df.id==x,'description'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            
            if sel.approval_status == 'Approved':
                st.warning("Data ini sudah disetujui (Approved) dan tidak dapat diubah lagi.")
            else:
                if perm("rab","edit"):
                    st.info(FORM_INSTRUCTION)
                    a, b, c = st.columns(3)
                    e_code = a.text_input("Kode *", sel.code, key="er_c")
                    e_cat = b.text_input("Kategori", sel.category if pd.notna(sel.category) else "", key="er_ca")
                    e_desc = c.text_input("Uraian *", sel.description, key="er_d")
                    
                    d, e, f = st.columns(3)
                    e_qty = d.number_input("Qty", 0., value=float(sel.qty), key="er_q")
                    e_unit = e.text_input("Satuan", sel.unit if pd.notna(sel.unit) else "", key="er_u")
                    e_price = f.number_input("Harga Satuan (Rp)", 0., value=float(sel.unit_price), help=CURRENCY_HELP, key="er_p")
                    with f: render_live_format(e_price)
                    
                    if st.button("Update RAB", type="primary", key="btn_upd_rab"):
                        if not e_code.strip() or not e_desc.strip():
                            st.error("Kode dan Uraian wajib diisi!")
                        else:
                            s, _, err = execute("UPDATE rab SET code=?, category=?, description=?, qty=?, unit=?, unit_price=?, budget=? WHERE id=?", 
                                                (e_code, e_cat, e_desc, e_qty, e_unit, e_price, e_qty*e_price, psel))
                            if s: 
                                audit("UPDATE", "rab", "rab", psel, e_code)
                                st.success("Data RAB berhasil diperbarui!")
                                st.rerun()
                            else: st.error(err)
                            
                if perm("rab","delete"):
                    st.write("")
                    with st.expander("⚠️ Hapus RAB"):
                        st.warning("Data RAB yang dihapus tidak dapat dikembalikan dan dapat mempengaruhi Actual Cost yang sudah terhubung.")
                        if st.button("Hapus Secara Permanen", type="primary", key="btn_del_rab"):
                            s, _, err = execute("DELETE FROM rab WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "rab", "rab", psel)
                                st.success("RAB berhasil dihapus!")
                                st.rerun()
                            else: st.error(err)
                        
    with tab3:
        if role in ["Admin","Manager"]:
            if df.empty or df[df.approval_status != 'Approved'].empty:
                st.success("Tidak ada RAB yang menunggu persetujuan.")
            else:
                rid = st.selectbox("Pilih RAB untuk disetujui", df[df.approval_status != 'Approved'].id.tolist(), key="sel_appr_rab", format_func=lambda x: f"{df.loc[df.id==x,'code'].iloc[0]} - {df.loc[df.id==x,'description'].iloc[0]}")
                if rid and st.button("Approve RAB", type="primary", key="btn_appr_rab"):
                    s, _, err = execute("UPDATE rab SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?", (user["username"], now(), rid))
                    if s: 
                        audit("APPROVE", "rab", "rab", rid)
                        st.success("RAB berhasil disetujui!")
                        st.rerun()
                    else: st.error(err)
        else: 
            st.info("Hanya Admin atau Manager yang dapat memberikan persetujuan.")

if not df.empty:
    st.markdown("#### 📋 Daftar RAB")
    disp = df.copy()
    disp["unit_price"] = disp["unit_price"].apply(lambda x: money(x))
    disp["budget"] = disp["budget"].apply(lambda x: money(x))
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "code": "Kode",
        "category": "Kategori", "description": "Uraian",
        "qty": "Qty", "unit": "Satuan", "unit_price": "Harga Satuan",
        "budget": "Total Budget", "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    st.dataframe(disp, hide_index=True)
    st.metric("Grand Total RAB", money(df.budget.sum()))
