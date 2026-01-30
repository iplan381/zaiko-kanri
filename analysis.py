import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO
import datetime as dt # datetimeをdtとしてインポート

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
    # 💡 エラー対策：混合フォーマットに対応
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
    
        st.sidebar.header("🔍 絞り込み条件")
        
        # 💡 カレンダーによる期間選択（年・月・週の選択から差し替え）
        min_d = df_out_all["日時"].min().date()
        max_d = df_out_all["日時"].max().date()
        # デフォルトは直近30日間
        start_default = max(min_d, max_d - dt.timedelta(days=30))
        date_range = st.date_input("📅 期間を選択", [start_default, max_d], min_value=min_d, max_value=max_d)

        # 商品名・サイズ・地名の選択肢
        all_item_list = ["すべて表示"] + sorted(df_out_all["商品名"].unique().tolist())
        all_size_list = ["すべて表示"] + sorted(df_out_all["サイズ"].unique().tolist())
        all_loc_list = ["すべて表示"] + sorted(df_out_all["地名"].unique().tolist())

        sel_item = st.sidebar.selectbox("📦 商品名を選択", all_item_list)
        sel_size = st.sidebar.selectbox("📏 サイズを選択", all_size_list)
        sel_loc = st.sidebar.selectbox("📍 地名を選択", all_loc_list)
        show_compare = st.sidebar.checkbox("🔄 昨年対比を表示する", value=True)

    # --- 最終的なフィルタリング実行 ---
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
        # 期間フィルタ
        df_final = df_out_all[(df_out_all["日時"].dt.date >= start_date) & (df_out_all["日時"].dt.date <= end_date)]
        # 昨年対比用フィルタ
        ls, le = start_date - dt.timedelta(days=365), end_date - dt.timedelta(days=365)
        df_last = df_out_all[(df_out_all["日時"].dt.date >= ls) & (df_out_all["日時"].dt.date <= le)]
    else:
        st.info("カレンダーで開始日と終了日を選択してください。")
        st.stop()

    # 商品・サイズ・地名フィルタ
    if sel_item != "すべて表示":
        df_final = df_final[df_final["商品名"] == sel_item]
        df_last = df_last[df_last["商品名"] == sel_item]
    if sel_size != "すべて表示":
        df_final = df_final[df_final["サイズ"] == sel_size]
        df_last = df_last[df_last["サイズ"] == sel_size]
    if sel_loc != "すべて表示":
        df_final = df_final[df_final["地名"] == sel_loc]
        df_last = df_last[df_last["地名"] == sel_loc]

    st.divider()

    # --- 表示ロジック（提示されたコードのまま） ---
    if not df_final.empty:
        qty_this = df_final["数量"].sum()
        qty_last = df_last["数量"].sum()
        
        if show_compare:
            k1, k2, k3, k4 = st.columns(4)
            diff_pct = f"{round(((qty_this - qty_last) / qty_last) * 100, 1)}%" if qty_last > 0 else "---"
            with k1: st.metric("期間内 合計出荷", f"{int(qty_this):,}")
            with k2: st.metric("前年同期実績", f"{int(qty_last):,}")
            with k3: st.metric("前年同期比", diff_pct)
            with k4: st.metric("稼働詳細項目数", f"{df_final['項目詳細'].nunique()}")
        else:
            k1, k2, k3 = st.columns(3)
            with k1: st.metric("期間内 合計出荷", f"{int(qty_this):,}")
            with k2: st.metric("稼働詳細項目数", f"{df_final['項目詳細'].nunique()}")
            with k3: st.metric("平均出荷量", f"{round(df_final['数量'].mean(), 1)}")

        tab1, tab2, tab4, tab5 = st.tabs(["📊 傾向", "📈 トレンド推移", "⚠️ 不動・安全在庫", "🔢 履歴明細"])

        with tab1:
            st.subheader("📦 詳細項目別ランキング（上位20件）")
            summary_rank = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(20).reset_index()
            fig_rank = px.bar(summary_rank, y="項目詳細", x="数量", orientation='h', text_auto=True, color="数量", color_continuous_scale=px.colors.sequential.Viridis)
            fig_rank.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_rank, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📍 地名別")
                st.plotly_chart(px.pie(df_final, values='数量', names='地名', hole=0.4), use_container_width=True)
            with c2:
                st.subheader("📅 曜日別傾向 (クリックで内訳)")
                df_final["曜日"] = df_final["日時"].dt.day_name()
                day_jp = {'Monday':'月','Tuesday':'火','Wednesday':'水','Thursday':'木','Friday':'金','Saturday':'土','Sunday':'日'}
                summary_day = df_final.groupby("曜日")["数量"].sum().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).reset_index()
                summary_day["表示曜日"] = summary_day["曜日"].map(day_jp)
                fig_day = px.bar(summary_day, x="表示曜日", y="数量", text_auto=True, color="数量", color_continuous_scale=px.colors.sequential.Blues, custom_data=["表示曜日"])
                fig_day.update_layout(coloraxis_showscale=False, clickmode='event+select')
                selected_points = st.plotly_chart(fig_day, use_container_width=True, on_select="rerun")
                
                if selected_points and "selection" in selected_points and selected_points["selection"]["points"]:
                    selected_day = selected_points["selection"]["points"][0]["x"]
                    st.info(f"📅 {selected_day}曜日の出荷内訳")
                    df_day_detail = df_final[df_final["曜日"].map(day_jp) == selected_day]
                    day_summary = df_day_detail.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
                    st.dataframe(day_summary, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("📈 トレンド推移")
            df_trend = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            st.plotly_chart(px.line(df_trend, x="日時", y="数量", markers=True), use_container_width=True)

        with tab4:
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.subheader("⚠️ 不動在庫")
                df_db = df_out_all.copy()
                if sel_item != "すべて表示": df_db = df_db[df_db["商品名"] == sel_item]
                if sel_size != "すべて表示": df_db = df_db[df_db["サイズ"] == sel_size]
                if sel_loc != "すべて表示": df_db = df_db[df_db["地名"] == sel_loc]
                
                now = pd.Timestamp.now()
                dead = df_db.groupby("項目詳細")["日時"].max().reset_index()
                dead = dead.rename(columns={"日時": "最終出荷日"})
                dead["経過日数"] = (now - dead["最終出荷日"]).dt.days
                dead.loc[dead["経過日数"] < 0, "経過日数"] = 0
                dead = dead.sort_values("経過日数", ascending=False)
                dead["最終出荷日"] = dead["最終出荷日"].dt.strftime('%Y-%m-%d')
                st.dataframe(dead, use_container_width=True, hide_index=True)
            with col_w2:
                st.subheader("💡 推奨・安全在庫")
                safety_df = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
                safety_df["推奨在庫"] = (safety_df["mean"] + 2 * safety_df["std"]).round(0)
                st.dataframe(safety_df[["項目詳細", "推奨在庫"]].sort_values("推奨在庫", ascending=False), use_container_width=True, hide_index=True)

        with tab5:
            st.subheader("🔢 履歴明細")
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("選択された条件に該当するデータがありません。")
else:
    st.error("データの読み込みに失敗しました。")
