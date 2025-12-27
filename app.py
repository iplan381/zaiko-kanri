import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import requests
from io import StringIO

# --- 1. 設定 ---
REPO_NAME = "iplan381/zaiko-kanri" 
FILE_PATH_STOCK = "inventory_main.csv"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

SIZES_MASTER = ["大", "中", "小", "なし"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]
USERS = ["佐藤", "手塚", "檀原"]

st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- 2. GitHub関数 ---
def get_github_data(file_path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        df = pd.read_csv(StringIO(csv_text))
        return df.fillna(""), content["sha"]
    return pd.DataFrame(), None

def update_github_data(file_path, df, sha, message):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    data = {
        "message": message,
        "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"),
        "sha": sha
    }
    res = requests.put(url, headers=headers, json=data)
    return res.status_code == 200

def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

# データ読み込み
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)

st.title("📦 在庫管理")

# --- 3. サイドバー：入出庫・登録 ---
with st.sidebar:
    # --- 入出庫フォーム ---
    st.header("🔄 入出庫入力")
    if not df_stock.empty:
        # 商品を特定するための選択
        target_item = st.selectbox("対象商品", df_stock["商品名"].unique())
        # 同じ商品名でもサイズや地名が違う場合を考慮
        sub_df = df_stock[df_stock["商品名"] == target_item]
        target_size = st.selectbox("サイズ ", sub_df["サイズ"].unique())
        target_loc = st.selectbox("地名 ", sub_df["地名"].unique())
        
        move_type = st.radio("区分", ["入庫", "出庫"], horizontal=True)
        move_qty = st.number_input("数量", min_value=1, value=1)
        user_name = st.selectbox("担当者", USERS)

        if st.button("更新実行"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            # 在庫数計算
            idx = df_stock[(df_stock["商品名"] == target_item) & 
                          (df_stock["サイズ"] == target_size) & 
                          (df_stock["地名"] == target_loc)].index[0]
            
            old_qty = df_stock.at[idx, "在庫数"]
            new_qty = old_qty + move_qty if move_type == "入庫" else old_qty - move_qty
            
            df_stock.at[idx, "在庫数"] = new_qty
            df_stock.at[idx, "最終更新日"] = now
            
            # 履歴作成
            new_log = pd.DataFrame([{
                "日時": now, "商品名": target_item, "サイズ": target_size, 
                "地名": target_loc, "区分": move_type, "数量": move_qty, "担当者": user_name
            }])
            updated_log = pd.concat([df_log, new_log], ignore_index=True)
            
            if update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, f"Stock {move_type}") and \
               update_github_data(FILE_PATH_LOG, updated_log, sha_log, "Add Log"):
                st.success("更新完了！")
                st.rerun()

    st.divider()
    # --- 新規登録フォーム ---
    st.header("✨ 新商品登録")
    n_item = st.text_input("商品名")
    n_size = st.selectbox("サイズ", SIZES_MASTER)
    n_loc = st.text_input("地名")
    n_vendor = st.selectbox("取引先", VENDORS_MASTER)
    n_stock = st.number_input("初期在庫", min_value=0, value=0)

    if st.button("新規登録"):
        if n_item and n_loc:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_row = pd.DataFrame([{"最終更新日": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "在庫数": n_stock, "アラート基準": 5, "取引先": n_vendor}])
            new_log = pd.DataFrame([{"日時": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "区分": "新規登録", "数量": n_stock, "担当者": "システム"}])
            
            if update_github_data(FILE_PATH_STOCK, pd.concat([df_stock, new_row]), sha_stock, "Add Item") and \
               update_github_data(FILE_PATH_LOG, pd.concat([df_log, new_log]), sha_log, "Add Log"):
                st.success("登録完了！")
                st.rerun()

# --- 4. メイン表示 ---
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("絞込:商品名", get_opts(df_stock["商品名"]))
with c2: s_size = st.selectbox("絞込:サイズ", get_opts(df_stock["サイズ"]))
with c3: s_loc = st.selectbox("絞込:地名", get_opts(df_stock["地名"]))
with c4: s_vendor = st.selectbox("絞込:取引先", get_opts(df_stock["取引先"]))

df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc != "すべて": df_disp = df_disp[df_disp["地名"] == s_loc]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]
st.dataframe(df_disp, use_container_width=True, hide_index=True)

st.divider()
st.subheader("📜 入出庫履歴")
if not df_log.empty:
    st.dataframe(df_log.sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
