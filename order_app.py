import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import io

# --- 1. 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_ORDERS = "order_log.csv"
FILE_PATH_MASTER = "material_master.csv" # 新しいマスタファイル
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- 2. GitHub連携関数 ---
def get_github_data(file_path, default_cols):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_data = base64.b64decode(content["content"]).decode("utf-8")
        if not csv_data.strip():
            return pd.DataFrame(columns=default_cols), content["sha"]
        return pd.read_csv(io.StringIO(csv_data)), content["sha"]
    else:
        return pd.DataFrame(columns=default_cols), None

def update_github_data(file_path, df, sha, message):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    content_base64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    data = {"message": message, "content": content_base64, "sha": sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

st.set_page_config(page_title="資材管理システム", layout="wide", page_icon="📦")

# データ読み込み
df_orders, sha_orders = get_github_data(FILE_PATH_ORDERS, ["id","category","item_name","product_name","request_date","quantity","vendor","order_date","delivery_date","status"])
df_master, sha_master = get_github_data(FILE_PATH_MASTER, ["item_name", "product_name"])

# タブ分け
tab1, tab2 = st.tabs(["🛒 発注・管理", "⚙️ マスタ登録"])

# --- タブ1：発注・管理 ---
with tab1:
    st.title("📦 資材発注管理")
    
    # 現場：発注依頼
    st.header("🛒 現場：発注依頼")
    with st.expander("➕ 新規依頼フォーム", expanded=False):
        if df_master.empty:
            st.info("先にマスタ登録タブから資材と商品を登録してください。")
        else:
            # 【重要】資材名を選んだら、商品名を絞り込む
            unique_items = df_master["item_name"].unique()
            c_item = st.selectbox("資材名を選択", unique_items)
            
            # 選ばれた資材名に紐づく商品名だけにフィルター
            filtered_products = df_master[df_master["item_name"] == c_item]["product_name"].tolist()
            c_prod = st.selectbox("該当する商品名を選択", filtered_products)
            
            if st.button("依頼を送信", type="primary"):
                new_id = int(df_orders['id'].max() + 1) if not df_orders.empty else 1
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_row = pd.DataFrame([{"id": new_id, "item_name": c_item, "product_name": c_prod, "request_date": now, "status": "未対応"}])
                df_updated = pd.concat([df_orders, new_row], ignore_index=True)
                if update_github_data(FILE_PATH_ORDERS, df_updated, sha_orders, "New Request") in [200, 201]:
                    st.success("依頼完了！")
                    st.rerun()

    # (中略：担当者処理・履歴表示は前回のコードと同じ)

# --- タブ2：マスタ登録 ---
with tab2:
    st.header("⚙️ 資材・商品マスタ登録")
    st.write("ここで登録した「資材名」と「商品名」が、依頼フォームの選択肢になります。")
    
    with st.form("master_form"):
        new_item = st.text_input("資材名 (例: 化粧箱A)")
        new_prod = st.text_input("商品名 (例: クッキーセット)")
        if st.form_submit_button("マスタに追加"):
            if new_item and new_prod:
                new_m_row = pd.DataFrame([{"item_name": new_item, "product_name": new_prod}])
                df_m_updated = pd.concat([df_master, new_m_row], ignore_index=True).drop_duplicates()
                if update_github_data(FILE_PATH_MASTER, df_m_updated, sha_master, "Update Master") in [200, 201]:
                    st.success(f"登録しました: {new_item} - {new_prod}")
                    st.rerun()
            else:
                st.error("両方の項目を入力してください。")

    st.subheader("現在の登録内容")
    st.dataframe(df_master, use_container_width=True, hide_index=True)
