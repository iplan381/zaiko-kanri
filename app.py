import streamlit as st
import pandas as pd
import datetime as dt 
import base64
import requests
import time
from io import StringIO

# --- 0. 基本関数 ---
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

# --- 2. GitHub連携関数 (キャッシュ・エラー対策版) ---
def get_github_data(file_path):
    # 強力なキャッシュ回避
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}?t={int(time.time())}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Cache-Control": "no-cache"
    }
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
    
    # 保存前に数値を整数に固定（小数点を消す）
    for col in ["在庫数", "アラート基準", "数量"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
    csv_content = df.to_csv(index=False)
    data = {
        "message": message,
        "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"),
        "sha": latest_sha
    }
    res = requests.put(url, headers=headers, json=data)
    return res.status_code in [200, 201]

# データ読み込みと整数化
df_stock, _ = get_github_data(FILE_PATH_STOCK)
df_log, _ = get_github_data(FILE_PATH_LOG)
df_res_all, _ = get_github_data(FILE_PATH_RESERVATION)

def to_int(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    return df

df_stock = to_int(df_stock, ["在庫数", "アラート基準"])
df_log = to_int(df_log, ["数量", "在庫数"])
df_res_all = to_int(df_res_all, ["数量"])

def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

def highlight_alert(row):
    if "有効在庫" in row.index and row["有効在庫"] < row["アラート基準"]:
        return ['background-color: #d9534f; color: white'] * len(row)
    return [''] * len(row)

# --- 3. サイドバー：新規登録 ---
with st.sidebar:
    st.header("✨ 新規商品登録")
    n_item = st.text_input("商品名")
    n_size = st.selectbox("サイズ", SIZES_MASTER)
    n_loc = st.text_input("地名")
    n_vendor = st.selectbox("取引商社", VENDORS_MASTER)
    n_stock = st.number_input("初期在庫", min_value=0, value=0)
    n_alert = st.number_input("アラート基準", min_value=0, value=5)
    
    if st.button("新規登録実行", use_container_width=True, type="primary"):
        if n_item and n_loc:
            now = get_now_jst()
            new_row = pd.DataFrame([{"最終更新日": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "在庫数": int(n_stock), "アラート基準": int(n_alert), "取引先": n_vendor}])
            new_log = pd.DataFrame([{"日時": now, "商品名": n_item, "サイズ": n_size, "地名": n_loc, "区分": "新規登録", "数量": int(n_stock), "在庫数": int(n_stock), "担当者": "システム"}])
            if update_github_data(FILE_PATH_STOCK, pd.concat([df_stock, new_row], ignore_index=True), "Add Item") and \
               update_github_data(FILE_PATH_LOG, pd.concat([df_log, new_log], ignore_index=True), "Add Log"):
                st.success("登録完了！")
                st.rerun()

# --- 4. メイン：在庫一覧 ---
st.title("📦 在庫管理システム")

c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("検索:商品名", get_opts(df_stock["商品名"]))
with c2: s_size = st.selectbox("検索:サイズ", get_opts(df_stock["サイズ"]))
with c3: search_loc = st.text_input("検索:地名（手入力）", placeholder="例: 青森")
with c4: s_vendor = st.selectbox("検索:取引先", get_opts(df_stock["取引先"]))

df_disp = df_stock.copy()
if not df_res_all.empty:
    res_sum = df_res_all.groupby(["商品名", "サイズ", "地名"])["数量"].sum().reset_index().rename(columns={"数量": "予約計"})
    df_disp = pd.merge(df_disp, res_sum, on=["商品名", "サイズ", "地名"], how="left").fillna({"予約計": 0})
else:
    df_disp["予約計"] = 0

df_disp["有効在庫"] = (df_disp["在庫数"] - df_disp["予約計"]).astype(int)

if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if search_loc.strip(): df_disp = df_disp[df_disp["地名"].astype(str).str.contains(search_loc, na=False)]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

df_show = df_disp[["最終更新日", "商品名", "サイズ", "地名", "在庫数", "有効在庫", "アラート基準", "取引先"]].sort_values("最終更新日", ascending=False)

event = st.dataframe(
    df_show.style.apply(highlight_alert, axis=1),
    use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row",
    column_config={
        "在庫数": st.column_config.NumberColumn("実在庫", format="%d"),
        "有効在庫": st.column_config.NumberColumn("有効在庫", format="%d")
    }
)

# --- 5. 操作パネル (ダイアログ表示修正) ---
st.divider()
selected_indices = event.selection.rows
if selected_indices:
    selected_data = df_show.iloc[selected_indices]
    st.markdown(f"### 📋 {len(selected_data)} 件を一括操作")
    user_name = st.selectbox("担当者を選んでください", ["-- 選択 --"] + USERS)
    
    if user_name != "-- 選択 --":
        update_payload = {}
        for i, row in selected_data.iterrows():
            with st.expander(f"📌 {row['商品名']} ({row['サイズ']}/{row['地名']})", expanded=True):
                col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1.2, 1, 0.6])
                with col1: m_type = st.radio("区分", ["入庫", "出庫", "予約出庫", "調整"], horizontal=True, key=f"t_{i}")
                with col2: m_qty = st.number_input("数量", value=0, key=f"q_{i}", step=1)
                with col3:
                    if m_type == "予約出庫":
                        res_d = st.date_input("予約日", value=dt.date.today()+dt.timedelta(days=1), key=f"d_{i}")
                        new_l = row['地名']
                    else:
                        new_l = st.text_input("地名変更", value=row['地名'], key=f"l_{i}")
                with col4: new_a = st.number_input("アラート", min_value=0, value=int(row['アラート基準']), key=f"a_{i}", step=1)
                with col5: is_del = st.checkbox("削除", key=f"del_{i}")
                update_payload[i] = {"type": m_type, "qty": int(m_qty), "loc": new_l, "alert": int(new_a), "delete": is_del, "res_date": res_d if m_type=="予約出庫" else None, "orig": row}

        if st.button("🔄 全ての変更を確定する", type="primary", use_container_width=True):
            st.session_state.current_payload = update_payload
            
            @st.dialog("最終確認")
            def confirm_dialog():
                payloads = st.session_state.get('current_payload', {})
                st.warning("以下の内容で保存します。")
                for idx, p in payloads.items():
                    act = "🗑️ 削除" if p['delete'] else f"📦 {p['type']} ({p['qty']})"
                    st.write(f"・**{p['orig']['商品名']}** ({p['orig']['サイズ']}/{p['loc']}) → {act}")
                
                if st.button("はい、確定します", type="primary", use_container_width=True):
                    now, new_l_list, new_r_list = get_now_jst(), [], []
                    temp_stock = df_stock.copy()
                    for idx, p in payloads.items():
                        mask = (temp_stock["商品名"]==p['orig']["商品名"]) & (temp_stock["サイズ"]==p['orig']["サイズ"]) & (temp_stock["地名"]==p['orig']["地名"])
                        if mask.any():
                            oidx = temp_stock[mask].index[0]
                            if p['delete']:
                                temp_stock = temp_stock.drop(oidx)
                                new_l_list.append({"日時": now, "商品名": p['orig']["商品名"], "サイズ": p['orig']["サイズ"], "地名": p['orig']["地名"], "区分": "削除", "数量": 0, "在庫数": 0, "担当者": user_name})
                            elif p['type'] == "予約出庫":
                                new_r_list.append({"予約日": str(p['res_date']), "商品名": p['orig']["商品名"], "サイズ": p['orig']["サイズ"], "地名": p['orig']["地名"], "数量": p['qty'], "担当者": user_name})
                            else:
                                if p['type'] in ["入庫", "調整"]: temp_stock.at[oidx, "在庫数"] += p['qty']
                                elif p['type'] == "出庫": temp_stock.at[oidx, "在庫数"] -= p['qty']
                                temp_stock.at[oidx, "地名"], temp_stock.at[oidx, "アラート基準"], temp_stock.at[oidx, "最終更新日"] = p["loc"], p["alert"], now
                                new_l_list.append({"日時": now, "商品名": p['orig']["商品名"], "サイズ": p['orig']["サイズ"], "地名": p['loc'], "区分": p['type'], "数量": p['qty'], "在庫数": int(temp_stock.at[oidx, "在庫数"]), "担当者": user_name})
                    
                    if update_github_data(FILE_PATH_STOCK, temp_stock, "Stock Update"):
                        if new_l_list: update_github_data(FILE_PATH_LOG, pd.concat([df_log, pd.DataFrame(new_l_list)], ignore_index=True), "Log Update")
                        if new_r_list:
                            d_r, _ = get_github_data(FILE_PATH_RESERVATION)
                            update_github_data(FILE_PATH_RESERVATION, pd.concat([d_r, pd.DataFrame(new_r_list)], ignore_index=True), "Res Update")
                        st.success("更新しました！")
                        st.rerun()
            confirm_dialog()
