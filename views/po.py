import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils import q, execute, audit, now, require, perm, money, get_active_project, render_live_format, FORM_INSTRUCTION, CURRENCY_HELP

require("po")

pid, project = get_active_project()
st.subheader(f"🧾 PO / Procurement + Approval — {project['name'] if project is not None else 'Belum Ada Proyek'}")

if project is None:
    st.info("Pilih proyek aktif terlebih dahulu di bilah samping (sidebar).")
    st.stop()

df = q("SELECT * FROM purchase_orders WHERE project_id=? ORDER BY id DESC", (pid,)) if pid else pd.DataFrame()

user = st.session_state.get("user")
role = user["role"] if user else ""

if perm("po","create") or perm("po","edit") or perm("po","delete") or role in ["Admin","Manager"]:
    tab1, tab2, tab3 = st.tabs(["➕ Tambah PO", "✏️ Edit / Hapus PO", "✅ Approval"])
    
    with tab1:
        if perm("po","create"):
            st.info(FORM_INSTRUCTION)
            a, b, c = st.columns(3)
            no = a.text_input("PO No *", placeholder="Nomor PO")
            vendor = b.text_input("Vendor *", placeholder="Nama Vendor")
            dt = c.date_input("Tanggal *", date.today())
            
            d, e, f = st.columns(3)
            desc = d.text_input("Deskripsi", placeholder="Keterangan")
            value = e.number_input("Nilai PO (Rp) *", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Total PO")
            with e: render_live_format(value)
            paid = f.number_input("Paid (Rp)", 0., step=100000., help=CURRENCY_HELP, value=None, placeholder="Sudah Dibayar")
            with f: render_live_format(paid)
            
            if st.button("Simpan PO", type="primary", key="btn_create_po"):
                if not no.strip() or not vendor.strip() or value is None:
                    st.error("Nomor PO, Vendor, dan Nilai PO wajib diisi!")
                else:
                    s, lid, err = execute("INSERT INTO purchase_orders(project_id,po_no,vendor,date,description,po_value,paid_value) VALUES(?,?,?,?,?,?,?)",
                                          (pid, no, vendor, str(dt), desc, value or 0, paid or 0))
                    if s: 
                        audit("CREATE", "po", "purchase_orders", lid, no)
                        st.success("Data Purchase Order berhasil ditambahkan!")
                        st.rerun()
                    else: st.error(err)
        else: st.info("Anda tidak memiliki hak akses untuk menambah PO.")
        
    with tab2:
        if df.empty:
            st.info("Belum ada data PO untuk proyek ini.")
        else:
            psel = st.selectbox("Pilih PO", df.id.tolist(), key="sel_po", format_func=lambda x: f"{df.loc[df.id==x,'po_no'].iloc[0]} - {df.loc[df.id==x,'vendor'].iloc[0]}")
            sel = df.loc[df.id==psel].iloc[0]
            
            if sel.approval_status == 'Approved':
                st.warning("Data ini sudah disetujui (Approved) dan tidak dapat diubah lagi.")
            else:
                if perm("po","edit"):
                    st.info(FORM_INSTRUCTION)
                    a, b, c = st.columns(3)
                    e_no = a.text_input("PO No *", sel.po_no, key="epo_no")
                    e_ven = b.text_input("Vendor *", sel.vendor, key="epo_ven")
                    e_dt = c.date_input("Tanggal *", datetime.strptime(sel.date, "%Y-%m-%d").date() if sel.date else date.today(), key="epo_dt")
                    
                    d, e, f = st.columns(3)
                    e_desc = d.text_input("Deskripsi", sel.description if pd.notna(sel.description) else "", key="epo_d")
                    e_val = e.number_input("Nilai PO (Rp) *", 0., value=float(sel.po_value), help=CURRENCY_HELP, key="epo_v")
                    with e: render_live_format(e_val)
                    e_paid = f.number_input("Paid (Rp)", 0., value=float(sel.paid_value), help=CURRENCY_HELP, key="epo_p")
                    with f: render_live_format(e_paid)
                    
                    if st.button("Update PO", type="primary", key="btn_upd_po"):
                        if not e_no.strip() or not e_ven.strip():
                            st.error("Nomor PO dan Vendor wajib diisi!")
                        else:
                            s, _, err = execute("UPDATE purchase_orders SET po_no=?, vendor=?, date=?, description=?, po_value=?, paid_value=? WHERE id=?", 
                                                (e_no, e_ven, str(e_dt), e_desc, e_val, e_paid, psel))
                            if s: 
                                audit("UPDATE", "po", "purchase_orders", psel, e_no)
                                st.success("Data Purchase Order berhasil diperbarui!")
                                st.rerun()
                            else: st.error(err)
                            
                if perm("po","delete"):
                    st.write("")
                    with st.expander("⚠️ Hapus Purchase Order (PO)"):
                        st.warning("Data PO yang dihapus tidak dapat dikembalikan.")
                        if st.button("Hapus Secara Permanen", type="primary", key="btn_del_po"):
                            s, _, err = execute("DELETE FROM purchase_orders WHERE id=?", (psel,))
                            if s: 
                                audit("DELETE", "po", "purchase_orders", psel)
                                st.success("Purchase Order berhasil dihapus!")
                                st.rerun()
                            else: st.error(err)
                            
    with tab3:
        if role in ["Admin","Manager"]:
            if df.empty or df[df.approval_status != 'Approved'].empty:
                st.success("Tidak ada PO yang menunggu persetujuan.")
            else:
                rid = st.selectbox("Pilih PO untuk disetujui", df[df.approval_status != 'Approved'].id.tolist(), key="sel_appr_po", format_func=lambda x: f"{df.loc[df.id==x,'po_no'].iloc[0]} - {df.loc[df.id==x,'vendor'].iloc[0]}")
                if rid and st.button("Approve PO", type="primary", key="btn_appr_po"):
                    s, _, err = execute("UPDATE purchase_orders SET approval_status='Approved',approved_by=?,approved_at=? WHERE id=?", (user["username"], now(), rid))
                    if s: 
                        audit("APPROVE", "po", "purchase_orders", rid)
                        st.success("Purchase Order berhasil disetujui!")
                        st.rerun()
                    else: st.error(err)
        else: 
            st.info("Hanya Admin atau Manager yang dapat memberikan persetujuan.")

if not df.empty:
    st.markdown("#### 📋 Daftar Purchase Order (PO)")
    disp = df.copy()
    disp["outstanding"] = disp.po_value - disp.paid_value
    
    # Format Currency
    disp["po_value"] = disp["po_value"].apply(lambda x: money(x))
    disp["paid_value"] = disp["paid_value"].apply(lambda x: money(x))
    disp["outstanding"] = disp["outstanding"].apply(lambda x: money(x))
    
    disp = disp.rename(columns={
        "id": "ID", "project_id": "ID Proyek", "po_no": "No. PO",
        "vendor": "Vendor", "date": "Tanggal", "description": "Deskripsi",
        "po_value": "Nilai PO", "paid_value": "Sudah Dibayar",
        "outstanding": "Outstanding / Sisa", "approval_status": "Status Approval",
        "approved_by": "Disetujui Oleh", "approved_at": "Tanggal Disetujui"
    })
    
    st.dataframe(disp, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Grand Total PO", money(df.po_value.sum()))
    c2.metric("Total Terbayar", money(df.paid_value.sum()))
    c3.metric("Total Outstanding", money((df.po_value - df.paid_value).sum()))
