"""
GPS Tracking Dashboard - Trisatria Persada Borneo
Streamlit + SQLite | Breakdown Status Persistent

Cara pakai:
  pip install streamlit pandas openpyxl plotly
  streamlit run app_gtrack_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GPS Dashboard – Trisatria Persada Borneo",
    page_icon="📡",
    layout="wide",
)

DB_PATH = "breakdown_status.db"   # file SQLite lokal, tidak ikut terhapus saat Excel baru diupload
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── SQLite helpers ─────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS breakdown (
            unit_id     TEXT PRIMARY KEY,
            fleet_group TEXT,
            vehicle_code TEXT,
            catatan     TEXT,
            teknisi     TEXT,
            updated_at  TEXT
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

# ── Sidebar: upload ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📁 Upload Group Project")
    uploaded = st.file_uploader("Upload file .xlsx", type=["xlsx"])
    st.caption("Upload tiap pagi. Status Breakdown tidak akan terhapus.")

    st.divider()
    st.markdown("### 🔍 Filter")
    filter_fleet = st.selectbox("Fleet Group", ["Semua"])
    filter_status = st.selectbox("Status GPS", ["Semua", "Tracking", "Stop", "GPRS Lost", "Breakdown"])
    search_text = st.text_input("Cari kode unit / unit ID")

    st.divider()
    st.markdown("### 📊 Database Breakdown")
    bd_df = load_breakdown()
    st.metric("Total Breakdown aktif", len(bd_df))
    if not bd_df.empty:
        if st.button("🗑 Reset semua breakdown", type="secondary"):
            conn = get_conn()
            conn.execute("DELETE FROM breakdown")
            conn.commit()
            conn.close()
            st.rerun()

# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.big-metric { font-size: 2.2rem; font-weight: 700; line-height: 1; }
.metric-label { font-size: 0.78rem; color: #888; margin-top: 2px; }
.badge-tracking { background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:4px; font-size:12px; }
.badge-stop { background:#f3f4f6; color:#374151; padding:2px 8px; border-radius:4px; font-size:12px; }
.badge-lost { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:4px; font-size:12px; }
.badge-breakdown { background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:4px; font-size:12px; }
</style>
""", unsafe_allow_html=True)

# Header
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.markdown("<span style='font-size:2rem; font-weight:700; color:#ff6b35'>G<span style='color:#1e3a5f'>track</span></span>", unsafe_allow_html=True)
with col_title:
    st.markdown("**GPS Tracking Dashboard** — Trisatria Persada Borneo")
    st.caption(f"Data diperbarui: {datetime.now().strftime('%d %B %Y %H:%M')}")

st.divider()

if uploaded is None:
    st.info("⬅ Upload file Group Project (.xlsx) di sidebar untuk memulai.")
    st.stop()

# Load data
df = load_excel(uploaded)
bd_df = load_breakdown()

# Merge breakdown status
bd_ids = set(bd_df["unit_id"].astype(str).tolist())
df["_breakdown"] = df["Unit ID"].isin(bd_ids)
df["_display_status"] = df.apply(
    lambda r: "Breakdown" if r["_breakdown"] else r.get("Vehicle Status", ""), axis=1
)

# Update sidebar filter options
all_fleets = ["Semua"] + sorted(df["Fleet Group"].dropna().unique().tolist())
# (Note: in production rebuild the selectbox options from data)

# Apply filters
fdf = df.copy()
if filter_fleet != "Semua":
    fdf = fdf[fdf["Fleet Group"] == filter_fleet]
if filter_status != "Semua":
    fdf = fdf[fdf["_display_status"] == filter_status]
if search_text:
    q = search_text.lower()
    fdf = fdf[
        fdf["Vehicle Code"].astype(str).str.lower().str.contains(q, na=False) |
        fdf["Unit ID"].astype(str).str.lower().str.contains(q, na=False) |
        fdf["Fleet Group"].astype(str).str.lower().str.contains(q, na=False)
    ]

# ── KPI cards ──────────────────────────────────────────────────────────────────
total       = len(df)
no_update   = (df["Vehicle Status"] == "GPRS Lost").sum()
tracking    = (df["Vehicle Status"] == "Tracking").sum()
stop        = (df["Vehicle Status"] == "Stop").sum()
n_breakdown = len(bd_ids & set(df["Unit ID"].tolist()))

