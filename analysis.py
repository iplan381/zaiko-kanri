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

st.set_page_config(page_title="在庫分析ダッシュボード", layout="wide")

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

st.title("📈 在庫変動 分析ボード")

if not df_log_raw.empty:
    # データ前処理
    df_log = df_log_raw.copy()
    df_log["日時"] = pd.to_datetime(df_log["日時"])
    df_log["年"] = df_log["日時"].dt.year
    df_log["月"] = df_log["日時"].dt.month
    df_log["年月"] = df_log["日時"].dt.strftime("%Y-%m")
    df_log["数量"] = pd.to_numeric(df_log["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ（予約含む）
    df_out = df_log[df_log["区分"].str.contains("出庫")].copy()

    # --- 1. 月ごとの出荷数（何がどれだけ出たか内訳付き） ---
    st.subheader("📅 月別・商品別の出荷トレンド")
    st.caption("どの月に、どの商品がどれくらい出たかを積み上げグラフで表示します。")
    
    # 月と商品名で集計
    monthly_item_sum = df_out.groupby(["年月", "商品名"])["数量"].sum().reset_index()
    
    fig_monthly = px.bar(monthly_item_sum, x="年月", y="数量", color="商品名",
                         text_auto=True, title="月別総出荷数（商品内訳）",
                         barmode="stack") # 積み上げ形式
    st.plotly_chart(fig_monthly, use_container_width=True)

    # --- 2. 別の年月との比較 ---
    st.divider()
    st.subheader("⚖️ 年月比較分析")
    
    col1, col2 = st.columns(2)
    with col1:
        target_a = st.selectbox("比較対象 A", df_out["年月"].unique(), index=0)
    with col2:
        # データが1件以上ある場合、2番目を選択、なければ1番目
        default_b = 1 if len(df_out["年月"].unique()) > 1 else 0
        target_b = st.selectbox("比較対象 B", df_out["年月"].unique(), index=default_b)

    # 比較用データの抽出
    df_a = df_out[df_out["年月"] == target_a].groupby("商品名")["数量"].sum().reset_index()
    df_b = df_out[df_out["年月"] == target_b].groupby("商品名")["数量"].sum().reset_index()
    
    # 2つのデータを結合して比較
    df_compare = pd.merge(df_a, df_b, on="商品名", how="outer", suffixes=(f'_{target_a}', f'_{target_b}')).fillna(0)
    
    # 比較棒グラフ
    fig_comp = px.bar(df_compare, x="商品名", y=[f"数量_{target_a}", f"数量_{target_b}"],
                      barmode="group", title=f"{target_a} vs {target_b} の出荷比較",
                      labels={"value": "出荷数", "variable": "年月"})
    st.plotly_chart(fig_comp, use_container_width=True)

else:
    st.warning("履歴データがまだ蓄積されていないか、読み込めません。")
