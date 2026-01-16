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
    st.divider()

    # 1. 基本単位（ユニークキー）の作成
    # 後の集計で使いやすいように「商品名・サイズ・地名」を結合した列を作ります
    df_final["項目詳細"] = df_final["商品名"] + " | " + df_final["サイズ"] + " | " + df_final["地名"]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 傾向・シェア", "📈 トレンド・前年比較", "🏆 ABC分析", "⚠️ 不動在庫・安全在庫", "🔢 履歴明細"
    ])

    with tab1:
        st.subheader("📦 詳細項目別の出荷ボリューム")
        if not df_final.empty:
            # 商品名・サイズ・地名をすべて含めて集計
            summary_full = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).reset_index()
            fig_full = px.bar(summary_full, y="項目詳細", x="数量", orientation='h', 
                             text_auto=True, color="数量", title="詳細別出荷ランキング")
            st.plotly_chart(fig_full, use_container_width=True)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("📍 地名別出荷シェア")
            fig_pie = px.pie(df_final, values='数量', names='地名', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_g2:
            st.subheader("📅 曜日別の出荷傾向")
            df_final["曜日"] = df_final["日時"].dt.day_name()
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_jp = {'Monday': '月', 'Tuesday': '火', 'Wednesday': '水', 'Thursday': '木', 'Friday': '金', 'Saturday': '土', 'Sunday': '日'}
            summary_day = df_final.groupby("曜日")["数量"].sum().reindex(day_order).reset_index()
            summary_day["曜日"] = summary_day["曜日"].map(day_jp)
            fig_day = px.bar(summary_day, x="曜日", y="数量", text_auto=True, color_discrete_sequence=['#FF8C00'])
            st.plotly_chart(fig_day, use_container_width=True)

    with tab3:
        st.subheader("🏆 ABC分析（詳細項目別）")
        # 商品×サイズ×地名 でランク付け
        abc_df = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
        abc_df["累計構成比"] = (abc_df["数量"].cumsum() / abc_df["数量"].sum()) * 100
        abc_df["ランク"] = abc_df["累計構成比"].apply(lambda x: "A (最重要)" if x <= 80 else ("B (重要)" if x <= 95 else "C (一般)"))
        
        fig_abc = px.bar(abc_df, x="項目詳細", y="数量", color="ランク", title="詳細項目パレート図")
        st.plotly_chart(fig_abc, use_container_width=True)

    with tab4:
        st.subheader("💡 詳細別・安全在庫の目安")
        # 詳細項目ごとに標準偏差を計算
        safety_df = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
        safety_df["推奨在庫数"] = (safety_df["mean"] + 2 * safety_df["std"]).round(0)
        st.dataframe(safety_df[["項目詳細", "推奨在庫数"]].sort_values("推奨在庫数", ascending=False), 
                     use_container_width=True, hide_index=True)
