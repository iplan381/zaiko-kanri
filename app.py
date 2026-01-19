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

# データ読み込み
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)
df_res_all, sha_res_all = get_github_data(FILE_PATH_RESERVATION)

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
res_sum = df_res_all.groupby(["商品名", "サイズ", "地名"])["数量"].sum().reset_index().rename(columns={"数量": "予約計"})
df_disp = pd.merge(df_disp, res_sum, on=["商品名", "サイズ", "地名"], how="left").fillna({"予約計": 0})
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
                    if m_type == "調整":
                        m_qty = st.number_input("数量", value=0, key=f"qty_{i}")
                    else:
                        m_qty = st.number_input("数量", min_value=0, value=0, key=f"qty_{i}")
                with col3:
                    if m_type == "予約出庫":
                        res_date = st.date_input("予約日", value=dt.date.today() + dt.timedelta(days=1), key=f"date_{i}")
                        new_loc = row['地名']
                    else:
                        new_loc = st.text_input("地名変更", value=row['地名'], key=f"loc_{i}")
                with col4: new_alert = st.number_input("アラート基準", min_value=0, value=int(row['アラート基準']), key=f"alt_{i}")
                with col5: is_delete = st.checkbox("削除", key=f"del_{i}")
                update_payload[i] = {"type": m_type, "qty": m_qty, "loc": new_loc, "alert": new_alert, "delete": is_delete, "res_date": res_date if m_type == "予約出庫" else None, "orig_data": row}

        # --- 確認ダイアログ ---
        if st.button("🔄 全ての変更を確定する", type="primary", use_container_width=True):
            @st.dialog("変更内容の最終確認")
            def confirm_dialog(payloads):
                st.warning("⚠️ 以下の内容で更新します。間違いありませんか？")
                for idx, p in payloads.items():
                    if p['delete']:
                        action_str = "🗑️ 【削除】"
                    elif p['type'] == "予約出庫":
                        action_str = f"📅 【予約】 {p['qty']}c/s ({p['res_date']})"
                    else:
                        action_str = f"📦 【{p['type']}】 {p['qty']}c/s"
                    
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
                                new_reservations.append({"予約日": p["res_date"], "商品名": row["商品名"], "サイズ": row["サイズ"], "地名": row["地名"], "数量": p["qty"], "担当者": user_name})
                            else:
                                if p["type"] == "入庫" or p["type"] == "調整":
                                    temp_df_stock.at[orig_idx, "在庫数"] += p["qty"]
                                elif p["type"] == "出庫":
                                    temp_df_stock.at[orig_idx, "在庫数"] -= p["qty"]
                                
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
    res_sum_all = df_res_all.groupby(["商品名", "サイズ", "地名"])["数量"].sum().reset_index().rename(columns={"数量": "予約計"})
    all_stocks = pd.merge(df_stock, res_sum_all, on=["商品名", "サイズ", "地名"], how="left").fillna({"予約計": 0})
    all_stocks["有効在庫"] = all_stocks["在庫数"] - all_stocks["予約計"]

    df_rv = pd.merge(df_res_all, all_stocks[["商品名", "サイズ", "地名", "在庫数", "有効在庫"]], on=["商品名", "サイズ", "地名"], how="left").fillna({"在庫数": 0, "有効在庫": 0})
    
    res_filter_item = st.selectbox("予約検索:商品名", get_opts(df_rv["商品名"]), key="res_f_item")
    if res_filter_item != "すべて":
        df_rv = df_rv[df_rv["商品名"] == res_filter_item]

    df_rv["予約日"] = pd.to_datetime(df_rv["予約日"]).dt.date
    res_disp_cols = ["予約日", "商品名", "サイズ", "地名", "数量", "在庫数", "有効在庫", "担当者"]

    res_event = st.dataframe(
        df_rv[res_disp_cols].sort_values("予約日"), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row",
        column_config={
            "予約日": st.column_config.DateColumn("予約日", format="YYYY-MM-DD"),
            "数量": st.column_config.NumberColumn("予約数", format="%d"),
            "在庫数": st.column_config.NumberColumn("実在庫", format="%d"),
            "有効在庫": st.column_config.NumberColumn("有効在庫", format="%d")
        }
    )
    
    selected_rows = res_event.selection.rows
    if selected_rows:
        st.markdown(f"#### ✍️ 選択中の予約 ({len(selected_rows)}件) を編集")
        df_target = df_rv.sort_values("予約日").iloc[selected_rows]
        res_updates = {}
        for i, row in df_target.iterrows():
            orig_idx = row.name
            with st.expander(f"予約: {row['商品名']} ({row['サイズ']} / {row['地名']})", expanded=True):
                c1, c2, c3 = st.columns([1.5, 1, 0.5])
                with c1: upd_date = st.date_input("予約日変更", value=row['予約日'], key=f"up_res_d_{orig_idx}")
                with c2: upd_qty = st.number_input("数量変更", min_value=1, value=int(row['数量']), key=f"up_res_q_{orig_idx}")
                with c3: is_res_del = st.checkbox("削除", key=f"up_res_del_{orig_idx}")
                res_updates[orig_idx] = {"date": upd_date, "qty": upd_qty, "delete": is_res_del}

        if st.button("✅ 予約の変更/削除を確定する", type="primary", use_container_width=True):
            new_df_res = df_res_all.copy()
            indices_to_drop = [o_idx for o_idx, val in res_updates.items() if val["delete"]]
            for o_idx, val in res_updates.items():
                if not val["delete"]:
                    new_df_res.at[o_idx, "予約日"] = str(val["date"])
                    new_df_res.at[o_idx, "数量"] = val["qty"]
            if indices_to_drop:
                new_df_res = new_df_res.drop(indices_to_drop)
            update_github_data(FILE_PATH_RESERVATION, new_df_res, sha_res_all, "Individual Res Update Fix")
            st.rerun()
