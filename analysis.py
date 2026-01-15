import streamlit as st
import pandas as pd
import plotly.express as px # グラフ用
import requests
import base64
from io import StringIO

# --- 1. 設定 (管理システムと同じものを使用) ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="在庫分析ダッシュボード", layout="wide")

# --- 2. データ読み込み関数 ---
def get_github_data(file_path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        df = pd.read_csv(StringIO(csv_text))
        return df.fillna("")
    return pd.DataFrame()

# データの取得
df_log_raw = get_github_data(FILE_PATH_LOG)

st.title("📈 在庫変動 分析ボード")

if not df_log_raw.empty:
    # --- 3. データの前処理 ---
    df_log = df_log_raw.copy()
    # 日時を日付型に変換
    df_log["日時"] = pd.to_datetime(df_log["日時"])
    df_log["年月"] = df_log["日時"].dt.strftime("%Y-%m")
    # 数量を数値型に変換
    df_log["数量"] = pd.to_numeric(df_log["数量"], errors='coerce').fillna(0)

    # --- 4. フィルター設定 ---
    st.sidebar.header("🔍 絞り込み")
    selected_year = st.sidebar.selectbox("年を選択", sorted(df_log["日時"].dt.year.unique(), reverse=True))
    
    # 選択した年のデータに絞り込み
    df_year = df_log[df_log["日時"].dt.year == selected_year]
    
    # 出庫データのみ抽出（出庫・予約出庫・出庫(予約実行)）
    df_out = df_year[df_year["区分"].str.contains("出庫")]

    # --- 5. メイン表示：月別の合計出庫数 ---
    st.subheader(f"📅 {selected_year}年 月別 総出庫数")
    
    # 月ごとに集計
    monthly_summary = df_out.groupby("年月")["数量"].sum().reset_index()
    
    # グラフ作成 (Plotly)
    fig = px.bar(monthly_summary, x="年月", y="数量", 
                 labels={"数量": "出庫合計数", "年月": "月"},
                 text_auto=True,
                 color_discrete_sequence=["#3366CC"])
    st.plotly_chart(fig, use_container_width=True)

    # --- 6. 商品別の詳細分析 ---
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 商品別 出庫ランキング")
        item_summary = df_out.groupby("商品名")["数量"].sum().sort_values(ascending=True).reset_index()
        fig_item = px.bar(item_summary, x="数量", y="商品名", orientation='h',
                          text_auto=True, color="数量", color_continuous_scale="Blues")
        st.plotly_chart(fig_item, use_container_width=True)

    with col2:
        st.subheader("👤 担当者別 作業割合")
        user_summary = df_year.groupby("担当者").size().reset_index(name="作業件数")
        fig_user = px.pie(user_summary, values="作業件数", names="担当者", hole=0.4)
        st.plotly_chart(fig_user, use_container_width=True)

else:
    st.warning("履歴データが見つかりません。")
