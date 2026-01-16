import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO

# --- 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="詳細階層分析ボード", layout="wide")

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

st.title("📈 階層別 在庫動態分析")

if not df_log_raw.empty:
    # --- データ前処理 ---
    df = df_log_raw.copy()
    df["日時"] = pd.to_datetime(df["日時"])
    df["年"] = df["日時"].dt.year
    # 月を文字化して変な目盛り（0.5月など）を解消
    df["月"] = df["日時"].dt.month.astype(str) + "月"
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ
    df_out = df[df["区分"].str.contains("出庫")].copy()

    # --- 5段階 階層絞り込み ---
    st.sidebar.header("🔍 絞り込み条件")
    
    year_list = sorted(df_out["年"].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 ① 年を選択", year_list)
    df_y = df_out[df_out["年"] == sel_year]

    month_options = ["すべて表示"] + sorted(df_y["月"].unique().tolist())
    sel_month = st.sidebar.selectbox("📆 ② 月を選択", month_options)
    df_m = df_y if sel_month == "すべて表示" else df_y[df_y["月"] == sel_month]

    item_list = ["すべて表示"] + sorted(df_m["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 ③ 商品名を選択", item_list)
    
    if sel_item != "すべて表示":
        df_i = df_m[df_m["商品名"] == sel_item]
        size_list = ["すべて表示"] + sorted(df_i["サイズ"].unique().tolist())
        sel_size = st.sidebar.selectbox("📏 ④ サイズを選択", size_list)
        
        if sel_size != "すべて表示":
            df_s = df_i[df_i["サイズ"] == sel_size]
            loc_list = ["すべて表示"] + sorted(df_s["地名"].unique().tolist())
            sel_loc = st.sidebar.selectbox("📍 ⑤ 地名を選択", loc_list)
        else:
            df_s = df_i
            sel_loc = "すべて表示"
    else:
        df_i = df_m
        sel_size = "すべて表示"
        sel_loc = "すべて表示"

    # フィルタリング適用
    df_final = df_m.copy()
    if sel_item != "すべて表示": df_final = df_final[df_final["商品名"] == sel_item]
    if sel_size != "すべて表示": df_final = df_final[df_final["サイズ"] == sel_size]
    if sel_loc != "すべて表示": df_final = df_final[df_final["地名"] == sel_loc]

 # --- メイン表示 ---
    # KPIカードを表示
    st.markdown("### 📌 絞り込み集計")
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric("合計出荷数", f"{int(df_final['数量'].sum()):,}")
    with kpi2:
        st.metric("出荷件数", f"{len(df_final)} 件")
    with kpi3:
        avg_v = round(df_final["数量"].mean(), 1) if not df_final.empty else 0
        st.metric("平均出荷量", f"{avg_v}")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📊 出荷傾向分析", "📈 時系列トレンド", "🔢 履歴明細"])

    with tab1:
        # 商品×サイズの需要集中度を可視化
        st.subheader("📦 商品・サイズ別の需要集中度")
        if not df_final.empty:
            summary_heat = df_final.groupby(["商品名", "サイズ"])["数量"].sum().reset_index()
            fig_heat = px.density_heatmap(
                summary_heat, x="サイズ", y="商品名", z="数量", 
                text_auto=True, color_continuous_scale="Viridis"
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        # カラムを分けて表示
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("📍 地名別出荷シェア")
            if not df_final.empty:
                fig_pie = px.pie(df_final, values='数量', names='地名', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            st.subheader("📅 曜日別の出荷傾向")
            if not df_final.empty:
                # 曜日順に並び替え
                df_final["曜日"] = df_final["日時"].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_jp = {'Monday': '月', 'Tuesday': '火', 'Wednesday': '水', 'Thursday': '木', 'Friday': '金', 'Saturday': '土', 'Sunday': '日'}
                
                summary_day = df_final.groupby("曜日")["数量"].sum().reindex(day_order).reset_index()
                summary_day["曜日"] = summary_day["曜日"].map(day_jp)
                
                fig_day = px.bar(summary_day, x="曜日", y="数量", text_auto=True, color_discrete_sequence=['#FF8C00'])
                st.plotly_chart(fig_day, use_container_width=True)

    with tab2:
        st.subheader("📈 日次出荷推移")
        if not df_final.empty:
            df_trend = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            fig_trend = px.line(df_trend, x="日時", y="数量", markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)

    with tab3:
        st.subheader("🔢 履歴明細")
        if not df_final.empty:
            view_df = df_final[["日時", "商品名", "サイズ", "地名", "数量", "担当者"]].copy()
            view_df["日時"] = view_df["日時"].dt.strftime('%Y-%m-%d %H:%M')
            # 地名順 > 数量順
            view_df = view_df.sort_values(by=["地名", "数量"], ascending=[True, False])
            st.dataframe(view_df, use_container_width=True, hide_index=True)