else:
    st.write("現在予約はありません。")

st.divider()

# --- B. 入出庫履歴 ---
st.subheader("📜 入出庫履歴")

if not df_log.empty:
    # --- 修正: 読み込みデータのコピーを作成して表示用に加工する ---
    df_log_display = df_log.copy()
    
    # 全ての列を文字列に変換してから、空の行を削除（GitHub由来のゴミ対策）
    df_log_display = df_log_display.replace("", pd.NA).dropna(how='all')
    
    # 日時を表示用に変換（エラーは無視せず、不正なものはNaTにする）
    df_log_display["日時"] = pd.to_datetime(df_log_display["日時"], errors='coerce')
    
    # 万が一、日時の変換に失敗した行があれば削除（表示用のみ）
    df_log_display = df_log_display.dropna(subset=["日時"])

    # フィルター設置
    col_log1, col_log2, col_log3, col_log4, col_log5 = st.columns([1.5, 1.2, 1, 1, 1.2])
    
    with col_log1:
        min_date = df_log_display["日時"].min().date()
        max_date = df_log_display["日時"].max().date()
        log_date_range = st.date_input("期間", value=(min_date, max_date), key="log_date_filter")
    
    with col_log2:
        l_item = st.selectbox("履歴検索:商品名", get_opts(df_log_display["商品名"]), key="log_f_item")
    with col_log3:
        l_size = st.selectbox("履歴検索:サイズ", get_opts(df_log_display["サイズ"]), key="log_f_size")
    with col_log4:
        l_loc = st.selectbox("履歴検索:地名", get_opts(df_log_display["地名"]), key="log_f_loc")
    with col_log5:
        all_types = [t for t in sorted(df_log_display["区分"].unique()) if t not in ["基準変更", "編集"] and str(t).strip() != ""]
        selected_types = st.multiselect("区分", options=all_types, key="log_type_filter")

    # 絞り込み実行
    if isinstance(log_date_range, tuple) and len(log_date_range) == 2:
        df_log_display = df_log_display[(df_log_display["日時"].dt.date >= log_date_range[0]) & (df_log_display["日時"].dt.date <= log_date_range[1])]
    
    if l_item != "すべて": df_log_display = df_log_display[df_log_display["商品名"] == l_item]
    if l_size != "すべて": df_log_display = df_log_display[df_log_display["サイズ"] == l_size]
    if l_loc != "すべて": df_log_display = df_log_display[df_log_display["地名"] == l_loc]
    if selected_types:
        df_log_display = df_log_display[df_log_display["区分"].isin(selected_types)]

    # 表示
    disp_log_cols = ["日時", "商品名", "サイズ", "地名", "区分", "数量", "在庫数", "担当者"]
    st.dataframe(
        df_log_display[disp_log_cols].sort_values("日時", ascending=False),
        use_container_width=True, hide_index=True,
        column_config={
            "日時": st.column_config.DatetimeColumn("日時", format="YYYY-MM-DD HH:mm"),
            "数量": st.column_config.NumberColumn("数", format="%d"),
            "在庫数": st.column_config.NumberColumn("現在庫", format="%d")
        }
    )
