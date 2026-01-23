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

# 各ステータスのデータ抽出
pending_df = df_orders[df_orders['status'] == '未対応'].copy()
ordered_df = df_orders[df_orders['status'] == '発注済み'].copy()
count = len(pending_df)

# --- 👈 サイドバー：新規発注依頼 ---
with st.sidebar:
    st.title("➕ 新規発注依頼")
    st.divider()
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
                st.toast("✅ 依頼を送信しました！")
                st.rerun()
    st.divider()
    with st.expander("⚙️ マスタ登録"):
        with st.form("master_form", clear_on_submit=True):
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

# 1. 未対応通知（左詰め・赤地に白文字）
if count > 0:
    st.markdown(f"""
        <div style="background-color: #ff4b4b; color: white; padding: 12px 25px; border-radius: 8px; font-size: 18px; font-weight: bold; text-align: left; margin-bottom: 25px;">
            📢 未対応の依頼が {count} 件あります
        </div>
    """, unsafe_allow_html=True)

# 2. 【エリア1】発注処理待ち
st.subheader("📝 発注処理待ち")
if not pending_df.empty:
    pending_df.insert(0, "選択", False)
    edited_p = st.data_editor(pending_df[["選択", "category", "item_name", "product_name", "request_date"]], hide_index=True, use_container_width=True, key="pending_editor")
    selected_ids = pending_df.loc[edited_p[edited_p["選択"] == True].index, "id"].tolist()
    if selected_ids:
        with st.form("process_form"):
            payload = {}
            for sid in selected_ids:
                row = pending_df[pending_df["id"] == sid].iloc[0]
                st.write(f"📍 {row['item_name']} ({row['product_name']})")
                c1, c2, c3 = st.columns(3)
                payload[sid] = {"qty": c1.number_input("数量", min_value=1, key=f"q_{sid}"), "vendor": c2.text_input("発注先", key=f"v_{sid}"), "date": c3.date_input("納品予定", key=f"d_{sid}")}
            if st.form_submit_button("✅ チェックした項目を発注済みにする"):
                for oid, v in payload.items():
                    idx = df_orders[df_orders['id'] == oid].index[0]
                    df_orders.loc[idx, ["quantity","vendor","delivery_date","status","order_date"]] = [v['qty'], v['vendor'], str(v['date']), "発注済み", datetime.now().strftime("%Y-%m-%d")]
                update_github_data(FILE_PATH_ORDERS, df_orders, sha_orders, "Ordered")
                st.rerun()
else:
    st.info("現在、新規の依頼はありません。")

st.divider()

# 3. 【エリア2】発注済み（入荷待ち・編集可能）
st.subheader("🚚 発注済み")
if not ordered_df.empty:
    st.caption("※数量や納品予定日はここで直接編集して保存できます。入荷したらチェックを入れて確定してください。")
    ordered_df.insert(0, "入荷", False)
    # data_editorで数量と納品予定日を編集可能にする
    edited_ordered = st.data_editor(
        ordered_df[["入荷", "id", "category", "item_name", "product_name", "quantity", "vendor", "delivery_date", "order_date"]],
        hide_index=True, use_container_width=True,
        disabled=["category", "item_name", "product_name", "vendor", "order_date"],
        key="ordered_editor"
    )
    
    if st.button("✅ チェックした項目の納品を確認（完了へ）", type="primary"):
        # 編集された内容（数量・納品日）を反映しつつ、ステータスを完了にする
        for i, row in edited_ordered.iterrows():
            orig_id = row["id"]
            idx = df_orders[df_orders["id"] == orig_id].index[0]
            # 常に最新の編集値を反映
            df_orders.at[idx, "quantity"] = row["quantity"]
            df_orders.at[idx, "delivery_date"] = str(row["delivery_date"])
            # チェックが入っていれば完了
            if row["入荷"]:
                df_orders.at[idx, "status"] = "完了"
        
        update_github_data(FILE_PATH_ORDERS, df_orders, sha_orders, "Delivery Confirmed")
        st.toast("納品処理が完了しました！")
        st.rerun()
else:
    st.write("現在、入荷待ちの資材はありません。")

st.divider()

# 4. 【エリア3】履歴（完了分）
st.subheader("📑 3. 完了履歴（直近30件）")
done_df = df_orders[df_orders['status'] == '完了'].sort_values("delivery_date", ascending=False)
st.dataframe(done_df[["category", "item_name", "product_name", "quantity", "vendor", "delivery_date", "request_date"]].head(30), use_container_width=True, hide_index=True)
