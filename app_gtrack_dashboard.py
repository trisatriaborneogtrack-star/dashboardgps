"""
GPS Tracking Dashboard - Trisatria Persada Borneo
Streamlit + SQLite | Breakdown Status Persistent
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os
from datetime import datetime

st.set_page_config(
    page_title="GPS Dashboard – Trisatria Persada Borneo",
    page_icon="📡",
    layout="wide",
)

DB_PATH = "breakdown_status.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── SQLite ─────────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS breakdown (
            unit_id      TEXT PRIMARY KEY,
            fleet_group  TEXT,
            vehicle_code TEXT,
            catatan      TEXT,
            teknisi      TEXT,
            updated_at   TEXT
        )
    """)
    conn.commit()
    return conn

def load_breakdown():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM breakdown", conn)
    conn.close()
    return df

def save_breakdown(unit_id, fleet, code, catatan, teknisi):
    conn = get_conn()
    conn.execute("""
        INSERT INTO breakdown (unit_id, fleet_group, vehicle_code, catatan, teknisi, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(unit_id) DO UPDATE SET
            catatan=excluded.catatan,
            teknisi=excluded.teknisi,
            updated_at=excluded.updated_at
    """, (str(unit_id), fleet, code, catatan, teknisi,
          datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def delete_breakdown(unit_id):
    conn = get_conn()
    conn.execute("DELETE FROM breakdown WHERE unit_id = ?", (str(unit_id),))
    conn.commit()
    conn.close()

# ── Load Excel ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_excel(file_bytes):
    df = pd.read_excel(file_bytes)
    df.columns = df.columns.str.strip()
    df["Unit ID"] = df["Unit ID"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Local Time"] = pd.to_datetime(df["Local Time"], errors="coerce")
    return df

# ── Session state ──────────────────────────────────────────────────────────────
if "modal_unit" not in st.session_state:
    st.session_state.modal_unit = None
if "page_num" not in st.session_state:
    st.session_state.page_num = 1

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📁 Upload Group Project")
    uploaded = st.file_uploader("Upload file .xlsx", type=["xlsx"])
    st.caption("Upload tiap pagi. Status Breakdown tidak akan terhapus.")

    st.divider()
    st.markdown("### 🔍 Filter")
    filter_status = st.selectbox("Status", ["Semua", "Tracking", "Stop", "GPRS Lost", "Breakdown"])
    search_text = st.text_input("Cari kode / unit ID / fleet")

    st.divider()
    bd_sidebar = load_breakdown()
    st.metric("Breakdown aktif", len(bd_sidebar))
    if not bd_sidebar.empty:
        if st.button("🗑 Reset semua breakdown", type="secondary"):
            conn = get_conn()
            conn.execute("DELETE FROM breakdown")
            conn.commit()
            conn.close()
            st.rerun()

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.big-metric { font-size:2.2rem; font-weight:700; line-height:1; }
.metric-label { font-size:0.78rem; color:#888; margin-top:2px; }
.tbl-header {
    display:flex; align-items:center; padding:7px 10px;
    background:#f9fafb; border:1px solid #e5e7eb;
    border-radius:6px 6px 0 0;
    font-size:11px; font-weight:600; color:#6b7280; gap:8px;
}
.row-info {
    display:flex; align-items:center; padding:7px 10px;
    border-left:1px solid #e5e7eb; border-right:1px solid #e5e7eb;
    border-bottom:1px solid #f3f4f6; gap:8px; flex-wrap:nowrap;
}
.row-info:hover { background:#fafafa; }
.col-fleet  { flex:2; min-width:110px; font-size:12px; color:#374151; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.col-uid    { flex:1.2; min-width:80px; font-size:11px; color:#9ca3af; font-family:monospace; }
.col-code   { flex:1.4; min-width:90px; font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.col-time   { flex:1.4; min-width:100px; font-size:11px; color:#9ca3af; }
.col-res    { flex:1.3; min-width:90px; font-size:11px; color:#6b7280; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.col-status { flex:0.9; min-width:75px; }
.badge-tracking  { background:#d1fae5; color:#065f46; padding:2px 7px; border-radius:4px; font-size:11px; font-weight:500; }
.badge-stop      { background:#f3f4f6; color:#374151; padding:2px 7px; border-radius:4px; font-size:11px; font-weight:500; }
.badge-lost      { background:#fee2e2; color:#991b1b; padding:2px 7px; border-radius:4px; font-size:11px; font-weight:500; }
.badge-breakdown { background:#fef3c7; color:#92400e; padding:2px 7px; border-radius:4px; font-size:11px; font-weight:500; }
/* Rapatkan jarak antar elemen baris */
div[data-testid="stHorizontalBlock"] { gap: 0 !important; margin-bottom: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([1, 4])
with c1:
    st.markdown("<span style='font-size:2rem;font-weight:700;color:#ff6b35'>G<span style='color:#1e3a5f'>track</span></span>", unsafe_allow_html=True)
with c2:
    st.markdown("**GPS Tracking Dashboard** — Trisatria Persada Borneo")
    st.caption(f"Data diperbarui: {datetime.now().strftime('%d %B %Y %H:%M')}")

st.divider()

if uploaded is None:
    st.info("⬅ Upload file Group Project (.xlsx) di sidebar untuk memulai.")
    st.stop()

# ── Load & merge ───────────────────────────────────────────────────────────────
df    = load_excel(uploaded)
bd_df = load_breakdown()
bd_ids = set(bd_df["unit_id"].astype(str).tolist())

df["_breakdown"]      = df["Unit ID"].isin(bd_ids)
df["_display_status"] = df.apply(
    lambda r: "Breakdown" if r["_breakdown"] else str(r.get("Vehicle Status", "") or ""), axis=1
)

# ── KPI ────────────────────────────────────────────────────────────────────────
total       = len(df)
no_update   = int((df["Vehicle Status"] == "GPRS Lost").sum())
tracking    = int((df["Vehicle Status"] == "Tracking").sum())
stop        = int((df["Vehicle Status"] == "Stop").sum())
n_breakdown = len(bd_ids & set(df["Unit ID"].tolist()))

kcols = st.columns(5)
for col, label, val, color in [
    (kcols[0], "Total Unit", total,       "#1e3a5f"),
    (kcols[1], "No Update",  no_update,   "#ef4444"),
    (kcols[2], "Tracking",   tracking,    "#10b981"),
    (kcols[3], "Stop",       stop,        "#6b7280"),
    (kcols[4], "Breakdown",  n_breakdown, "#f59e0b"),
]:
    with col:
        st.markdown(f"""
        <div style='padding:12px 16px;border-radius:8px;border:1px solid #e5e7eb'>
          <div class='big-metric' style='color:{color}'>{val}</div>
          <div class='metric-label'>{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("")

# ── Charts ─────────────────────────────────────────────────────────────────────
cp, cb = st.columns([1, 2])
with cp:
    st.markdown("##### Distribusi Status")
    fig_pie = go.Figure(go.Pie(
        labels=["Update", "No Update", "Breakdown"],
        values=[max(0, total - no_update - n_breakdown), no_update, n_breakdown],
        marker_colors=["#6b7280", "#ef4444", "#f59e0b"],
        hole=0.45, textinfo="percent", showlegend=True,
    ))
    fig_pie.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=220,
                          legend=dict(orientation="v", x=1, y=0.5),
                          paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_pie, use_container_width=True)

with cb:
    st.markdown("##### Top 10 Fleet — GPRS Lost")
    top_lost = (df[df["Vehicle Status"] == "GPRS Lost"]
                .groupby("Fleet Group").size().sort_values(ascending=False).head(10))
    if not top_lost.empty:
        fig_bar = go.Figure(go.Bar(
            x=top_lost.values, y=top_lost.index, orientation="h",
            marker_color="#ef4444", opacity=0.8
        ))
        fig_bar.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=220,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_bar, use_container_width=True)

# ── Filter ─────────────────────────────────────────────────────────────────────
fdf = df.copy()
if filter_status != "Semua":
    fdf = fdf[fdf["_display_status"] == filter_status]
if search_text:
    q = search_text.lower()
    fdf = fdf[
        fdf["Vehicle Code"].astype(str).str.lower().str.contains(q, na=False) |
        fdf["Unit ID"].astype(str).str.lower().str.contains(q, na=False) |
        fdf["Fleet Group"].astype(str).str.lower().str.contains(q, na=False)
    ]
fdf = fdf.reset_index(drop=True)

# ── Pagination ──────────────────────────────────────────────────────────────────
PER_PAGE    = 20
total_rows  = len(fdf)
total_pages = max(1, (total_rows + PER_PAGE - 1) // PER_PAGE)
if st.session_state.page_num > total_pages:
    st.session_state.page_num = 1

st.divider()
st.markdown(f"#### Daftar Unit &nbsp;<span style='font-size:13px;color:#9ca3af'>{total_rows} unit ditampilkan</span>", unsafe_allow_html=True)

# ── Modal breakdown ─────────────────────────────────────────────────────────────
if st.session_state.modal_unit is not None:
    mu       = st.session_state.modal_unit
    is_active = mu["unit_id"] in bd_ids
    bd_row   = bd_df[bd_df["unit_id"] == mu["unit_id"]]

    with st.container(border=True):
        st.markdown(f"**{'✏ Edit' if is_active else '⚠ Tandai'} Breakdown** — "
                    f"`{mu['code']}` &nbsp;·&nbsp; {mu['fleet']}")
        mc1, mc2 = st.columns(2)
        with mc1:
            default_tek = bd_row.iloc[0]["teknisi"] if is_active and not bd_row.empty else ""
            inp_tek = st.text_input("Nama Teknisi / Koordinator", value=default_tek, key="inp_tek")
        with mc2:
            default_cat = bd_row.iloc[0]["catatan"] if is_active and not bd_row.empty else ""
            inp_cat = st.text_input("Catatan", value=default_cat, key="inp_cat",
                                    placeholder="cth: kabel antena putus")

        bc1, bc2, bc3, _ = st.columns([1, 1, 1, 4])
        with bc1:
            if st.button("💾 Simpan", type="primary", key="btn_simpan"):
                save_breakdown(mu["unit_id"], mu["fleet"], mu["code"], inp_cat, inp_tek)
                st.session_state.modal_unit = None
                st.rerun()
        with bc2:
            if st.button("✕ Batal", key="btn_batal"):
                st.session_state.modal_unit = None
                st.rerun()
        if is_active:
            with bc3:
                if st.button("🗑 Hapus Status", key="btn_hapus"):
                    delete_breakdown(mu["unit_id"])
                    st.session_state.modal_unit = None
                    st.rerun()

# ── Tabel header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class='tbl-header'>
  <div style='flex:2;min-width:110px'>Fleet Group</div>
  <div style='flex:1.2;min-width:80px'>Unit ID</div>
  <div style='flex:1.4;min-width:90px'>Vehicle Code</div>
  <div style='flex:1.4;min-width:100px'>Local Time</div>
  <div style='flex:1.3;min-width:90px'>Resource</div>
  <div style='flex:0.9;min-width:75px'>Status</div>
  <div style='flex:0.9;min-width:100px'>Aksi</div>
</div>
""", unsafe_allow_html=True)

# ── Render baris tabel ─────────────────────────────────────────────────────────
BADGE = {
    "Tracking":  "badge-tracking",
    "Stop":      "badge-stop",
    "GPRS Lost": "badge-lost",
    "Breakdown": "badge-breakdown",
}

start    = (st.session_state.page_num - 1) * PER_PAGE
page_df  = fdf.iloc[start : start + PER_PAGE]

for idx, row in page_df.iterrows():
    uid    = str(row["Unit ID"])
    fleet  = str(row.get("Fleet Group", "") or "")
    code   = str(row.get("Vehicle Code", "") or "")
    ttime  = row["Local Time"].strftime("%Y-%m-%d %H:%M") if pd.notna(row["Local Time"]) else "-"
    res    = str(row.get("Resource", "") or "")
    status = str(row["_display_status"])
    is_bd  = bool(row["_breakdown"])
    badge  = BADGE.get(status, "badge-stop")
    bd_info = bd_df[bd_df["unit_id"] == uid]

    # Info kolom pakai HTML
    st.markdown(f"""
    <div class='row-info'>
      <div class='col-fleet' title='{fleet}'>{fleet}</div>
      <div class='col-uid'>{uid}</div>
      <div class='col-code' title='{code}'>{code}</div>
      <div class='col-time'>{ttime}</div>
      <div class='col-res' title='{res}'>{res}</div>
      <div class='col-status'><span class='{badge}'>{status}</span></div>
      <div style='flex:0.9;min-width:100px'></div>
    </div>
    """, unsafe_allow_html=True)

    # Tombol Streamlit — menumpuk di bawah baris, di kolom kanan
    _, btn_area = st.columns([8.5, 1.5])
    with btn_area:
        label = "⚠ Edit BD" if is_bd else "+ Breakdown"
        btn_type = "primary" if is_bd else "secondary"
        if st.button(label, key=f"bd_{uid}_{idx}", type=btn_type, use_container_width=True):
            st.session_state.modal_unit = {"unit_id": uid, "fleet": fleet, "code": code}
            st.rerun()

    # Tampilkan catatan di bawah baris jika breakdown aktif
    if is_bd and not bd_info.empty:
        bdi = bd_info.iloc[0]
        note_text = f"📝 {bdi['catatan']}" if bdi['catatan'] else ""
        tech_text = f"👤 {bdi['teknisi']}" if bdi['teknisi'] else ""
        if note_text or tech_text:
            st.markdown(
                f"<div style='font-size:11px;color:#92400e;background:#fffbeb;"
                f"padding:3px 10px;border-left:3px solid #fcd34d;margin-bottom:2px'>"
                f"{note_text} &nbsp; {tech_text}</div>",
                unsafe_allow_html=True
            )

# ── Pagination ─────────────────────────────────────────────────────────────────
st.markdown("")
pg1, pg2, pg3 = st.columns([1, 3, 1])
with pg1:
    if st.button("◀ Prev", disabled=st.session_state.page_num <= 1, use_container_width=True):
        st.session_state.page_num -= 1
        st.rerun()
with pg2:
    st.markdown(
        f"<div style='text-align:center;font-size:13px;padding-top:6px'>"
        f"Halaman {st.session_state.page_num} / {total_pages} &nbsp;·&nbsp; "
        f"Baris {start+1}–{min(start+PER_PAGE, total_rows)} dari {total_rows}</div>",
        unsafe_allow_html=True
    )
with pg3:
    if st.button("Next ▶", disabled=st.session_state.page_num >= total_pages, use_container_width=True):
        st.session_state.page_num += 1
        st.rerun()

# ── Daftar breakdown aktif ─────────────────────────────────────────────────────
st.divider()
st.markdown("#### 📋 Daftar Breakdown Aktif")
bd_now = load_breakdown()
if bd_now.empty:
    st.info("Tidak ada unit dalam status Breakdown saat ini.")
else:
    for _, brow in bd_now.iterrows():
        with st.expander(f"⚠ {brow['vehicle_code']} · {brow['fleet_group']} · ID: {brow['unit_id']}"):
            st.write(f"**Catatan:** {brow['catatan'] or '-'}")
            st.write(f"**Teknisi:** {brow['teknisi'] or '-'}")
            st.write(f"**Diperbarui:** {brow['updated_at']}")
            if st.button("🗑 Hapus status ini", key=f"del_{brow['unit_id']}"):
                delete_breakdown(brow["unit_id"])
                st.rerun()

st.divider()
st.caption(f"GPS Tracking Dashboard · Trisatria Persada Borneo · Powered by Streamlit + SQLite · {datetime.now().year}")
