import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO
from datetime import datetime, date

# --- 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="カレンダー分析ボード", layout="wide")

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

st.title("📅 カレンダー期間指定・詳細分析")

if not df_log_raw.empty:
    # データ前処理
    df = df_log_raw.copy()
    df["日時"] = pd.to_datetime(df["日時"])
    df["日付"] = df["日時"].dt.date # 日付のみの列を作成
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ
    df_out = df[df["区分"].str.contains("出庫")].copy()

    # --- 絞り込み条件（サイドバー） ---
    st.sidebar.header("🔍 絞り込み条件")
    
    # 1. カレンダーで期間を選択
    st.sidebar.subheader("📅 期間を指定")
    min_date = df_out["日付"].min()
    max_date = df_out["日付"].max()
    
    # 期間選択（開始日と終了日）
    date_range = st.sidebar.date_input(
        "分析期間を選択",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # 期間が正しく選択されているか確認
    if len(date_range) == 2:
        start_date, end_date = date_range
        df_period = df_out[(df_out["日付"] >= start_date) & (df_out["日付"] <= end_date)]
        
        st.sidebar.divider()

        # 2. 商品名
        item_list = ["すべて表示"] + sorted(df_period["商品名"].unique().tolist())
        sel_item = st.sidebar.selectbox("📦 商品名を選択", item_list)
        
        if sel_item != "すべて表示":
            df_i = df_period[df_period["商品名"] == sel_item]
            # 3. 地名
            loc_list = ["すべて表示"] + sorted(df_i["地名"].unique().tolist())
            sel_loc = st.sidebar.selectbox("📍 地名を選択", loc_list)
            
            if sel_loc != "すべて表示":
                df_l = df_i[df_i["地名"] == sel_loc]
                # 4. サイズ
                size_list = ["すべて表示"] + sorted(df_l["サイズ"].unique().tolist())
                sel_size = st.sidebar.selectbox("📏 サイズを選択", size_list)
            else:
                df_l = df_i
                sel_size = "すべて表示"
        else:
            df_i = df_period
            sel_loc = "すべて表示"
            sel_size = "すべて表示"

        # 最終フィルター適用
        df_final = df_period.copy()
        title_parts = [f"{start_date} ～ {end_date}"]
        
        if sel_item != "すべて表示":
            df_final = df_final[df_final["商品名"] == sel_item]
            title_parts.append(sel_item)
        if sel_loc != "すべて表示":
            df_final = df_final[df_final["地名"] == sel_loc]
            title_parts.append(sel_loc)
        if sel_size != "すべて表示":
            df_final = df_final[df_final["サイズ"] == sel_size]
            title_parts.append(sel_size)

        display_title = " / ".join(title_parts)

        # --- メイン表示 ---
        tab1, tab2 = st.tabs(["📊 出荷グラフ", "🔢 詳細データ一覧"])

        with tab1:
            st.subheader(f"出荷状況: {display_title}")
            if not df_final.empty:
                # グラフ用の項目名作成
                df_final["表示項目"] = df_final["商品名"] + " (" + df_final["サイズ"] + " / " + df_final["地名"] + ")"
                summary = df_final.groupby("表示項目")["数量"].sum().reset_index()
                
                fig = px.bar(summary, x="表示項目", y="数量", text_auto=True,
                             color="数量", color_continuous_scale="Reds")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("該当するデータがありません。期間や条件を変更してください。")

        with tab2:
            st.subheader("分析対象の履歴明細")
            if not df_final.empty:
                st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量", "担当者"]].sort_values("日時", ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("データがありません。")
    else:
        st.info("カレンダーで開始日と終了日の両方を選択してください。")

else:
    st.warning("履歴データが読み込めません。")
