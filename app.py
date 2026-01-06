import streamlit as st
import pandas as pd
import datetime as dt 
import base64
import requests
from io import StringIO

def get_now_jst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")

# --- 1. 設定 ---
REPO_NAME = "iplan381/zaiko-kanri" 
FILE_PATH_STOCK = "inventory_main.csv"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

SIZES_MASTER = ["大", "中", "小", "4個入", " - "]
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

# 💡 在庫列をヘッダーと同じ濃いグレーにする関数
def highlight_alert(row):
    styles = [''] * len(row)
    col_names = row.index.tolist()
    stock_idx = col_names.index("在庫数")
    
    # 1. 在庫列を濃いグレーにし、文字を白太字にする
    styles[stock_idx] = 'background-color: #262730; color: white; font-weight: bold;' 

    # 2. アラート時はこちらが優先（行全体を濃い赤）
    if row["在庫数"] <= row["アラート基準"]:
        return ['background-color: #d9534f; color: white'] * len(row)
    
    return styles

# データ読み込み
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)

# --- 3. サイドバー：新規登録 ＆ 絞り込みスイッチ ---
with st.sidebar:
    st.header("✨ 新規商品登録")
    n_item = st.text_input("商品名 ")
    n_size = st.selectbox("サイズ ", SIZES_MASTER)
    n_loc = st.text_input("地名 ")
    n_vendor = st.selectbox("取引先 ", VENDORS_MASTER)
    n_stock = st.number_input("初期在庫", min_value=0, value=0)
    n_alert = st.number_input("アラート基準", min_value=0, value=5)
    
    if st.button("新規登録実行", use_container_width=True, type="primary"):
        is_duplicate = not df_stock[(df_stock["商品名"] == n_item) & (df_stock["サイズ"] == n_size) & (df_stock["地名"] == n_loc)].empty
        if is_duplicate:
            st.error(f"❌ 重複エラー：既に登録されています。")
        elif n_item and n_loc:
            now = get_now_jst()
            new_row = pd.DataFrame([{"最終更新日": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "在庫数": n_stock, "アラート基準": n_alert, "取引先": n_vendor}])
            new_log = pd.DataFrame([{"日時": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "区分": "新規登録", "数量": n_stock, "担当者": "システム"}])
            if update_github_data(FILE_PATH_STOCK, pd.concat([df_stock, new_row], ignore_index=True), sha_stock, "Add Item") and \
               update_github_data(FILE_PATH_LOG, pd.concat([df_log, new_log], ignore_index=True), sha_log, "Add Log"):
                st.success("登録完了！")
                st.rerun()
    
    st.divider()
    # 💡 履歴絞り込みのスイッチ
    sync_logs = st.checkbox("履歴も検索条件で絞り込む", value=True)

# --- 4. メイン：在庫一覧 ---
st.title("📦 在庫管理")
st.subheader("📊 在庫一覧")

c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("検索:商品名", get_opts(df_stock["商品名"]))
with c2: s_size = st.selectbox("検索:サイズ", get_opts(df_stock["サイズ"]))
with c3: search_loc = st.text_input("検索:地名（手入力）", placeholder="例: 青森")
with c4: s_vendor = st.selectbox("検索:取引先", get_opts(df_stock["取引先"]))

# 💡 検索ロジック：空欄や「すべて」を正しく判定
df_disp = df_stock.copy()
if s_item != "すべて": 
    df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": 
    df_disp = df_disp[df_disp["サイズ"] == s_size]
if search_loc.strip(): 
    df_disp = df_disp[df_disp["地名"].astype(str).str.contains(search_loc, na=False)]
if s_vendor != "すべて": 
    df_disp = df_disp[df_disp["取引先"] == s_vendor]

df_disp = df_disp.sort_values("最終更新日", ascending=False)
styled_df = df_disp.style.apply(highlight_alert, axis=1)

event = st.dataframe(
    styled_df, 
    use_container_width=True, 
    hide_index=True, 
    on_select="rerun", 
    selection_mode="single-row",
    column_config={
        "最終更新日": "日時",
        "商品名": "商品名",
        "サイズ": "サイズ",
        "地名": "地名",
        "在庫数": "在庫",
        "アラート基準": "基準",
        "取引先": "取引先",
    }
)

# --- 5. 操作パネル ---
st.divider()
selected_rows = event.selection.rows
selected_data = df_disp.iloc[selected_rows[0]] if selected_rows else None

