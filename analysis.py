import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO
import datetime as dt

# --- 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="出庫分析", layout="wide")

@st.cache_data(ttl=60)
def get_github_data(file_path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        return pd.read_csv(StringIO(csv_text)).fillna("")
    return pd.DataFrame()

df_log_raw = get_github_data(FILE_PATH_LOG)

st.title("📈 在庫動態分析")

if not df_log_raw.empty:
    # --- データ前処理 ---
    df = df_log_raw.copy()
    # 💡 混合フォーマット対応でエラーを回避
    df["日時"] = pd.to_datetime(df["日時"], errors='coerce', format='mixed')
    df = df.dropna(subset=["日時"])
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    df_out_all = df[df["区分"].str.contains("出庫")].copy()
    df_out_all["項目詳細"] = df_out_all["商品名"].astype(str) + " | " + df_out_all["サイズ"].astype(str) + " | " + df_out_all["地名"].astype(str)

    # --- 🔍 絞り込み条件（サイドバー） ---
    with st.sidebar:
        # ✅ クイック移動（絶対死守！）
        st.markdown("### 🔗 クイック移動")
        c1, c2 = st.columns(2)
        c1.link_button("📦 在庫管理", "https://zaiko-kanri.streamlit.app/")
        c2.link_button("🚚 発注管理", "https://zaiko-kanri-qzelakcnxralslk3ac27ex.streamlit.app/")
        st.divider()

        # ✅ カレンダー選択
        st.markdown("### 📅 分析期間を選択")
        min_d = df_out_all["日時"].min().date()
        max_d = df_out_all["日時"].max().date()
        start_default = max_d - dt.timedelta(days=30)
        date_range = st.date_input("範囲指定", [max(min_d, start_default), max_d], min_value=min_d, max_value=max_d)
        
        st.divider()
        st.header("🔍 絞り込み条件")
        
        all_item_list = ["すべて表示"] + sorted(df_out_all["商品名"].unique().tolist())
        all_size_list = ["すべて表示"] + sorted(df_out_all["サイズ"].unique().tolist())
        all_loc_list = ["すべて表示"] + sorted(df_out_all["地名"].unique().tolist())

        sel_item = st.selectbox("📦 商品名", all_item_list)
        sel_size = st.selectbox("📏 サイズ", all_size_list)
        sel_loc = st.selectbox("📍 地名", all_loc_list)
        show_compare = st.checkbox("🔄 昨年対比を表示する", value=True)

    # 期間確定ロジック
    if isinstance(date_range, list) and len(date_range) == 2:
        start_date, end_date = date_range
        df_final = df_out_all[(df_out_all["日時"].dt.date >= start_date) & (df_out_all["日時"].dt.date <= end_date)]
        last_start, last_end = start_date - dt.timedelta(days=365), end_date - dt.timedelta(days=365)
        df_last = df_out_all[(df_out_all["日時"].dt.date >= last_start) & (df_out_all["日時"].dt.date <= last_end)]
    else:
        st.info("カレンダーで開始日と終了日を選択してください。")
        st.stop()

    # フィルタ適用
    if sel_item != "すべて表示":
        df_final = df_final[df_final["商品名"] == sel_item]
        df_last = df_last[df_last["商品名"] == sel_item]
    if sel_size != "すべて表示":
        df_final = df_final[df_final["サイズ"] == sel_size]
        df_last = df_last[df_last["サイズ"] == sel_size]
    if sel_loc != "すべて表示":
        df_final = df_final[df_final["地名"] == sel_loc]
        df_last = df_last[df_last["地名"] == sel_loc]

    # --- 表示エリア ---
    if not df_final.empty:
        qty_this, qty_last = df_final["数量"].sum(), df_last["数量"].sum()
        k1, k2, k3 = st.columns(3)
        with k1: st.metric("期間内 合計出荷", f"{int(qty_this):,}")
        if show_compare:
            diff_pct = f"{round(((qty_this - qty_last) / qty_last) * 100, 1)}%" if qty_last > 0 else "---"
            with k2: st.metric("前年同期実績", f"{int(qty_last):,}", delta=diff_pct)
        else:
            with k2: st.metric("稼働詳細項目数", f"{df_final['項目詳細'].nunique()}")
        with k3: st.metric("平均出荷量", f"{round(df_final['数量'].mean(), 1)}")

        tab1, tab2, tab3 = st.tabs(["📊 傾向", "📈 トレンド", "🔢 履歴明細"])
        with tab1:
            summary_rank = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(20).reset_index()
            st.plotly_chart(px.bar(summary_rank, y="項目詳細", x="数量", orientation='h', text_auto=True), use_container_width=True)
        with tab2:
            df_trend = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            st.plotly_chart(px.line(df_trend, x="日時", y="数量", markers=True), use_container_width=True)
        with tab3:
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("該当するデータがありません。")
else:
    st.error("データの読み込みに失敗しました。")