else:
    st.info("💡 一覧から商品を選択してください")

# --- 6. 履歴表示 (エラー対策版) ---
st.divider()
st.subheader("📜 入出庫履歴")
if not df_log.empty:
    df_l = df_log.copy()
    # errors='coerce' で、壊れた日付データがあってもクラッシュさせない
    df_l["日時_dt"] = pd.to_datetime(df_l["日時"], errors='coerce')
    df_l = df_l.dropna(subset=["日時_dt"]).sort_values("日時_dt", ascending=False)
    
    cl1, cl2, cl3 = st.columns(3)
    with cl1: l_item = st.selectbox("履歴:商品名", get_opts(df_l["商品名"]), key="l_i")
    with cl2: l_loc = st.selectbox("履歴:地名", get_opts(df_l["地名"]), key="l_l")
    with cl3: l_type = st.multiselect("区分", options=sorted(df_l["区分"].unique()), key="l_t")
    
    if l_item != "すべて": df_l = df_l[df_l["商品名"] == l_item]
    if l_loc != "すべて": df_l = df_l[df_l["地名"] == l_loc]
    if l_type: df_l = df_l[df_l["区分"].isin(l_type)]
    
    st.dataframe(
        df_l[["日時", "商品名", "サイズ", "地名", "区分", "数量", "在庫数", "担当者"]],
        use_container_width=True, hide_index=True,
        column_config={
            "数量": st.column_config.NumberColumn("数量", format="%d"),
            "在庫数": st.column_config.NumberColumn("在庫数", format="%d")
        }
    )
