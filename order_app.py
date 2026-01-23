import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import io

# --- 1. 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_ORDERS = "order_log.csv"
FILE_PATH_MASTER = "material_master.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- 2. GitHub連携関数（エラーを力ずくで回避する仕様） ---
def get_github_data(file_path, default_cols):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        content = res.json()
        csv_data = base64.b64decode(content["content"]).decode("utf-8")
        if not csv_data.strip():
            return pd.DataFrame(columns=default_cols), content["sha"]
        
        df = pd.read_csv(io.StringIO(csv_data))
        
        # 【重要】足りない列（categoryなど）があれば自動で追加してエラーを防ぐ
        for col in default_cols:
            if col not in df.columns:
                df[col] = ""
        return df[default_cols], content["sha"]
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

# データ読み込み（列を強制固定）
order_cols = ["id","category","item_name","product_name","request_date","quantity","vendor","order_date","delivery_date","status"]
master_cols = ["category", "item_name", "product_name"]

df_orders, sha_orders = get_github_data(FILE_PATH_ORDERS, order_cols)
df_master, sha_master = get_github_data(FILE_PATH_MASTER, master_cols)

tab1, tab2, tab3 = st.tabs(["🛒 発注・管理", "⚙️ マスタ登録", "📑 履歴確認"])

# --- タブ1：発注・管理 ---
with tab1:
    st.title("📦 資材発注管理")
    st.header("🛒 現場：発注依頼")
    with st.expander("➕ 新規依頼フォーム", expanded=False):
        # マスタが空（あるいは全部空文字）の場合の処理
        if df_master.dropna(how='all').empty:
            st.warning("⚙️ 右側の「マスタ登録」タブから、カテゴリ・資材名・商品名を登録してください。")
        else:
            # カテゴリ選択（空文字を除外）
            cats = [c for c in df_master["category"].unique() if pd.notna(c) and c != ""]
            if not cats:
                st.info("マスタを登録してください。")
            else:
                c_cat = st.selectbox("カテゴリを選択", cats)
                items = df_master[df_master["category"] == c_cat]["item_name"].unique()
                c_item = st.selectbox("資材名を選択", items)
                prods = df_master[(df_master["category"] == c_cat) & (df_master["item_name"] == c_item)]["product_name"].unique()
                c_prod = st.selectbox("商品名を選択", prods)
                
                if st.button("依頼を送信", type="primary"):
                    new_id = int(df_orders['id'].max() + 1) if not df_orders.empty else 1
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    new_row = pd.DataFrame([{"id": new_id, "category": c_cat, "item_name": c_item, "product_name": c_prod, "request_date": now, "status": "未対応"}])
                    df_updated = pd.concat([df_orders, new_row], ignore_index=True)
                    if update_github_data(FILE_PATH_ORDERS, df_updated, sha_orders, "New Request") in [200, 201]:
                        st.success("依頼完了！")
                        st.rerun()

    st.divider()

    # 【B】担当者：発注処理（チェックボックス選択式）
    st.header("📝 担当者：発注処理")
    pending_df = df_orders[df_orders['status'] == '未対応'].copy()
    
    if not pending_df.empty:
        st.write("処理する項目にチェックを入れてください：")
        pending_df.insert(0, "選択", False)
        
        # 安定版のデータエディタ設定
        edited_df = st.data_editor(
            pending_df[["選択", "id", "category", "item_name", "product_name", "request_date"]],
            hide_index=True, use_container_width=True,
            disabled=["id", "category", "item_name", "product_name", "request_date"]
        )
        
        selected_ids = edited_df[edited_df["選択"] == True]["id"].tolist()

        if selected_ids:
            st.markdown(f"### 📋 選択中: {len(selected_ids)}件 の一括入力")
            with st.form("order_process_form"):
                payload = {}
                for sid in selected_ids:
                    row_info = pending_df[pending_df["id"] == sid].iloc[0]
                    st.markdown(f"**📍 ID:{sid} | {row_info['item_name']} ({row_info['product_name']})**")
                    col1, col2, col3 = st.columns(3)
                    with col1: q = st.number_input(f"数量", min_value=1, key=f"q_{sid}")
                    with col2: v = st.text_input(f"発注先", key=f"v_{sid}")
                    with col3: d = st.date_input(f"納品予定", key=f"d_{sid}")
                    payload[sid] = {"qty": q, "vendor": v, "date": d}
                
                if st.form_submit_button("✅ チェックした項目をすべて更新", use_container_width=True):
                    for oid, v in payload.items():
                        idx = df_orders[df_orders['id'] == oid].index[0]
                        df_orders.at[idx, 'quantity'] = v['qty']
                        df_orders.at[idx, 'vendor'] = v['vendor']
                        df_orders.at[idx, 'order_date'] = datetime.now().strftime("%Y-%m-%d")
                        df_orders.at[idx, 'delivery_date'] = str(v['date'])
                        df_orders.at[idx, 'status'] = "発注済み"
                    
                    if update_github_data(FILE_PATH_ORDERS, df_orders, sha_orders, "Process Orders") in [200, 201]:
                        st.success("一括更新しました！")
                        st.rerun()
    else:
        st.info("現在、未対応の依頼はありません。")

# --- タブ2：マスタ登録 ---
with tab2:
    st.header("⚙️ マスタ登録")
    with st.form("master_form"):
        m_cat = st.selectbox("カテゴリ", ["化粧箱", "トレイ", "ダンボール", "その他"])
        m_item = st.text_input("資材名 (例: サービス箱B)")
        m_prod = st.text_input("商品名 (例: ショートケーキ用)")
        if st.form_submit_button("マスタに追加"):
            if m_item and m_prod:
                new_m_row = pd.DataFrame([{"category": m_cat, "item_name": m_item, "product_name": m_prod}])
                df_m_updated = pd.concat([df_master, new_m_row], ignore_index=True).drop_duplicates()
                if update_github_data(FILE_PATH_MASTER, df_m_updated, sha_master, "Update Master") in [200, 201]:
                    st.success("マスタに登録しました！「発注・管理」タブで選択できるようになります。")
                    st.rerun()
            else:
                st.error("入力が漏れています。")

    st.subheader("登録済みのマスタ一覧")
    st.dataframe(df_master.dropna(how='all'), use_container_width=True, hide_index=True)

# --- タブ3：履歴確認 ---
with tab3:
    st.header("📑 全発注履歴")
    st.dataframe(df_orders.sort_values("id", ascending=False), use_container_width=True, hide_index=True)