if selected_data is not None:
    st.markdown(f"### 選択中: {selected_data['商品名']} ({selected_data['サイズ']})")
    st.metric(label="現在の在庫数", value=f"{selected_data['在庫数']} c/s") 
    
    st.divider()
    t1, t2 = st.tabs(["🔄 在庫・サイズ・地名更新", "🗑️ この行を削除"])
    
    with t1:
        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            new_loc_val = st.text_input("地名を変更", value=selected_data['地名'])
        with edit_col2:
            default_size_idx = SIZES_MASTER.index(selected_data['サイズ']) if selected_data['サイズ'] in SIZES_MASTER else 0
            new_size_val = st.selectbox("サイズを変更", SIZES_MASTER, index=default_size_idx)

        st.divider()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            move_type = st.radio("区分", ["入庫", "出庫", "設定のみ"], horizontal=True)
        with col2:
            move_qty = st.number_input("数量", min_value=0, value=1) if move_type != "設定のみ" else 0
        with col3:
            new_alert_val = st.number_input("アラート基準", min_value=0, value=int(selected_data['アラート基準']))
        with col4:
            user_opts = ["-- 選択してください --"] + USERS
            default_idx = 0
            if "last_user" in st.session_state:
                if st.session_state.last_user in user_opts:
                    default_idx = user_opts.index(st.session_state.last_user)
            user_name = st.selectbox("担当者", user_opts, index=default_idx)
            
            is_disabled = (user_name == "-- 選択してください --")
            
            if st.button("更新を確定する", type="primary", use_container_width=True, disabled=is_disabled):
                st.session_state.last_user = user_name
                now = get_now_jst()
                idx = df_stock[(df_stock["商品名"] == selected_data["商品名"]) & 
                              (df_stock["サイズ"] == selected_data["サイズ"]) & 
                              (df_stock["地名"] == selected_data["地名"])].index[0]
                
                if move_type == "入庫": df_stock.at[idx, "在庫数"] += move_qty
                elif move_type == "出庫": df_stock.at[idx, "在庫数"] -= move_qty
                
                df_stock.at[idx, "地名"] = new_loc_val
                df_stock.at[idx, "サイズ"] = new_size_val
                df_stock.at[idx, "アラート基準"] = new_alert_val
                df_stock.at[idx, "最終更新日"] = now
                
                log_row = pd.DataFrame([{"日時": now, "商品名": selected_data["商品名"], "サイズ": new_size_val, 
                                       "地名": new_loc_val, "区分": move_type if move_type != "設定のみ" else "編集", 
                                       "数量": move_qty, "担当者": user_name}])
                
                if update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Update/Edit") and \
                   update_github_data(FILE_PATH_LOG, pd.concat([df_log, log_row], ignore_index=True), sha_log, "Log"):
                    st.success("編集・更新が完了しました！")
                    st.rerun()

    with t2:
        if st.button("はい、このデータを削除します", type="primary", use_container_width=True):
            mask = (df_stock["商品名"] == selected_data["商品名"]) & \
                   (df_stock["サイズ"] == selected_data["サイズ"]) & \
                   (df_stock["地名"] == selected_data["地名"])
            if mask.any():
                idx = df_stock[mask].index[0]
                df_stock = df_stock.drop(idx)
                if update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Delete"):
                    st.success("削除しました")
                    st.rerun()
else:
    st.write("💡 **一覧から行を選択すると、ここに入出庫・サイズ編集・削除のメニューが出ます。**")
    
# --- 6. 履歴表示 ---
st.divider()
st.subheader("📜 入出庫履歴")
if not df_log.empty:
    df_log_filt = df_log.copy()
    if sync_logs:
        if s_item != "すべて":
            df_log_filt = df_log_filt[df_log_filt["商品名"] == s_item]
        if s_size != "すべて":
            df_log_filt = df_log_filt[df_log_filt["サイズ"] == s_size]
        if search_loc.strip():
            df_log_filt = df_log_filt[df_log_filt["地名"].astype(str).str.contains(search_loc, na=False)]

    df_log_display = df_log_filt[["日時", "商品名", "サイズ", "地名", "区分", "数量", "担当者"]]
    
    st.dataframe(
        df_log_display.sort_values("日時", ascending=False), 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "日時": "日時",
            "商品名": "商品名",
            "サイズ": "サイズ",
            "地名": "地名",
            "区分": "区分",
            "数量": st.column_config.NumberColumn("数", format="%d"),
            "担当者": "担当者",
        }
    )
