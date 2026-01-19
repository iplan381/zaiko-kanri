import streamlit as st
import pandas as pd
import datetime as dt 
import base64
import requests
import time
from io import StringIO

def get_now_jst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")

# --- 1. 設定 ---
REPO_NAME = "iplan381/zaiko-kanri" 
FILE_PATH_STOCK = "inventory_main.csv"
FILE_PATH_LOG = "stock_log_main.csv"
FILE_PATH_RESERVATION = "reservations_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

SIZES_MASTER = ["大", "中", "小", "4個入", " - "]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]
USERS = ["佐藤", "手塚", "檀原"]

st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- 2. GitHub関数 (キャッシュ対策済み) ---
def get_github_data(file_path):
    # URLにタイムスタンプを足してGitHubから「常に最新」を強制取得する
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}?t={time.time()}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        # 読み込み時は型を指定せず、後で安全に処理する
        df = pd.read_csv(StringIO(csv_text), dtype=str)
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

# データ読み込み
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)
df_res_all, sha_res_all = get_github_data(FILE_PATH_RESERVATION)

# 在庫数やアラート基準を数値に変換（安全策）
for col in ["在庫数", "アラート基準"]:
    if col in df_stock.columns:
        df_stock[col] = pd.to_numeric(df_stock[col], errors='coerce').fillna(0).astype(int)

def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

def highlight_alert(row):
    styles = [''] * len(row)
    if "有効在庫" in row.index and row["有効在庫"] < row["アラート基準"]:
        return ['background-color: #d9534f; color: white'] * len(row)
    return styles

# --- 3. サイドバー：新規商品登録 ---
with st.sidebar:
    st.header("✨ 新規商品登録")
    n_item = st.text_input("商品名", key="sidebar_n_item")
    n_size = st.selectbox("サイズ", SIZES_MASTER, key="sidebar_n_size")
    n_loc = st.text_input("地名", key="sidebar_n_loc")
    n_vendor = st.selectbox("取引先", VENDORS_MASTER, key="sidebar_n_vendor")
    n_stock = st.number_input("初期在庫", min_value=0, value=0, key="sidebar_n_stock")
    n_alert = st.number_input("アラート基準", min_value=0, value=5, key="sidebar_n_alert")
    
    if st.button("新規登録実行", use_container_width=True, type="primary"):
        is_duplicate = not df_stock[(df_stock["商品名"] == n_item) & (df_stock["サイズ"] == n_size) & (df_stock["地名"] == n_loc)].empty
        if is_duplicate:
            st.error(f"❌ 重複エラー")
        elif n_item and n_loc:
            now = get_now_jst()
            new_row = pd.DataFrame([{"最終更新日": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "在庫数": n_stock, "アラート基準": n_alert, "取引先": n_vendor}])
            new_log = pd.DataFrame([{"日時": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "区分": "新規登録", "数量": n_stock, "在庫数": n_stock, "担当者": "システム"}])
            if update_github_data(FILE_PATH_STOCK, pd.concat([df_stock, new_row], ignore_index=True), sha_stock, "Add Item") and \
               update_github_data(FILE_PATH_LOG, pd.concat([df_log, pd.DataFrame(new_log)], ignore_index=True), sha_log, "Add Log"):
                st.success("登録完了")
                st.rerun()

# --- 4. メイン：在庫一覧 ---
st.title("📦 在庫管理")

c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("検索:商品名", get_opts(df_stock["商品名"]), key="filter_item")
with c2: s_size = st.selectbox("検索:サイズ", get_opts(df_stock["サイズ"]), key="filter_size")
with c3: search_loc = st.text_input("検索:地名（手入力）", placeholder="例: 青森", key="filter_loc")
with c4: s_vendor = st.selectbox("検索:取引先", get_opts(df_stock["取引先"]), key="filter_vendor")

# 有効在庫の計算
df_disp = df_stock.copy()
if not df_res_all.empty:
    df_res_all["数量"] = pd.to_numeric(df_res_all["数量"], errors='coerce').fillna(0)
    res_sum = df_res_all.groupby(["商品名", "サイズ", "地名"])["数量"].sum().reset_index().rename(columns={"数量": "予約計"})
    df_disp = pd.merge(df_disp, res_sum, on=["商品名", "サイズ", "地名"], how="left").fillna({"予約計": 0})
