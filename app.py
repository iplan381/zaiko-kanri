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
FILE_PATH_RESERVATION = "reservations_main.csv" # 💡 予約用パスを追加
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

# 💡 2. 予約を自動処理する関数
def process_reservations(df_stock, sha_stock, df_log, sha_log):
    df_res, sha_res = get_github_data(FILE_PATH_RESERVATION)
    if df_res.empty: return df_stock, df_log
    
    # 今日の日付を取得
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    df_res["予約日_dt"] = pd.to_datetime(df_res["予約日"]).dt.date
    
    # 今日以前（当日含む）の予約を抽出
    to_process = df_res[df_res["予約日_dt"] <= today]
    
    if not to_process.empty:
        new_logs = []
        for _, row in to_process.iterrows():
            mask = (df_stock["商品名"] == row["商品名"]) & (df_stock["サイズ"] == row["サイズ"]) & (df_stock["地名"] == row["地名"])
            if mask.any():
                idx = df_stock[mask].index[0]
                df_stock.at[idx, "在庫数"] -= row["数量"]
                df_stock.at[idx, "最終更新日"] = get_now_jst()
                new_logs.append({
                    "日時": get_now_jst(), "商品名": row["商品名"], "サイズ": row["サイズ"], 
                    "地名": row["地名"], "区分": "出庫(予約実行)", "数量": row["数量"], "担当者": row["担当者"]
                })
        
        # 処理が終わったものを削除して更新
        df_res_remain = df_res[df_res["予約日_dt"] > today].drop(columns=["予約日_dt"])
        update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Auto Reservation Executed")
        update_github_data(FILE_PATH_LOG, pd.concat([df_log, pd.DataFrame(new_logs)], ignore_index=True), sha_log, "Auto Res Log")
        update_github_data(FILE_PATH_RESERVATION, df_res_remain, sha_res, "Clean up Reservation")
        st.success(f"📢 本日の出庫予約（{len(to_process)}件）を在庫に反映しました！")
        st.rerun()
    return df_stock, df_log

def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

def highlight_alert(row):
    styles = [''] * len(row)
    col_names = row.index.tolist()
    if "在庫数" in col_names:
        stock_idx = col_names.index("在庫数")
        styles[stock_idx] = 'background-color: #262730; color: white; font-weight: bold;' 
        if row["在庫数"] < row["アラート基準"]:
            return ['background-color: #d9534f; color: white'] * len(row)
    return styles

# データ読み込み
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)

# 💡 データ読み込み直後に予約チェックを実行
df_stock, df_log = process_reservations(df_stock, sha_stock, df_log, sha_log)

# --- 3. サイドバー ---
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
            st.error(f"❌ 重複エラー")
        elif n_item and n_loc:
            now = get_now_jst()
            new_row = pd.DataFrame([{"最終更新日": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "在庫数": n_stock, "アラート基準": n_alert, "取引先": n_vendor}])
            new_log = pd.DataFrame([{"日時": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "区分": "新規登録", "数量": n_stock, "担当者": "システム"}])
            if update_github_data(FILE_PATH_STOCK, pd.concat([df_stock, new_row], ignore_index=True), sha_stock, "Add Item") and \
               update_github_data(FILE_PATH_LOG, pd.concat([df_log, new_log], ignore_index=True), sha_log, "Add Log"):
                st.success("登録完了")
                st.rerun()
    
    st.divider()
    sync_logs = st.checkbox("履歴も在庫検索と連動させる", value=True)

# --- 4. メイン：在庫一覧 ---
st.title("📦 在庫管理")
st.subheader("📊 在庫一覧")

c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("検索:商品名", get_opts(df_stock["商品名"]))
with c2: s_size = st.selectbox("検索:サイズ", get_opts(df_stock["サイズ"]))
with c3: search_loc = st.text_input("検索:地名（手入力）", placeholder="例: 青森")
with c4: s_vendor = st.selectbox("検索:取引先", get_opts(df_stock["取引先"]))

df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if search_loc.strip(): df_disp = df_disp[df_disp["地名"].astype(str).str.contains(search_loc, na=False)]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

df_disp = df_disp.sort_values("最終更新日", ascending=False)
styled_df = df_disp.style.apply(highlight_alert, axis=1)

event = st.dataframe(
    styled_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row",
    column_config={"最終更新日": "日時", "在庫数": "在庫", "数量": st.column_config.NumberColumn(format="%d")}
)

# --- 5. 操作パネル：一括編集 ---
st.divider()
selected_indices = event.selection.rows
selected_data_list = df_disp.iloc[selected_indices] if selected_indices else pd.DataFrame()

