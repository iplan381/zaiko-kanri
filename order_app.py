import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import io

# --- 1. 設定（あなたの環境用） ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_ORDERS = "order_log.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- 2. GitHub連携用関数 ---
def get_github_data(file_path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    cols = ["id","category","item_name","product_name","request_date","quantity","vendor","order_date","delivery_date","status"]
    if res.status_code == 200:
        content = res.json()
        csv_data = base64.b64decode(content["content"]).decode("utf-8")
        if not csv_data.strip():
            return pd.DataFrame(columns=cols), content["sha"]
        df = pd.read_csv(io.StringIO(csv_data))
        return df, content["sha"]
    else:
        return pd.DataFrame(columns=cols), None

def update_github_data(file_path, df, sha, message):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    content_base64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    data = {"message": message, "content": content_base64, "sha": sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 3. 資材マスタ ---
MASTER_DATA = {
    "化粧箱": {
        "ギフト箱A": ["クッキーセット", "ゼリー詰合せ"],
        "サービス箱B": ["ショートケーキ用", "シュークリーム用"]
    },
    "トレイ": {
        "透明トレイS": ["サラダ用", "フルーツ用"],
        "耐熱L": ["カレー弁当", "パスタ用"]
    }
}

st.set_page_config(page_title="資材発注システム", layout="wide", page_icon="📦")
st.title("📦 資材発注管理システム")

# データ読み出し
df_orders, sha_orders = get_github_data(FILE_PATH_ORDERS)

# --- 4. 未対応通知 ---
pending_df = df_orders[df_orders['status'] == '未対応']
if not pending_df.empty:
    st.warning(f"⚠️ **未対応の発注依頼が {len(pending_df)} 件あります。**")
else:
    st.success("✅ 全ての依頼が処理済みです。")

# --- 5. 現場：発注依頼 ---
st.header("🛒 現場：発注依頼")
with st.expander("➕ 新規依頼フォーム", expanded=False):
    c_cat = st.selectbox("カテゴリ", list(MASTER_DATA.keys()))
    c_item = st.selectbox("資材名", list(MASTER_DATA[c_cat].keys()))
    c_prod = st.selectbox("商品名", MASTER_DATA[c_cat][c_item])
    
    if st.button("依頼を送信", type="primary", use_container_width=True):
        new_id = int(df_orders['id'].max() + 1) if not df_orders.empty else 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_row = pd.DataFrame([{
            "id": new_id, "category": c_cat, "item_name": c_item, "product_name": c_prod,
            "request_date": now, "status": "未対応", "quantity": 0, "vendor": "",
            "order_date": "", "delivery_date": ""
        }])
        df_updated = pd.concat([df_orders, new_row], ignore_index=True)
        if update_github_data(FILE_PATH_ORDERS, df_updated, sha_orders, f"Request {c_item}") in [200, 201]:
            st.success("依頼完了！")
            st.rerun()

st.divider()

# --- 6. 担当者：発注処理（ここをエラー回避のために書き換えました） ---
st.header("📝 担当者：発注処理")
if not pending_df.empty:
    # 古いStreamlitでも動くように、ID入力方式に変更
    st.write("処理する依頼のIDを選択してください：")
    target_ids = st.multiselect("IDを選択", pending_df['id'].tolist())

    if target_ids:
        selected_rows = pending_df[pending_df['id'].isin(target_ids)]
        with st.form("order_process_form"):
            payload = {}
            for _, r in selected_rows.iterrows():
                st.markdown(f"**📌 ID:{r['id']} | {r['item_name']}**")
                col1, col2, col3 = st.columns(3)
                with col1: qty = st.number_input(f"数量 ({r['id']})", min_value=1, key=f"q_{r['id']}")
                with col2: ven = st.text_input(f"発注先 ({r['id']})", key=f"v_{r['id']}")
                with col3: ddt = st.date_input(f"納品予定 ({r['id']})", key=f"d_{r['id']}")
                payload[r['id']] = {"qty": qty, "vendor": ven, "date": ddt}
            
            if st.form_submit_button("一括更新", use_container_width=True):
                for oid, v in payload.items():
                    idx = df_orders[df_orders['id'] == oid].index[0]
                    df_orders.at[idx, 'quantity'] = v['qty']
                    df_orders.at[idx, 'vendor'] = v['vendor']
                    df_orders.at[idx, 'order_date'] = datetime.now().strftime("%Y-%m-%d")
                    df_orders.at[idx, 'delivery_date'] = str(v['date'])
                    df_orders.at[idx, 'status'] = "発注済み"
                
                if update_github_data(FILE_PATH_ORDERS, df_orders, sha_orders, "Process Orders") in [200, 201]:
                    st.success("更新しました！")
                    st.rerun()
    
    st.write("現在の未対応一覧：")
    st.dataframe(pending_df[["id", "category", "item_name", "product_name", "request_date"]], use_container_width=True, hide_index=True)
else:
    st.info("対応が必要な依頼はありません。")

with st.expander("📑 履歴一覧"):
    st.dataframe(df_orders.sort_values("id", ascending=False), use_container_width=True, hide_index=True)
    