else:
    df_disp["予約計"] = 0

df_disp["有効在庫"] = df_disp["在庫数"] - df_disp["予約計"]

# フィルタリング
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if search_loc.strip(): df_disp = df_disp[df_disp["地名"].astype(str).str.contains(search_loc, na=False)]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

df_show = df_disp[["最終更新日", "商品名", "サイズ", "地名", "在庫数", "有効在庫", "アラート基準", "取引先"]].sort_values("最終更新日", ascending=False)
styled_df = df_show.style.apply(highlight_alert, axis=1)

event = st.dataframe(
    styled_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row",
    column_config={
        "在庫数": st.column_config.NumberColumn("実在庫", format="%d"),
        "有効在庫": st.column_config.NumberColumn("有効在庫", format="%d")
    }
)

# --- 5. 操作パネル ---
st.divider()
selected_indices = event.selection.rows
if selected_indices:
    selected_data_list = df_show.iloc[selected_indices]
    st.markdown(f"### 📋 {len(selected_data_list)} 件の一括操作")
    user_list = ["-- 選択 --"] + USERS
    user_name = st.selectbox("担当者を選んでください", user_list)
    
    if user_name != "-- 選択 --":
        update_payload = {}
        for i, row in selected_data_list.iterrows():
            with st.expander(f"📌 {row['商品名']} ({row['サイズ']} / {row['地名']})", expanded=True):
                col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1.2, 1, 0.6])
                with col1: m_type = st.radio("操作区分", ["入庫", "出庫", "予約出庫", "調整"], horizontal=True, key=f"type_{i}")
                with col2:
                    m_qty = st.number_input("数量", value=0, key=f"qty_{i}")
                with col3:
                    if m_type == "予約出庫":
                        res_date = st.date_input("予約日", value=dt.date.today() + dt.timedelta(days=1), key=f"date_{i}")
                        new_loc = row['地名']
                    else:
                        new_loc = st.text_input("地名変更", value=row['地名'], key=f"loc_{i}")
                with col4: new_alert = st.number_input("アラート基準", min_value=0, value=int(row['アラート基準']), key=f"alt_{i}")
                with col5: is_delete = st.checkbox("削除", key=f"del_{i}")
                update_payload[i] = {"type": m_type, "qty": m_qty, "loc": new_loc, "alert": new_alert, "delete": is_delete, "res_date": res_date if m_type == "予約出庫" else None, "orig_data": row}

        if st.button("🔄 全ての変更を確定する", type="primary", use_container_width=True):
            @st.dialog("変更内容の最終確認")
            def confirm_dialog(payloads):
                st.warning("⚠️ 以下の内容で更新します。間違いありませんか？")
                for idx, p in payloads.items():
                    if p['delete']: action_str = "🗑️ 【削除】"
                    elif p['type'] == "予約出庫": action_str = f"📅 【予約】 {p['qty']}件 ({p['res_date']})"
                    else: action_str = f"📦 【{p['type']}】 {p['qty']}件"
                    st.write(f"・{p['orig_data']['商品名']} ({p['orig_data']['サイズ']}/{p['loc']}) : {action_str}")
                
                st.divider()
                if st.button("はい、この内容で確定します", type="primary", use_container_width=True):
                    now, new_logs, new_reservations = get_now_jst(), [], []
                    temp_df_stock = df_stock.copy()
                    
                    for idx, p in payloads.items():
                        row = p["orig_data"]
                        target_mask = (temp_df_stock["商品名"] == row["商品名"]) & (temp_df_stock["サイズ"] == row["サイズ"]) & (temp_df_stock["地名"] == row["地名"])
                        if target_mask.any():
                            orig_idx = temp_df_stock[target_mask].index[0]
                            if p["delete"]:
                                temp_df_stock = temp_df_stock.drop(orig_idx)
                                new_logs.append({"日時": now, "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": row["地名"], "区分": "削除", "数量": 0, "在庫数": 0, "担当者": user_name})
                            elif p["type"] == "予約出庫" and p["qty"] > 0:
                                new_reservations.append({"予約日": str(p["res_date"]), "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": row["地名"], "数量": p["qty"], "担当者": user_name})
                            else:
                                if p["type"] == "入庫" or p["type"] == "調整": temp_df_stock.at[orig_idx, "在庫数"] += p["qty"]
                                elif p["type"] == "出庫": temp_df_stock.at[orig_idx, "在庫数"] -= p["qty"]
                                
                                temp_df_stock.at[orig_idx, "地名"], temp_df_stock.at[orig_idx, "アラート基準"], temp_df_stock.at[orig_idx, "最終更新日"] = p["loc"], p["alert"], now
                                curr_stock = temp_df_stock.at[orig_idx, "在庫数"]
                                
                                if p["qty"] != 0: 
                                    new_logs.append({"日時": now, "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": p["loc"], "区分": p["type"], "数量": p["qty"], "在庫数": curr_stock, "担当者": user_name})
                                if p["loc"] != row["地名"]: 
                                    new_logs.append({"日時": now, "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": p["loc"], "区分": "地名変更", "数量": 0, "在庫数": curr_stock, "担当者": user_name})
                    
                    if update_github_data(FILE_PATH_STOCK, temp_df_stock, sha_stock, "Batch Update"):
                        if new_logs: update_github_data(FILE_PATH_LOG, pd.concat([df_log, pd.DataFrame(new_logs)], ignore_index=True), sha_log, "Log Update")
                        if new_reservations:
                            df_res_old, sha_res = get_github_data(FILE_PATH_RESERVATION)
                            update_github_data(FILE_PATH_RESERVATION, pd.concat([df_res_old, pd.DataFrame(new_reservations)], ignore_index=True), sha_res, "Add Reservation")
                        st.success("✅ 更新完了しました！")
                        st.rerun()
            confirm_dialog(update_payload)