if not selected_data_list.empty:
    n_selected = len(selected_data_list)
    st.markdown(f"### 📋 {n_selected} 件の一括操作")
    
    user_list = ["-- 選択 --"] + USERS
    default_user_idx = 0
    if "last_user" in st.session_state and st.session_state.last_user in user_list:
        default_user_idx = user_list.index(st.session_state.last_user)
    
    user_name = st.selectbox("担当者を選んでください", user_list, index=default_user_idx)
    
    if user_name != "-- 選択 --":
        st.info("💡 変更したい項目を入力してください（予約出庫は未来の日付を選べます）")
        
        update_payload = {}
        for i, row in selected_data_list.iterrows():
            with st.expander(f"📌 {row['商品名']} ({row['サイズ']} / {row['地名']}) - 現在の在庫: {row['在庫数']}", expanded=True):
                col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1, 1, 0.5])
                
                with col1:
                    # 💡 予約出庫を追加
                    m_type = st.radio("", ["入庫", "出庫", "予約出庫", "変更なし"], horizontal=True, key=f"type_{i}", label_visibility="collapsed")
                with col2:
                    m_qty = st.number_input("", min_value=0, value=0, key=f"qty_{i}", label_visibility="collapsed")
                with col3:
                    # 💡 予約出庫の時は日付、それ以外は地名変更
                    if m_type == "予約出庫":
                        res_date = st.date_input("予約日", value=dt.date.today() + dt.timedelta(days=1), key=f"date_{i}")
                    else:
                        new_loc = st.text_input("地名変更", value=row['地名'], key=f"loc_{i}")
                with col4:
                    new_alert = st.number_input("アラート基準", min_value=0, value=int(row['アラート基準']), key=f"alt_{i}")
                with col5:
                    is_delete = st.checkbox("🗑️", key=f"del_{i}")
                
                update_payload[i] = {
                    "type": m_type, "qty": m_qty, "loc": new_loc if m_type != "予約出庫" else row['地名'], 
                    "alert": new_alert, "delete": is_delete, "res_date": res_date if m_type == "予約出庫" else None, "orig_data": row
                }
        
        if st.button("🔄 全ての変更を確定する", type="primary", use_container_width=True):
            st.session_state.last_user = user_name
            now = get_now_jst()
            new_logs = []
            new_reservations = []
            
            for idx_in_disp, p in update_payload.items():
                row = p["orig_data"]
                target_mask = (df_stock["商品名"] == row["商品名"]) & \
                              (df_stock["サイズ"] == row["サイズ"]) & \
                              (df_stock["地名"] == row["地名"])
                
                if target_mask.any():
                    orig_idx = df_stock[target_mask].index[0]
                    
                    if p["delete"]:
                        df_stock = df_stock.drop(orig_idx)
                        new_logs.append({"日時": now, "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": row["地名"], "区分": "削除", "数量": 0, "担当者": user_name})
                    elif p["type"] == "予約出庫":
                        # 💡 予約リストに追加（ここでは在庫を減らさない）
                        if p["qty"] > 0:
                            new_reservations.append({
                                "予約日": p["res_date"], "商品名": row["商品名"], "サイズ": row["サイズ"],
                                "地名": row["地名"], "数量": p["qty"], "担当者": user_name
                            })
                    else:
                        if p["type"] == "入庫":
                            df_stock.at[orig_idx, "在庫数"] += p["qty"]
                        elif p["type"] == "出庫":
                            df_stock.at[orig_idx, "在庫数"] -= p["qty"]
                        
                        df_stock.at[orig_idx, "地名"] = p["loc"]
                        df_stock.at[orig_idx, "アラート基準"] = p["alert"]
                        df_stock.at[orig_idx, "最終更新日"] = now
                        
                        if p["qty"] > 0:
                            new_logs.append({"日時": now, "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": p["loc"], "区分": p["type"], "数量": p["qty"], "担当者": user_name})
                        if p["loc"] != row["地名"]:
                            new_logs.append({"日時": now, "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": p["loc"], "区分": "地名変更", "数量": 0, "担当者": user_name})

            # --- GitHub保存処理 ---
            update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Batch Update")
            if new_logs:
                update_github_data(FILE_PATH_LOG, pd.concat([df_log, pd.DataFrame(new_logs)], ignore_index=True), sha_log, "Log Update")
            
            # 💡 予約データの保存
            if new_reservations:
                df_res_old, sha_res = get_github_data(FILE_PATH_RESERVATION)
                update_github_data(FILE_PATH_RESERVATION, pd.concat([df_res_old, pd.DataFrame(new_reservations)], ignore_index=True), sha_res, "Add Reservation")
                
            st.rerun()
else:
    st.info("💡 **一覧で複数チェックを入れると、一括編集・予約・削除パネルが表示されます。**")

# --- 6. 履歴表示 ---
st.divider()
log_h_col1, log_h_col2, log_h_col3 = st.columns([1.5, 2, 2])
with log_h_col1:
    st.subheader("📜 入出庫履歴")
with log_h_col2:
    log_types = st.multiselect("区分:", ["入庫", "出庫", "出庫(予約実行)", "削除", "地名変更", "新規登録"], default=["入庫", "出庫", "出庫(予約実行)", "新規登録"], label_visibility="collapsed")
with log_h_col3:
    log_date_range = st.date_input("期間選択", value=(dt.date.today() - dt.timedelta(days=7), dt.date.today()), label_visibility="collapsed")

if not df_log.empty:
    df_log_filt = df_log.copy()
    if isinstance(log_date_range, tuple) and len(log_date_range) == 2:
        start_date, end_date = log_date_range
        df_log_filt["日時_dt"] = pd.to_datetime(df_log_filt["日時"]).dt.date
        df_log_filt = df_log_filt[(df_log_filt["日時_dt"] >= start_date) & (df_log_filt["日時_dt"] <= end_date)]
    if log_types:
        df_log_filt = df_log_filt[df_log_filt["区分"].isin(log_types)]
    if sync_logs:
        if s_item != "すべて": df_log_filt = df_log_filt[df_log_filt["商品名"] == s_item]
        if s_size != "すべて": df_log_filt = df_log_filt[df_log_filt["サイズ"] == s_size]
        if search_loc.strip(): df_log_filt = df_log_filt[df_log_filt["地名"].astype(str).str.contains(search_loc, na=False)]

    st.dataframe(
        df_log_filt[["日時", "商品名", "サイズ", "地名", "区分", "数量", "担当者"]].sort_values("日時", ascending=False), 
        use_container_width=True, hide_index=True,
        column_config={"数量": st.column_config.NumberColumn("数", format="%d")}
    )
