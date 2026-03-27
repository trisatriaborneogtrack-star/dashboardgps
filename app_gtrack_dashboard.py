"""
GPS Tracking Dashboard - Trisatria Persada Borneo
Streamlit + SQLite | Upload per session | Multi-status persisten
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

# Daftar status yang bisa dipilih koordinator
STATUS_OPTIONS = [
    "Breakdown",
    "Standby",
    "Sudah dismantle",
    "Plan dismantle",
    "Offhire",
]

# ── SQLite ─────────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS unit_status (
            unit_id      TEXT PRIMARY KEY,
            fleet_group  TEXT,
            vehicle_code TEXT,
            status       TEXT,
            catatan      TEXT,
            teknisi      TEXT,
            updated_at   TEXT
        )
    """)
    # Migrasi dari tabel lama 'breakdown' jika ada
    try:
        conn.execute("""
            INSERT OR IGNORE INTO unit_status
                (unit_id, fleet_group, vehicle_code, status, catatan, teknisi, updated_at)
            SELECT unit_id, fleet_group, vehicle_code, 'Breakdown', catatan, teknisi, updated_at
            FROM breakdown
        """)
        conn.commit()
    except Exception:
        pass
    return conn

def load_unit_status():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM unit_status", conn)
    conn.close()
    return df