else:
    st.info("💡 **一覧で複数チェックを入れると、一括操作パネルが表示されます。**")

# --- 6. 予約・履歴 ---
st.divider()

# --- A. 出庫予約リスト ---
st.subheader("📅 出庫予約リスト")
if not df_res_all.empty:
    df_rv = df_res_all.copy()
    df_rv["予約日"] = pd.to_datetime(df_rv["予約日"], errors='coerce')
    df_rv = df_rv.dropna(subset=["予約日"])
    
    res_filter_item = st.selectbox("予約検索:商品名", get_opts(df_rv["商品名"]), key="res_f_item")
    if res_filter_item != "すべて": df_rv = df_rv[df_rv["商品名"] == res_filter_item]

    st.dataframe(df_rv.sort_values("予約日"), use_container_width=True, hide_index=True)
else:
    st.write("現在予約はありません。")

# --- B. 入出庫履歴 (バグ修正版) ---
st.subheader("📜 入出庫履歴")
if not df_log.empty:
    df_l = df_log.copy()
    # 数値列を変換
    for c in ["数量", "在庫数"]: df_l[c] = pd.to_numeric(df_l[c], errors='coerce').fillna(0)
    
    # 日時を表示用に安全変換
    df_l["日時_dt"] = pd.to_datetime(df_l["日時"], errors='coerce')
    df_l = df_l.dropna(subset=["日時_dt"])

    col_log1, col_log2, col_log3, col_log4 = st.columns(4)
    with col_log1:
        min_d, max_d = df_l["日時_dt"].min().date(), df_l["日時_dt"].max().date()
        l_range = st.date_input("期間", value=(min_d, max_d), key="log_date_filter")
    with col_log2: l_item = st.selectbox("履歴検索:商品名", get_opts(df_l["商品名"]), key="log_f_item")
    with col_log3: l_loc = st.selectbox("履歴検索:地名", get_opts(df_l["地名"]), key="log_f_loc")
    with col_log4:
        all_types = sorted(df_l["区分"].unique())
        sel_types = st.multiselect("区分", options=all_types, key="log_type_filter")

    # フィルタ適用
    if isinstance(l_range, tuple) and len(l_range) == 2:
        df_l = df_l[(df_l["日時_dt"].dt.date >= l_range[0]) & (df_l["日時_dt"].dt.date <= l_range[1])]
    if l_item != "すべて": df_l = df_l[df_l["商品名"] == l_item]
    if l_loc != "すべて": df_l = df_l[df_l["地名"] == l_loc]
    if sel_types: df_l = df_l[df_l["区分"].isin(sel_types)]

    st.dataframe(
        df_l[["日時", "商品名", "サイズ", "地名", "区分", "数量", "在庫数", "担当者"]].sort_values("日時", ascending=False),
        use_container_width=True, hide_index=True
    )