k1, k2, k3, k4, k5 = st.columns(5)
for col, label, val, color in [
    (k1, "Total Unit",       total,       "#1e3a5f"),
    (k2, "No Update",        no_update,   "#ef4444"),
    (k3, "Tracking",         tracking,    "#10b981"),
    (k4, "Stop",             stop,        "#6b7280"),
    (k5, "Breakdown",        n_breakdown, "#f59e0b"),
]:
    with col:
        st.markdown(f"""
        <div style='padding:12px 16px; border-radius:8px; border:1px solid #e5e7eb'>
          <div class='big-metric' style='color:{color}'>{val}</div>
          <div class='metric-label'>{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# ── Charts ─────────────────────────────────────────────────────────────────────
col_pie, col_bar = st.columns([1, 2])

with col_pie:
    st.markdown("##### Distribusi Status")
    fig_pie = go.Figure(go.Pie(
        labels=["Update", "No Update", "Breakdown"],
        values=[total - no_update - n_breakdown, no_update, n_breakdown],
        marker_colors=["#6b7280", "#ef4444", "#f59e0b"],
        hole=0.45, textinfo="percent", showlegend=True,
    ))
    fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=240,
                          legend=dict(orientation="v", x=1, y=0.5), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    st.markdown("##### Top 10 Fleet Group — Unit GPRS Lost")
    top_lost = (df[df["Vehicle Status"] == "GPRS Lost"]
                .groupby("Fleet Group").size().sort_values(ascending=False).head(10))
    if not top_lost.empty:
        fig_bar = go.Figure(go.Bar(
            x=top_lost.values, y=top_lost.index, orientation="h",
            marker_color="#ef4444", opacity=0.8
        ))
        fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=240,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_bar, use_container_width=True)

# ── Main table ─────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"#### Daftar Unit ({len(fdf)} ditampilkan dari {total} total)")

cols_show = ["Fleet Group", "Unit ID", "Vehicle Code", "Local Time",
             "Resource", "_display_status", "_breakdown"]

display_df = fdf[cols_show].copy()
display_df.columns = ["Fleet Group", "Unit ID", "Vehicle Code", "Local Time",
                       "Resource", "Status", "Breakdown?"]
display_df["Local Time"] = display_df["Local Time"].dt.strftime("%Y-%m-%d %H:%M").fillna("-")

st.dataframe(
    display_df,
    use_container_width=True,
    height=420,
    column_config={
        "Breakdown?": st.column_config.CheckboxColumn("BD", disabled=True),
        "Status": st.column_config.TextColumn("Status"),
    }
)

# ── Breakdown management panel ──────────────────────────────────────────────────
st.divider()
st.markdown("#### ⚠ Manajemen Status Breakdown")
st.caption("Status yang ditambahkan di sini akan tetap tersimpan meski file Excel diperbarui besok.")

tab_add, tab_list = st.tabs(["➕ Tambah / Edit Breakdown", "📋 Daftar Breakdown Aktif"])

with tab_add:
    with st.form("form_breakdown"):
        st.markdown("**Input Unit ID yang akan ditandai Breakdown:**")
        c1, c2 = st.columns(2)
        with c1:
            sel_unit = st.text_input("Unit ID", placeholder="cth: 3030022547")
        with c2:
            sel_tech = st.text_input("Nama Koordinator / Teknisi", placeholder="cth: Andi Wijaya")
        catatan = st.text_area("Catatan Breakdown", placeholder="cth: Kabel antena GPS putus, perlu pengecekan di lapangan", height=80)
        submitted = st.form_submit_button("💾 Simpan Status Breakdown", type="primary")
        if submitted:
            if not sel_unit.strip():
                st.error("Unit ID tidak boleh kosong.")
            else:
                matched = df[df["Unit ID"] == sel_unit.strip()]
                fleet = matched.iloc[0]["Fleet Group"] if not matched.empty else "-"
                code  = matched.iloc[0]["Vehicle Code"] if not matched.empty else "-"
                save_breakdown(sel_unit.strip(), fleet, str(code), catatan, sel_tech)
                st.success(f"✅ Status Breakdown disimpan untuk Unit ID: {sel_unit.strip()}")
                st.rerun()

with tab_list:
    bd_df = load_breakdown()
    if bd_df.empty:
        st.info("Tidak ada unit dalam status Breakdown saat ini.")
    else:
        for _, row in bd_df.iterrows():
            with st.expander(f"⚠ {row['vehicle_code']} · {row['fleet_group']} · ID: {row['unit_id']}"):
                st.write(f"**Catatan:** {row['catatan'] or '-'}")
                st.write(f"**Teknisi:** {row['teknisi'] or '-'}")
                st.write(f"**Diperbarui:** {row['updated_at']}")
                if st.button(f"🗑 Hapus status breakdown — {row['unit_id']}", key=f"del_{row['unit_id']}"):
                    delete_breakdown(row["unit_id"])
                    st.success("Status dihapus.")
                    st.rerun()

# ── Footer ──────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Dashboard GPS Tracking · Trisatria Persada Borneo · "
    f"Powered by Streamlit + SQLite · {datetime.now().strftime('%Y')}"
)
