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
        df = pd.read_csv(io.StringIO(csv_data))
        for col in default_cols:
            if col not in df.columns: df[col] = ""
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

# データ読み込み
order_cols = ["id","category","item_name","product_name","request_date","quantity","vendor","order_date","delivery_date","status"]
master_cols = ["category", "item_name", "product_name"]
df_orders, sha_orders = get_github_data(FILE_PATH_ORDERS, order_cols)
df_master, sha_master = get_github_data(FILE_PATH_MASTER, master_cols)

# --- 👈 サイドバー：新規発注依頼 ---
with st.sidebar:
    st.title("➕ 新規発注依頼")
    if df_master.dropna(how='all').empty:
        st.warning("先にマスタ登録が必要です。")
    else:
        cats = [c for c in df_master["category"].unique() if pd.notna(c) and c != ""]
        c_cat = st.selectbox("1. カテゴリ", cats)
        items = df_master[df_master["category"] == c_cat]["item_name"].unique()
        c_item = st.selectbox("2. 資材名", items)
        prods = df_master[(df_master["category"] == c_cat) & (df_master["item_name"] == c_item)]["product_name"].unique()
        c_prod = st.selectbox("3. 商品名", prods)
        
        if st.button("依頼を送信", type="primary", use_container_width=True):
            new_id = int(df_orders['id'].max() + 1) if not df_orders.empty else 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_row = pd.DataFrame([{"id": new_id, "category": c_cat, "item_name": c_item, "product_name": c_prod, "request_date": now, "status": "未対応"}])
            df_updated = pd.concat([df_orders, new_row], ignore_index=True)
            if update_github_data(FILE_PATH_ORDERS, df_updated, sha_orders, "New Request") in [200, 201]:
                st.success("依頼完了！")
                st.rerun()
    
    st.divider()
    # マスタ登録はサイドバーの下の方に配置
    with st.expander("⚙️ マスタ登録・編集"):
        with st.form("master_form"):
            m_cat = st.selectbox("カテゴリ", ["化粧箱", "トレイ", "ダンボール", "その他"])
            m_item = st.text_input("資材名")
            m_prod = st.text_input("商品名")
            if st.form_submit_button("マスタに追加", use_container_width=True):
                if m_item and m_prod:
                    new_m_row = pd.DataFrame([{"category": m_cat, "item_name": m_item, "product_name": m_prod}])
                    df_m_updated = pd.concat([df_master, new_m_row], ignore_index=True).drop_duplicates()
                    update_github_data(FILE_PATH_MASTER, df_m_updated, sha_master, "Update Master")
                    st.rerun()

# --- メイン画面 ---
st.title("📦 資材管理メインボード")

# 1. 未処理件数の目立つ表示
pending_df = df_orders[df_orders['status'] == '未対応'].copy()
count = len(pending_df)

if count > 0:
    # 赤背景に白文字の目立つスタイル
    st.markdown(f"""
        <div style="background-color: #ff4b4b; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 25px;">
            <h1 style="color: white; margin: 0;">⚠️ 未対応の依頼が {count} 件 あります</h1>
            <p style="color: white; margin: 5px 0 0 0;">下のリストからチェックを入れて発注処理を行ってください。</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.success("✅ すべての依頼が処理済みです。")

# 2. 発注処理エリア
st.header("📝 発注処理（未対応リスト）")
if not pending_df.empty:
    pending_df.insert(0, "選択", False)
    show_cols = ["選択", "category", "item_name", "product_name", "request_date"]
    edited_df = st.data_editor(
        pending_df[show_cols],
        hide_index=True, use_container_width=True,
        disabled=["category", "item_name", "product_name", "request_date"]
    )
    
    selected_indices = edited_df[edited_df["選択"] == True].index
    selected_ids = pending_df.loc[selected_indices, "id"].tolist()

    if selected_ids:
        with st.form("order_process_form"):
            payload = {}
            for sid in selected_ids:
                row = pending_df[pending_df["id"] == sid].iloc[0]
                st.markdown(f"**📍 {row['category']} / {row['item_name']} ({row['product_name']})**")
                c1, c2, c3 = st.columns(3)
                with c1: q = st.number_input(f"数量", min_value=1, key=f"q_{sid}")
                with c2: v = st.text_input(f"発注先", key=f"v_{sid}")
                with c3: d = st.date_input(f"納品予定", key=f"d_{sid}")
                payload[sid] = {"qty": q, "vendor": v, "date": d}
            
            if st.form_submit_button("✅ チェックした項目をすべて確定して発注済みにする", use_container_width=True):
                for oid, v in payload.items():
                    idx = df_orders[df_orders['id'] == oid].index[0]
                    df_orders.at[idx, 'quantity'], df_orders.at[idx, 'vendor'] = v['qty'], v['vendor']
                    df_orders.at[idx, 'order_date'] = datetime.now().strftime("%Y-%m-%d")
                    df_orders.at[idx, 'delivery_date'], df_orders.at[idx, 'status'] = str(v['date']), "発注済み"
                
                if update_github_data(FILE_PATH_ORDERS, df_orders, sha_orders, "Process") in [200, 201]:
                    st.toast("更新が完了しました！")
                    st.rerun()
else:
    st.info("現在、処理待ちのデータはありません。")

st.divider()

# 3. 履歴エリア（処理の下に配置）
st.header("📑 発注履歴（最近の30件）")
history_cols = ["status", "category", "item_name", "product_name", "quantity", "vendor", "delivery_date", "request_date"]
if not df_orders.empty:
    # ステータスが「発注済み」のものを上に、日付が新しい順に表示
    history_df = df_orders[history_cols].sort_values(by=["status", "request_date"], ascending=[False, False])
    st.dataframe(history_df.head(30), use_container_width=True, hide_index=True)
else:
    st.write("履歴はまだありません。")
