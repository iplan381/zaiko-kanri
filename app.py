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

st.title("📦 在庫管理プロ")

# --- 3. メイン：在庫一覧 ---
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("検索:商品名", get_opts(df_stock["商品名"]))
with c2: s_size = st.selectbox("検索:サイズ", get_opts(df_stock["サイズ"]))
with c3: s_loc = st.selectbox("検索:地名", get_opts(df_stock["地名"]))
with c4: s_vendor = st.selectbox("検索:取引先", get_opts(df_stock["取引先"]))

df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc != "すべて": df_disp = df_disp[df_disp["地名"] == s_loc]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

# 💡 選択機能
event = st.dataframe(df_disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

# --- 4. 操作パネル ---
st.divider()
selected_rows = event.selection.rows
selected_data = df_disp.iloc[selected_rows[0]] if selected_rows else None

t1, t2, t3 = st.tabs(["🔄 在庫・アラート更新", "✨ 新規商品登録", "🗑️ データ削除"])

with t1:
    if selected_data is not None:
        st.info(f"選択中: {selected_data['商品名']} ({selected_data['サイズ']} / {selected_data['地名']})")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            move_type = st.radio("区分", ["入庫", "出庫", "設定変更のみ"], horizontal=True)
        with col2:
            move_qty = st.number_input("数量変更", min_value=0, value=0) if move_type != "設定変更のみ" else 0
        with col3:
            new_alert_val = st.number_input("アラート基準の変更", min_value=0, value=int(selected_data['アラート基準']))
        with col4:
            user_name = st.selectbox("担当者", USERS)
            if st.button("この内容で更新", type="primary"):
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                idx = df_stock[(df_stock["商品名"] == selected_data["商品名"]) & (df_stock["サイズ"] == selected_data["サイズ"]) & (df_stock["地名"] == selected_data["地名"])].index[0]
                
                # 在庫計算
                if move_type == "入庫": df_stock.at[idx, "在庫数"] += move_qty
                elif move_type == "出庫": df_stock.at[idx, "在庫数"] -= move_qty
                
                df_stock.at[idx, "アラート基準"] = new_alert_val
                df_stock.at[idx, "最終更新日"] = now
                
                log_msg = f"{move_type}(アラート:{new_alert_val})"
                new_log = pd.DataFrame([{"日時": now, "商品名": selected_data["商品名"], "サイズ": selected_data["サイズ"], "地名": selected_data["地名"], "区分": log_msg, "数量": move_qty, "担当者": user_name}])
                
                if update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Update Stock/Alert") and \
                   update_github_data(FILE_PATH_LOG, pd.concat([df_log, new_log]), sha_log, "Add Log"):
                    st.success("更新しました！")
                    st.rerun()
    else:
        st.warning("一覧から行を選択してください。")

with t2:
    st.write("新規商品の追加")
    r1, r2, r3, r4 = st.columns(4)
    with r1: n_item = st.text_input("商品名 ")
    with r2: n_size = st.selectbox("サイズ ", SIZES_MASTER)
    with r3: n_loc = st.text_input("地名 ")
    with r4: n_vendor = st.selectbox("取引先 ", VENDORS_MASTER)
    
    if st.button("新規登録実行"):
        # 💡 重複チェック
        is_duplicate = not df_stock[(df_stock["商品名"] == n_item) & (df_stock["サイズ"] == n_size) & (df_stock["地名"] == n_loc)].empty
        if is_duplicate:
            st.error(f"❌ 重複エラー：『{n_item} ({n_size}) - {n_loc}』は既に登録されています。")
        elif n_item and n_loc:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_row = pd.DataFrame([{"最終更新日": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "在庫数": 0, "アラート基準": 5, "取引先": n_vendor}])
            if update_github_data(FILE_PATH_STOCK, pd.concat([df_stock, new_row]), sha_stock, "Add Item"):
                st.success("新しく登録しました！")
                st.rerun()

with t3:
    st.subheader("データの削除")
    if selected_data is not None:
        st.error(f"⚠️ 選択中の【{selected_data['商品名']}】を在庫一覧から完全に削除しますか？")
        if st.button("在庫から削除する"):
            idx = df_stock[(df_stock["商品名"] == selected_data["商品名"]) & (df_stock["サイズ"] == selected_data["サイズ"]) & (df_stock["地名"] == selected_data["地名"])].index[0]
            df_stock = df_stock.drop(idx)
            if update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Delete Item"):
                st.success("削除しました。")
                st.rerun()
    else:
        st.write("履歴の最新1件を削除したい場合は以下を押してください。")
        if st.button("最新の履歴を1件消す"):
            df_log = df_log.drop(df_log.index[-1])
            if update_github_data(FILE_PATH_LOG, df_log, sha_log, "Delete Log"):
                st.success("最新の履歴を削除しました。")
                st.rerun()

# --- 5. 入出庫履歴 ---
st.divider()
st.subheader("📜 入出庫履歴")
if not df_log.empty:
    st.dataframe(df_log.sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
