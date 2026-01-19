import streamlit as st
import pandas as pd
import datetime as dt 
import base64
import requests
import time
from io import StringIO

# --- 0. 基本関数 ---
def get_now_jst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")

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

# --- 2. GitHub連携関数 ---
def get_github_data(file_path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}?t={time.time_ns()}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Cache-Control": "no-cache"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        df = pd.read_csv(StringIO(csv_text), dtype=str)
        return df.fillna(""), content["sha"]
    return pd.DataFrame(), None

def update_github_data(file_path, df, message):
    _, latest_sha = get_github_data(file_path)
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    for col in ["在庫数", "アラート基準", "数量"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    csv_content = df.to_csv(index=False)
    data = {"message": message, "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"), "sha": latest_sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code in [200, 201]

# --- 3. データの読み込みと「自動出庫」処理 ---
df_stock, _ = get_github_data(FILE_PATH_STOCK)
df_log, _ = get_github_data(FILE_PATH_LOG)
df_res_all, _ = get_github_data(FILE_PATH_RESERVATION)

# 型変換
def to_int(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    return df

df_stock = to_int(df_stock, ["在庫数", "アラート基準"])
df_log = to_int(df_log, ["数量", "在庫数"])
df_res_all = to_int(df_res_all, ["数量"])

# 🔥 【重要】予約自動実行ロジック
if not df_res_all.empty:
    today_str = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d")
    # 今日以前の予約を抽出
    expired_res = df_res_all[df_res_all["予約日"] <= today_str]
    
    if not expired_res.empty:
        st.info(f"📢 予約期限が来たデータを自動出庫処理しています... ({len(expired_res)}件)")
        now = get_now_jst()
        temp_stock = df_stock.copy()
        new_logs = []
        
        for idx, r_row in expired_res.iterrows():
            mask = (temp_stock["商品名"]==r_row["商品名"]) & (temp_stock["サイズ"]==r_row["サイズ"]) & (temp_stock["地名"]==r_row["地名"])
            if mask.any():
                oidx = temp_stock[mask].index[0]
                temp_stock.at[oidx, "在庫数"] -= int(r_row["数量"])
                temp_stock.at[oidx, "最終更新日"] = now
                new_logs.append({
                    "日時": now, "商品名": r_row["商品名"], "サイズ": r_row["サイズ"], "地名": r_row["地名"],
                    "区分": "出庫(自動予約実行)", "数量": r_row["数量"], "在庫数": int(temp_stock.at[oidx, "在庫数"]), "担当者": r_row["担当者"]
                })
        
        # 実行済みの予約を削除
        new_res_df = df_res_all.drop(expired_res.index)
        
        # 保存実行
        if update_github_data(FILE_PATH_STOCK, temp_stock, "Auto Stock Update (Res)"):
            update_github_data(FILE_PATH_LOG, pd.concat([df_log, pd.DataFrame(new_logs)], ignore_index=True), "Auto Log Update (Res)")
            update_github_data(FILE_PATH_RESERVATION, new_res_df, "Auto Res Delete")
            st.success("予約の自動処理が完了しました。")
            st.rerun()

# --- 4. メイン画面表示 (以下、以前の表示ロジックを維持) ---
st.title("📦 在庫管理システム")

def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("検索:商品名", get_opts(df_stock["商品名"]))
with c2: s_size = st.selectbox("検索:サイズ", get_opts(df_stock["サイズ"]))
with c3: search_loc = st.text_input("検索:地名（手入力）", placeholder="例: 青森")
with c4: s_vendor = st.selectbox("検索:取引先", get_opts(df_stock["取引先"]))

# 有効在庫計算（自動処理後の最新データで計算）
df_disp = df_stock.copy()
if not df_res_all.empty:
    for df in [df_disp, df_res_all]:
        for col in ["商品名", "サイズ", "地名"]: df[col] = df[col].astype(str).str.strip()
    res_sum = df_res_all.groupby(["商品名", "サイズ", "地名"])["数量"].sum().reset_index().rename(columns={"数量": "予約計"})
    df_disp = pd.merge(df_disp, res_sum, on=["商品名", "サイズ", "地名"], how="left").fillna({"予約計": 0})
else:
    df_disp["予約計"] = 0

df_disp["有効在庫"] = (df_disp["在庫数"].astype(int) - df_disp["予約計"].astype(int)).astype(int)

# フィルタリング・表示
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if search_loc.strip(): df_disp = df_disp[df_disp["地名"].astype(str).str.contains(search_loc, na=False)]

df_show = df_disp[["最終更新日", "商品名", "サイズ", "地名", "在庫数", "予約計", "有効在庫", "アラート基準", "取引先"]].sort_values("最終更新日", ascending=False)
st.dataframe(df_show, use_container_width=True, hide_index=True)

# 予約一覧セクション（残っている未来の予約を表示）
st.divider()
st.subheader("📅 未来の予約一覧")
if not df_res_all.empty:
    st.dataframe(df_res_all.sort_values("予約日"), use_container_width=True, hide_index=True)
else:
    st.write("現在、予約はありません。")

# 履歴表示セクション
st.divider()
st.subheader("📜 入出庫履歴")
df_log_disp = df_log.copy()
df_log_disp["日時_dt"] = pd.to_datetime(df_log_disp["日時"], errors='coerce', format='mixed')
st.dataframe(df_log_disp.dropna(subset=["日時_dt"]).sort_values("日時_dt", ascending=False), use_container_width=True, hide_index=True)