def save_unit_status(unit_id, fleet, code, status, catatan, teknisi):
    conn = get_conn()
    conn.execute("""
        INSERT INTO unit_status (unit_id, fleet_group, vehicle_code, status, catatan, teknisi, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(unit_id) DO UPDATE SET
            status=excluded.status,
            catatan=excluded.catatan,
            teknisi=excluded.teknisi,
            updated_at=excluded.updated_at
    """, (str(unit_id), fleet, code, status, catatan, teknisi,
          datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def delete_unit_status(unit_id):
    conn = get_conn()
    conn.execute("DELETE FROM unit_status WHERE unit_id = ?", (str(unit_id),))
    conn.commit()
    conn.close()

# ── Load Excel ─────────────────────────────────────────────────────────────────
COL_MAP = {
    "Grup Fleet":       "Fleet Group",
    "Kode Kendaraan":   "Vehicle Code",
    "Status Kendaraan": "Vehicle Status",
    "Waktu lokal":      "Local Time",
    "Sumber daya":      "Resource",
    "Kecepatan":        "Speed",
}

@st.cache_data
def load_excel(file_bytes):
    df = pd.read_excel(file_bytes, header=0)
    df.columns = df.columns.str.strip()
    if "Unit ID" not in df.columns and "Fleet Group" not in df.columns and "Grup Fleet" not in df.columns:
        df = pd.read_excel(file_bytes, header=1)
        df.columns = df.columns.str.strip()
    df = df.rename(columns=COL_MAP)
    if "Unit ID" in df.columns:
        df["Unit ID"] = (
            df["Unit ID"].astype(str)
            .str.replace(".0", "", regex=False)
            .str.replace("nan", "", regex=False)
            .str.strip()
        )
    else:
        df["Unit ID"] = ""
    for col in ["Fleet Group", "Vehicle Code", "Vehicle Status", "Resource", "Speed", "ACC"]:
        if col not in df.columns:
            df[col] = ""
    df["Local Time"] = pd.to_datetime(df.get("Local Time"), errors="coerce")
    return df

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in [("modal_unit", None), ("page_num", 1)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.big-metric   { font-size:2.2rem; font-weight:700; line-height:1; }
.metric-label { font-size:0.78rem; color:#888; margin-top:2px; }
.cell     { padding:6px 8px; font-size:12px; border-bottom:1px solid rgba(128,128,128,0.12);
            overflow:hidden; text-overflow:ellipsis; white-space:nowrap; line-height:1.6; }
.cell-hdr { padding:6px 8px; font-size:11px; font-weight:600; color:#6b7280;
            border-bottom:2px solid rgba(128,128,128,0.2);
            background:rgba(128,128,128,0.05); }
.bd-note  { font-size:11px; padding:3px 10px; border-left:3px solid #d1d5db; margin-bottom:1px; }
/* Badge status GPS */
.badge-update     { background:#d1fae5;color:#065f46;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:500; }
.badge-noupdate   { background:#fee2e2;color:#991b1b;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:500; }
.badge-power      { background:#fde8d8;color:#7c2d12;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:500; }
.badge-antenna    { background:#ede9fe;color:#4c1d95;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:500; }
.badge-acc        { background:#fef9c3;color:#713f12;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:500; }
.badge-uninstall  { background:#f3f4f6;color:#6b7280;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:500;font-style:italic; }
/* Badge status koordinator */
.badge-breakdown  { background:#fef3c7;color:#92400e;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600; }
.badge-standby    { background:#dbeafe;color:#1e40af;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600; }
.badge-dismantle  { background:#f1f5f9;color:#334155;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600; }
.badge-plan       { background:#ffedd5;color:#9a3412;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600; }
.badge-offhire    { background:#f3e8ff;color:#6b21a8;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600; }
[data-testid="stHorizontalBlock"] { gap:0 !important; align-items:center !important; }
[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:last-child
    [data-testid="stBaseButton-secondary"],
[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:last-child
    [data-testid="stBaseButton-primary"] {
    height:28px !important; padding:0 6px !important; font-size:10px !important;
    white-space:nowrap !important; overflow:hidden !important;
    text-overflow:ellipsis !important; min-width:0 !important; margin-top:2px;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<span style='font-size:1.6rem;font-weight:700;color:#ff6b35'>G<span style='color:#1e3a5f'>track</span></span>", unsafe_allow_html=True)
    st.caption("Trisatria Persada Borneo")
    st.divider()

    st.markdown("### 📁 Upload Group Project")
    uploaded = st.file_uploader("Upload file .xlsx", type=["xlsx"])
    st.caption("Upload tiap pagi. Status unit tidak akan terhapus.")

    st.divider()
    st.markdown("### 🔍 Filter")
    filter_status = st.selectbox("Status", [
        "Semua", "Update", "No Update", "Belum diinstal",
        "Indikasi kabel power GPS lepas/kendor",
        "Indikasi antena GPS lepas/kendor",
        "Indikasi ACC bermasalah",
        "Breakdown", "Standby", "Sudah dismantle", "Plan dismantle", "Offhire",
    ])
    fleet_options = ["Semua"] + sorted(st.session_state.get("fleet_list", []))
    filter_fleet  = st.selectbox("Fleet Group", fleet_options)
    search_text   = st.text_input("Cari kode / unit ID / fleet")

    st.divider()
    us_sidebar = load_unit_status()
    st.metric("Status Unit Tidak Aktif", len(us_sidebar))
    # Ringkasan per status
    if not us_sidebar.empty:
        counts = us_sidebar["status"].value_counts()
        for s, c in counts.items():
            st.caption(f"• {s}: {c}")
        st.markdown("")
        if st.button("🗑 Reset semua status", type="secondary"):
            conn = get_conn(); conn.execute("DELETE FROM unit_status"); conn.commit(); conn.close()
            st.rerun()

# ── Header ─────────────────────────────────────────────────────────────────────
h1, h2 = st.columns([1, 5])
with h1:
    st.markdown("<span style='font-size:2rem;font-weight:700;color:#ff6b35'>G<span style='color:#1e3a5f'>track</span></span>", unsafe_allow_html=True)
with h2:
    st.markdown("**GPS Tracking Dashboard** — Trisatria Persada Borneo")
    st.caption(f"Data diperbarui: {datetime.now().strftime('%d %B %Y %H:%M')}")

st.divider()

if uploaded is None:
    st.info("⬅ Upload file Group Project (.xlsx) di sidebar untuk memulai.")
    st.stop()

# ── Load & proses data ─────────────────────────────────────────────────────────
df     = load_excel(uploaded)
us_df  = load_unit_status()
us_ids = set(us_df["unit_id"].astype(str).tolist())
# Map unit_id -> status koordinator
us_map = dict(zip(us_df["unit_id"].astype(str), us_df["status"]))

df["_has_status"] = df["Unit ID"].isin(us_ids)

# Hitung hari no update dulu sebelum compute_status
now = pd.Timestamp.now()
df["_days_no_update"] = df["Local Time"].apply(
    lambda t: int((now - t).days) if pd.notna(t) else None
)

def compute_status(r):
    # Status koordinator selalu prioritas tertinggi
    if r["_has_status"]:
        return us_map.get(str(r["Unit ID"]), "Breakdown")
    # Belum diinstal
    if pd.isna(r.get("Local Time")):
        return "Belum diinstal"
    # No Update
    days = r.get("_days_no_update")
    if days is not None and not (isinstance(days, float) and pd.isna(days)) and days > 0:
        return "No Update"
    # Indikasi masalah hardware
    resource = str(r.get("Resource", "") or "")
    acc      = str(r.get("ACC", "") or "")
    speed    = r.get("Speed", 0) or 0
    if resource in ("Main Power Remove", "Backup Battery Low", "Main Power Low"):
        return "Indikasi kabel power GPS lepas/kendor"
    if resource in ("GPS Antenna Disconnect", "GPS Antenna Re Connect"):
        return "Indikasi antena GPS lepas/kendor"
    try:
        if acc == "OFF" and float(speed) > 10:
            return "Indikasi ACC bermasalah"
    except (ValueError, TypeError):
        pass
    return "Update"

df["_display_status"] = df.apply(compute_status, axis=1)

# Urutkan dari Local Time terlama ke terbaru
df = df.sort_values("Local Time", ascending=True, na_position="first").reset_index(drop=True)

# Simpan daftar fleet ke session_state
fleet_list = sorted(df["Fleet Group"].dropna().unique().tolist())
if st.session_state.get("fleet_list") != fleet_list:
    st.session_state["fleet_list"] = fleet_list
    st.rerun()

# ── KPI ────────────────────────────────────────────────────────────────────────
total      = len(df)
no_update  = int((df["_display_status"] == "No Update").sum())
tracking   = int((df["_display_status"] == "Update").sum())
n_breakdown= int((df["_display_status"] == "Breakdown").sum())
n_aktif    = len(us_ids & set(df["Unit ID"].tolist()))

kcols = st.columns(5)
for col, label, val, color in [
    (kcols[0], "Total Unit",    total,      "#1e3a5f"),
    (kcols[1], "No Update",     no_update,  "#ef4444"),
    (kcols[2], "Update",        tracking,   "#10b981"),
    (kcols[3], "Breakdown",     n_breakdown,"#f59e0b"),
    (kcols[4], "Status Aktif",  n_aktif,    "#8b5cf6"),
]:
    with col:
        st.markdown(f"""
        <div style='padding:12px 16px;border-radius:8px;border:1px solid rgba(128,128,128,0.2)'>
          <div class='big-metric' style='color:{color}'>{val}</div>
          <div class='metric-label'>{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("")

# ── Charts ─────────────────────────────────────────────────────────────────────
cp, cb = st.columns([1, 2])
with cp:
    st.markdown("##### Distribusi Status")
    status_counts = df["_display_status"].value_counts()
    fig_pie = go.Figure(go.Pie(
        labels=status_counts.index.tolist(),
        values=status_counts.values.tolist(),
        hole=0.45, textinfo="percent", showlegend=True,
    ))
    fig_pie.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=220,
                          legend=dict(orientation="v", x=1, y=0.5),
                          paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_pie, use_container_width=True)

with cb:
    st.markdown("##### Top 10 Fleet — No Update")
    top_lost = (df[df["_display_status"] == "No Update"]
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
# Abaikan pemisah "── Status Koordinator ──"
if filter_status not in ("Semua", "── Status Koordinator ──"):
    fdf = fdf[fdf["_display_status"] == filter_status]
if filter_fleet != "Semua":
    fdf = fdf[fdf["Fleet Group"] == filter_fleet]
if search_text:
    q = search_text.lower()
    fdf = fdf[
        fdf["Vehicle Code"].astype(str).str.lower().str.contains(q, na=False) |
        fdf["Unit ID"].astype(str).str.lower().str.contains(q, na=False) |
        fdf["Fleet Group"].astype(str).str.lower().str.contains(q, na=False)
    ]
fdf = fdf.reset_index(drop=True)

# ── Pagination ──────────────────────────────────────────────────────────────────
PER_PAGE    = 25
total_rows  = len(fdf)
total_pages = max(1, (total_rows + PER_PAGE - 1) // PER_PAGE)
if st.session_state.page_num > total_pages:
    st.session_state.page_num = 1

st.divider()
st.markdown(f"#### Daftar Unit &nbsp;<span style='font-size:13px;color:#9ca3af'>{total_rows} unit ditampilkan</span>", unsafe_allow_html=True)

# ── Modal status koordinator ───────────────────────────────────────────────────
if st.session_state.modal_unit is not None:
    mu        = st.session_state.modal_unit
    is_active = mu["unit_id"] in us_ids
    us_row    = us_df[us_df["unit_id"] == mu["unit_id"]]

    with st.container(border=True):
        st.markdown(
            f"**{'✏ Edit' if is_active else '＋ Tandai'} Status Unit** — "
            f"`{mu['code']}` &nbsp;·&nbsp; {mu['fleet']}"
        )
        mc0, mc1, mc2 = st.columns(3)
        with mc0:
            current_status = us_row.iloc[0]["status"] if is_active and not us_row.empty else STATUS_OPTIONS[0]
            idx_default    = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
            inp_status = st.selectbox("Status", STATUS_OPTIONS, index=idx_default, key="inp_status")
        with mc1:
            inp_tek = st.text_input("Nama Teknisi / Koordinator",
                value=us_row.iloc[0]["teknisi"] if is_active and not us_row.empty else "",
                key="inp_tek")
        with mc2:
            inp_cat = st.text_input("Catatan",
                value=us_row.iloc[0]["catatan"] if is_active and not us_row.empty else "",
                placeholder="cth: unit dikirim ke workshop", key="inp_cat")

        bc1, bc2, bc3, _ = st.columns([1, 1, 1.5, 4])
        with bc1:
            if st.button("💾 Simpan", type="primary", key="btn_simpan"):
                save_unit_status(mu["unit_id"], mu["fleet"], mu["code"], inp_status, inp_cat, inp_tek)
                st.session_state.modal_unit = None
                st.rerun()
        with bc2:
            if st.button("✕ Batal", key="btn_batal"):
                st.session_state.modal_unit = None
                st.rerun()
        if is_active:
            with bc3:
                if st.button("🗑 Hapus Status", key="btn_hapus"):
                    delete_unit_status(mu["unit_id"])
                    st.session_state.modal_unit = None
                    st.rerun()

# ── Header tabel ───────────────────────────────────────────────────────────────
COL_W = [2.5, 1.6, 2, 1.8, 1.1, 1.8, 1.6, 1.1]

hcols = st.columns(COL_W)
for hc, label in zip(hcols, ["Fleet Group", "Unit ID", "Vehicle Code", "Local Time", "Hari", "Resource", "Status", "Aksi"]):
    hc.markdown(f"<div class='cell-hdr'>{label}</div>", unsafe_allow_html=True)

# Map status -> CSS badge class
BADGE = {
    "Update":                                  "badge-update",
    "No Update":                               "badge-noupdate",
    "Belum diinstal":                          "badge-uninstall",
    "Indikasi kabel power GPS lepas/kendor":   "badge-power",
    "Indikasi antena GPS lepas/kendor":        "badge-antenna",
    "Indikasi ACC bermasalah":                 "badge-acc",
    "Breakdown":                               "badge-breakdown",
    "Standby":                                 "badge-standby",
    "Sudah dismantle":                         "badge-dismantle",
    "Plan dismantle":                          "badge-plan",
    "Offhire":                                 "badge-offhire",
}

# Warna border bd-note per status koordinator
NOTE_BORDER = {
    "Breakdown":      "#fcd34d",
    "Standby":        "#93c5fd",
    "Sudah dismantle":"#cbd5e1",
    "Plan dismantle": "#fdba74",
    "Offhire":        "#c4b5fd",
}

# ── Render baris ───────────────────────────────────────────────────────────────
start   = (st.session_state.page_num - 1) * PER_PAGE
page_df = fdf.iloc[start : start + PER_PAGE]

for idx, row in page_df.iterrows():
    uid      = str(row["Unit ID"])
    fleet    = str(row.get("Fleet Group", "") or "")
    code     = str(row.get("Vehicle Code", "") or "")
    ttime    = row["Local Time"].strftime("%Y-%m-%d %H:%M") if pd.notna(row.get("Local Time")) else "-"
    res      = str(row.get("Resource", "") or "")
    status   = str(row["_display_status"])
    is_aktif = bool(row["_has_status"])
    badge    = BADGE.get(status, "badge-uninstall")

    # Kolom Hari
    days_val = row.get("_days_no_update")
    if days_val is None or (isinstance(days_val, float) and pd.isna(days_val)):
        days_html = "<span style='color:#9ca3af'>-</span>"
    elif days_val == 0:
        days_html = "<span style='background:#d1fae5;color:#065f46;padding:1px 6px;border-radius:4px;font-size:11px'>Hari ini</span>"
    elif days_val <= 3:
        days_html = f"<span style='background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:4px;font-size:11px'>{days_val}h</span>"
    elif days_val <= 7:
        days_html = f"<span style='background:#fee2e2;color:#991b1b;padding:1px 6px;border-radius:4px;font-size:11px'>{days_val}h</span>"
    else:
        days_html = f"<span style='background:#7f1d1d;color:#fecaca;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:600'>{days_val}h</span>"

    rcols = st.columns(COL_W)
    rcols[0].markdown(f"<div class='cell' title='{fleet}'>{fleet}</div>",           unsafe_allow_html=True)
    rcols[1].markdown(f"<div class='cell' style='font-family:monospace;font-size:11px'>{uid}</div>", unsafe_allow_html=True)
    rcols[2].markdown(f"<div class='cell' title='{code}'>{code}</div>",             unsafe_allow_html=True)
    rcols[3].markdown(f"<div class='cell'>{ttime}</div>",                            unsafe_allow_html=True)
    rcols[4].markdown(f"<div class='cell'>{days_html}</div>",                        unsafe_allow_html=True)
    rcols[5].markdown(f"<div class='cell' title='{res}'>{res}</div>",               unsafe_allow_html=True)
    rcols[6].markdown(f"<div class='cell'><span class='{badge}'>{status}</span></div>", unsafe_allow_html=True)

    with rcols[7]:
        btn_label = "✏ Edit" if is_aktif else "+ Status"
        btn_type  = "primary" if is_aktif else "secondary"
        if st.button(btn_label, key=f"st_{uid}_{idx}", type=btn_type, use_container_width=True):
            st.session_state.modal_unit = {"unit_id": uid, "fleet": fleet, "code": code}
            st.rerun()

    # Tampilkan catatan jika ada status aktif
    if is_aktif:
        us_info = us_df[us_df["unit_id"] == uid]
        if not us_info.empty:
            usi   = us_info.iloc[0]
            parts = []
            if usi["status"]:  parts.append(f"🏷 {usi['status']}")
            if usi["catatan"]: parts.append(f"📝 {usi['catatan']}")
            if usi["teknisi"]: parts.append(f"👤 {usi['teknisi']}")
            if len(parts) > 0:
                border = NOTE_BORDER.get(usi["status"], "#d1d5db")
                st.markdown(
                    f"<div class='bd-note' style='border-left-color:{border}'>"
                    f"{' &nbsp;·&nbsp; '.join(parts)}</div>",
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
        unsafe_allow_html=True,
    )
with pg3:
    if st.button("Next ▶", disabled=st.session_state.page_num >= total_pages, use_container_width=True):
        st.session_state.page_num += 1
        st.rerun()

# ── Daftar status aktif ────────────────────────────────────────────────────────
st.divider()
st.markdown("#### 📋 Daftar Status Unit Tidak Aktif")
us_now = load_unit_status()
if us_now.empty:
    st.info("Tidak ada unit dengan status aktif saat ini.")
else:
    # Kelompokkan per status
    for s in STATUS_OPTIONS:
        group = us_now[us_now["status"] == s]
        if group.empty:
            continue
        badge_cls = BADGE.get(s, "badge-uninstall")
        st.markdown(f"<span class='{badge_cls}'>{s}</span> &nbsp; {len(group)} unit", unsafe_allow_html=True)
        for _, urow in group.iterrows():
            with st.expander(f"{urow['vehicle_code']} · {urow['fleet_group']} · ID: {urow['unit_id']}"):
                st.write(f"**Status:** {urow['status']}")
                st.write(f"**Catatan:** {urow['catatan'] or '-'}")
                st.write(f"**Teknisi:** {urow['teknisi'] or '-'}")
                st.write(f"**Diperbarui:** {urow['updated_at']}")
                if st.button("🗑 Hapus status ini", key=f"del_{urow['unit_id']}"):
                    delete_unit_status(urow["unit_id"])
                    st.rerun()

st.divider()
st.caption(f"GPS Tracking Dashboard · Trisatria Persada Borneo · {datetime.now().year}")
