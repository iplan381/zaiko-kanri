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
FILE_PATH_RESERVATION = "reservations_main.csv"
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

def process_reservations(df_stock, sha_stock, df_log, sha_log):
    df_res, sha_res = get_github_data(FILE_PATH_RESERVATION)
    if df_res.empty: return df_stock, df_log
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    df_res["予約日_dt"] = pd.to_datetime(df_res["予約日"]).dt.date
    to_process = df_res[df_res["予約日_dt"] <= today]
    if not to_process.empty:
        new_logs = []
        for _, row in to_process.iterrows():
            mask = (df_stock["商品名"] == row["商品名"]) & (df_stock["サイズ"] == row["サイズ"]) & (df_stock["地名"] == row["地名"])
            if mask.any():
                idx = df_stock[mask].index[0]
                df_stock.at[idx, "在庫数"] -= row["数量"]
                df_stock.at[idx, "最終更新日"] = get_now_jst()
                new_logs.append({"日時": get_now_jst(), "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": row["地名"], "区分": "出庫(予約実行)", "数量": row["数量"], "担当者": row["担当者"]})
        df_res_remain = df_res[df_res["予約日_dt"] > today].drop(columns=["予約日_dt"])
        update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Auto Res Exec")
        update_github_data(FILE_PATH_LOG, pd.concat([df_log, pd.DataFrame(new_logs)], ignore_index=True), sha_log, "Auto Res Log")
        update_github_data(FILE_PATH_RESERVATION, df_res_remain, sha_res, "Clean Res")
        st.success(f"📢 本日の予約を反映しました")
        st.rerun()
    return df_stock, df_log

def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

def highlight_alert(row):
    styles = [''] * len(row)
    if "在庫数" in row.index and row["在庫数"] < row["アラート基準"]:
        return ['background-color: #d9534f; color: white'] * len(row)
    return styles

# データ準備
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)
df_stock, df_log = process_reservations(df_stock, sha_stock, df_log, sha_log)

# --- 3. サイドバー ---
with st.sidebar:
    st.header("✨ 新規商品登録")
    n_item = st.text_input("商品名", key="s_n_item")
    n_size = st.selectbox("サイズ", SIZES_MASTER, key="s_n_size")
    n_loc = st.text_input("地名", key="s_n_loc")
    n_vendor = st.selectbox("取引先", VENDORS_MASTER, key="s_n_vendor")
    n_stock = st.number_input("初期在庫", min_value=0, value=0, key="s_n_stock")
    n_alert = st.number_input("アラート基準", min_value=0, value=5, key="s_n_alert")
    if st.button("登録実行", use_container_width=True, type="primary"):
        if n_item and n_loc:
            now = get_now_jst()
            new_row = pd.DataFrame([{"最終更新日": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "在庫数": n_stock, "アラート基準": n_alert, "取引先": n_vendor}])
            update_github_data(FILE_PATH_STOCK, pd.concat([df_stock, new_row], ignore_index=True), sha_stock, "Add")
            st.rerun()

# --- 4. メイン ---
st.title("📦 在庫管理")

c1, c2, c3 = st.columns(3)
with c1: s_item = st.selectbox("商品名", get_opts(df_stock["商品名"]), key="f_item")
with c2: s_size = st.selectbox("サイズ", get_opts(df_stock["サイズ"]), key="f_size")
with c3: s_loc = st.text_input("地名検索", placeholder="キーワード", key="f_loc")

df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc.strip(): df_disp = df_disp[df_disp["地名"].astype(str).str.contains(s_loc, na=False)]

# 一覧表示（必要な項目のみに絞り込み）
disp_cols = ["商品名", "サイズ", "地名", "在庫数", "アラート基準"]
df_show = df_disp[disp_cols].sort_values("商品名")
styled_df = df_show.style.apply(highlight_alert, axis=1)

event = st.dataframe(
    styled_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row",
    column_config={"在庫数": st.column_config.NumberColumn("在庫", format="%d")}
)

# --- 5. 操作パネル ---
st.divider()
selected_indices = event.selection.rows
if selected_indices:
    selected_data_list = df_show.iloc[selected_indices]
    st.markdown(f"### 📋 {len(selected_data_list)} 件の操作")
    user_name = st.selectbox("担当者", ["-- 選択 --"] + USERS)
    
    if user_name != "-- 選択 --":
        update_payload = {}
        for i, row in selected_data_list.iterrows():
            with st.expander(f"📌 {row['商品名']} ({row['サイズ']} / {row['地名']})", expanded=True):
                col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1.2, 1, 0.6])
                with col1: m_type = st.radio("区分", ["入庫", "出庫", "予約出庫", "変更なし"], horizontal=True, key=f"t_{i}")
                with col2: m_qty = st.number_input("数量", min_value=0, key=f"q_{i}")
                with col3:
                    if m_type == "予約出庫":
                        res_date = st.date_input("予約日", value=dt.date.today() + dt.timedelta(days=1), key=f"d_{i}")
                    else:
                        new_loc = st.text_input("地名変更", value=row['地名'], key=f"l_{i}")
                with col4: new_alt = st.number_input("基準", min_value=0, value=int(row['アラート基準']), key=f"a_{i}")
                with col5: is_del = st.checkbox("削除", key=f"del_{i}")
                update_payload[i] = {"type": m_type, "qty": m_qty, "loc": new_loc if m_type != "予約出庫" else row['地名'], "alert": new_alt, "delete": is_del, "res_date": res_date if m_type == "予約出庫" else None, "orig_data": row}

        if st.button("🔄 確定", type="primary", use_container_width=True):
            now = get_now_jst()
            new_res = []
            for idx, p in update_payload.items():
                row = p["orig_data"]
                mask = (df_stock["商品名"] == row["商品名"]) & (df_stock["サイズ"] == row["サイズ"]) & (df_stock["地名"] == row["地名"])
                if mask.any():
                    oidx = df_stock[mask].index[0]
                    if p["delete"]: df_stock = df_stock.drop(oidx)
                    elif p["type"] == "予約出庫" and p["qty"] > 0:
                        new_res.append({"予約日": p["res_date"], "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": row["地名"], "数量": p["qty"], "担当者": user_name})
                    elif p["type"] != "変更なし":
                        if p["type"] == "入庫": df_stock.at[oidx, "在庫数"] += p["qty"]
                        elif p["type"] == "出庫": df_stock.at[oidx, "在庫数"] -= p["qty"]
                        df_stock.at[oidx, "地名"], df_stock.at[oidx, "アラート基準"], df_stock.at[oidx, "最終更新日"] = p["loc"], p["alert"], now
            update_github_data(FILE_PATH_STOCK, df_stock, sha_stock, "Update")
            if new_res:
                df_res_old, sha_res = get_github_data(FILE_PATH_RESERVATION)
                update_github_data(FILE_PATH_RESERVATION, pd.concat([df_res_old, pd.DataFrame(new_res)], ignore_index=True), sha_res, "Add Res")
            st.rerun()

# --- 6. 予約リスト ---
st.divider()
st.subheader("📅 出庫予約リスト")
df_rv, sha_rv = get_github_data(FILE_PATH_RESERVATION)
if not df_rv.empty:
    df_rv["予約日"] = pd.to_datetime(df_rv["予約日"]).dt.date
    res_sel = st.dataframe(df_rv.sort_values("予約日"), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row")
    if res_sel.selection.rows:
        if st.button("🗑️ 選択した予約を取消"):
            update_github_data(FILE_PATH_RESERVATION, df_rv.drop(df_rv.index[res_sel.selection.rows]), sha_rv, "Del Res")
            st.rerun()
