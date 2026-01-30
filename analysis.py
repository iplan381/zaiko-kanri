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

st.title("📈 在庫動態分析 (期間比較モード)")

if not df_log_raw.empty:
    # --- データ前処理 ---
    df = df_log_raw.copy()
    df["日時"] = pd.to_datetime(df["日時"], errors='coerce', format='mixed')
    df = df.dropna(subset=["日時"])
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    df_out_all = df[df["区分"].str.contains("出庫")].copy()
    df_out_all["項目詳細"] = df_out_all["商品名"].astype(str) + " | " + df_out_all["サイズ"].astype(str) + " | " + df_out_all["地名"].astype(str)

    # --- 🔍 絞り込み条件（サイドバー） ---
    with st.sidebar:
        st.markdown("### 🔗 クイック移動")
        c1, c2 = st.columns(2)
        c1.link_button("📦 在庫管理", "https://zaiko-kanri.streamlit.app/")
        c2.link_button("🚚 発注管理", "https://zaiko-kanri-qzelakcnxralslk3ac27ex.streamlit.app/")
        st.divider()
    
        st.header("🔍 期間設定")
        
        # 日付の安全な取得
        data_min = df_out_all["日時"].min().date()
        data_max = df_out_all["日時"].max().date()
        
        # 【期間A】メイン期間
        st.subheader("① 分析期間 (メイン)")
        val_a_start = max(data_min, data_max - dt.timedelta(days=30))
        range_a = st.date_input("分析期間を選択", [val_a_start, data_max], min_value=data_min, max_value=data_max, key="ra")

        # 【期間B】比較期間
        st.subheader("② 比較期間 (ターゲット)")
        val_b_start = max(data_min, data_max - dt.timedelta(days=61))
        val_b_end = max(data_min, data_max - dt.timedelta(days=31))
        range_b = st.date_input("比較期間を選択", [val_b_start, val_b_end], min_value=data_min, max_value=data_max, key="rb")

        st.divider()
        st.header("📦 絞り込み条件")
        all_items = ["すべて表示"] + sorted(df_out_all["商品名"].unique().tolist())
        all_sizes = ["すべて表示"] + sorted(df_out_all["サイズ"].unique().tolist())
        all_locs = ["すべて表示"] + sorted(df_out_all["地名"].unique().tolist())

        sel_item = st.selectbox("商品名", all_items)
        sel_size = st.selectbox("サイズ", all_sizes)
        sel_loc = st.selectbox("地名", all_locs)
        show_compare = st.checkbox("🔄 期間比較を表示する", value=True)

    # --- 期間確定と抽出 ---
    if isinstance(range_a, (list, tuple)) and len(range_a) == 2:
        df_a = df_out_all[(df_out_all["日時"].dt.date >= range_a[0]) & (df_out_all["日時"].dt.date <= range_a[1])]
    else:
        st.info("左側で「分析期間」を2箇所クリックしてください。")
        st.stop()

    if isinstance(range_b, (list, tuple)) and len(range_b) == 2:
        df_b = df_out_all[(df_out_all["日時"].dt.date >= range_b[0]) & (df_out_all["日時"].dt.date <= range_b[1])]
    else:
        df_b = pd.DataFrame()

    # --- 共通フィルタ適用 ---
    if sel_item != "すべて表示":
        df_a = df_a[df_a["商品名"] == sel_item]
        df_b = df_b[df_b["商品名"] == sel_item] if not df_b.empty else df_b
    if sel_size != "すべて表示":
        df_a = df_a[df_a["サイズ"] == sel_size]
        df_b = df_b[df_b["サイズ"] == sel_size] if not df_b.empty else df_b
    if sel_loc != "すべて表示":
        df_a = df_a[df_a["地名"] == sel_loc]
        df_b = df_b[df_b["地名"] == sel_loc] if not df_b.empty else df_b

    st.divider()

    # --- 📊 表示エリア ---
    if not df_a.empty:
        qty_a = df_a["数量"].sum()
        qty_b = df_b["数量"].sum() if not df_b.empty else 0
        
        if show_compare:
            k1, k2, k3, k4 = st.columns(4)
            diff_pct = f"{round(((qty_a - qty_b) / qty_b) * 100, 1)}%" if qty_b > 0 else "---"
            k1.metric("分析期間 合計", f"{int(qty_a):,}")
            k2.metric("比較期間 合績", f"{int(qty_b):,}")
            k3.metric("増減率", diff_pct, delta=f"{int(qty_a - qty_b):,}")
            k4.metric("メイン項目数", f"{df_a['項目詳細'].nunique()}")
        else:
            k1, k2, k3 = st.columns(3)
            k1.metric("分析期間 合計", f"{int(qty_a):,}")
            k2.metric("平均出荷量", f"{round(df_a['数量'].mean(), 1)}")
            k3.metric("メイン項目数", f"{df_a['項目詳細'].nunique()}")

        tab1, tab2, tab4, tab5 = st.tabs(["📊 傾向", "📈 トレンド推移", "⚠️ 不動・安全在庫", "🔢 履歴明細"])

        with tab1:
            st.subheader("📦 分析期間のランキング (上位20)")
            summary = df_a.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(20).reset_index()
            st.plotly_chart(px.bar(summary, y="項目詳細", x="数量", orientation='h', text_auto=True), use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📍 地名別 (分析期間)")
                st.plotly_chart(px.pie(df_a, values='数量', names='地名', hole=0.4), use_container_width=True)
            with c2:
                st.subheader("📅 曜日別傾向 (クリックで内訳)")
                df_a["曜日"] = df_a["日時"].dt.day_name()
                day_jp = {'Monday':'月','Tuesday':'火','Wednesday':'水','Thursday':'木','Friday':'金','Saturday':'土','Sunday':'日'}
                summary_day = df_a.groupby("曜日")["数量"].sum().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).reset_index()
                summary_day["表示曜日"] = summary_day["曜日"].map(day_jp)
                fig_day = px.bar(summary_day, x="表示曜日", y="数量", text_auto=True)
                selected = st.plotly_chart(fig_day, use_container_width=True, on_select="rerun")
                
                if selected and "selection" in selected and selected["selection"]["points"]:
                    sel_d = selected["selection"]["points"][0]["x"]
                    st.info(f"📅 {sel_d}曜日の詳細")
                    st.dataframe(df_a[df_a["曜日"].map(day_jp) == sel_d].groupby("項目詳細")["数量"].sum().sort_values(ascending=False), use_container_width=True)

        with tab2:
            st.subheader("📈 トレンド推移")
            trend_a = df_a.groupby(df_a["日時"].dt.date)["数量"].sum().reset_index()
            st.plotly_chart(px.line(trend_a, x="日時", y="数量", markers=True), use_container_width=True)

        with tab4:
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.subheader("⚠️ メイン期間の不動在庫")
                dead = df_a.groupby("項目詳細")["日時"].max().reset_index().rename(columns={"日時": "最終"})
                dead["経過日数"] = (pd.Timestamp.now() - dead["最終"]).dt.days
                st.dataframe(dead.sort_values("経過日数", ascending=False), use_container_width=True, hide_index=True)
            with col_w2:
                st.subheader("💡 推奨在庫 (メイン期間ベース)")
                safety = df_a.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
                safety["推奨"] = (safety["mean"] + 2 * safety["std"]).round(0)
                st.dataframe(safety.sort_values("推奨", ascending=False), use_
