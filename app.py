import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 設定：GoogleスプレッドシートのURL ---
# あなたのスプレッドシートURL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1n1Pjb0DMZfONEa0EMnixLwex1QEQgzbym8FmLs8HRD4/edit#gid=0"

# マスターデータの設定（必要に応じて書き換えてください）
USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし", "特大", "極小", "込"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

st.set_page_config(page_title="在庫管理システム", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- データ読み込み関数 ---
def load_data():
    # スプレッドシートから最新データを取得
    df_s = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="stock", ttl="0s")
    df_l = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="log", ttl="0s")
    return df_s.fillna(""), df_l.fillna("")

# --- 五十音順に並び替える関数 ---
def get_opts(series):
    if series is None or len(series) == 0:
        return ["すべて"]
    # 重複排除 -> 文字列化 -> ソート
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

# データの読み込み
df_stock, df_log = load_data()

st.title("📦 在庫管理")

# --- サイドバー：新商品登録 ---
with st.sidebar:
    st.header("✨ 新商品登録")
    new_item = st.text_input("商品名")
    new_size = st.selectbox("サイズ", SIZES_MASTER)
    new_loc = st.text_input("地名")
    new_vendor = st.selectbox("取引先", VENDORS_MASTER)
    new_stock = st.number_input("初期在庫", min_value=0, value=0)
    new_alert = st.number_input("アラート基準", min_value=0, value=5)

    if st.button("登録"):
        if new_item and new_loc:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_row = pd.DataFrame([{
                "最終更新日": now, "商品名": new_item, "サイズ": new_size,
                "地名": new_loc, "在庫数": new_stock, "アラート基準": new_alert, "取引先": new_vendor
            }])
            updated_stock = pd.concat([df_stock, new_row], ignore_index=True)
            conn.update(spreadsheet=SPREADSHEET_URL, worksheet="stock", data=updated_stock)
            st.success("スプレッドシートへ登録完了")
            st.rerun()
        else:
            st.error("商品名と地名は必須です")

    st.divider()
    # 商品削除機能
    if not df_stock.empty:
        st.header("🗑 商品の削除")
        target = st.selectbox(
            "削除対象",
            df_stock.apply(lambda x: f"{x['商品名']}|{x['サイズ']}|{x['地名']}", axis=1)
        )
        if st.button("商品を削除"):
            i, s, l = target.split("|")
            df_stock = df_stock[~((df_stock["商品名"] == i) & (df_stock["サイズ"] == s) & (df_stock["地名"] == l))]
            conn.update(spreadsheet=SPREADSHEET_URL, worksheet="stock", data=df_stock)
            st.rerun()

# --- メイン：在庫一覧（絞り込み） ---
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)
with c1:
    s_item = st.selectbox("商品名", get_opts(df_stock["商品名"]))
with c2:
    s_size = st.selectbox("サイズ", get_opts(df_stock["サイズ"]))
with c3:
    # ここであいうえお順に並びます
    s_loc = st.selectbox("地名", get_opts(df_stock["地名"]))
with c4:
    s_vendor = st.selectbox("取引先", get_opts(df_stock["取引先"]))

df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc != "すべて": df_disp = df_disp[df_disp["地名"] == s_loc]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

# アラートのハイライト
def highlight(row):
    if float(row["在庫数"]) <= float(row["アラート基準"]):
        return ["background-color: #FF0000; color: white; font-weight: bold"] * len(row)
    return [""] * len(row)

# テーブル表示（クリック選択可能）
df_disp = df_disp.sort_values(["地名", "商品名"])
selection = st.dataframe(
    df_disp.style.apply(highlight, axis=1),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# --- 入出庫フォーム（クリックで出現） ---
st.divider()
selected_rows = selection.get("selection", {}).get("rows", [])
if selected_rows:
    target_data = df_disp.iloc[selected_rows[0]]
    st.subheader(f"📥 更新: {target_data['商品名']} ({target_data['サイズ']}) - {target_data['地名']}")

    with st.form("up_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            val = st.number_input("数量増減 (+/-)", step=1)
            user = st.selectbox("担当者", USERS)
        with col_b:
            dest = st.text_input("詳細・出荷先", value="-")
            note = st.selectbox("区分", ["更新", "入庫", "出庫", "棚卸"])

        if st.form_submit_button("在庫を更新して保存"):
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            # 在庫更新ロジック
            mask = (df_stock["商品名"] == target_data["商品名"]) & \
                   (df_stock["サイズ"] == target_data["サイズ"]) & \
                   (df_stock["地名"] == target_data["地名"])
            
            df_stock.loc[mask, "在庫数"] = pd.to_numeric(df_stock.loc[mask, "在庫数"]) + val
            df_stock.loc[mask, "最終更新日"] = now_str
            
            # ログ作成
            new_log = pd.DataFrame([{
                "日時": now_str, "商品名": target_data["商品名"], "サイズ": target_data["サイズ"],
                "地名": target_data["地名"], "変動": val, "担当者": user, "区分": note, "詳細・出荷先": dest
            }])
            updated_log = pd.concat([df_log, new_log], ignore_index=True)

            # スプレッドシート更新
            conn.update(spreadsheet=SPREADSHEET_URL, worksheet="stock", data=df_stock)
            conn.update(spreadsheet=SPREADSHEET_URL, worksheet="log", data=updated_log)
            
            st.success("スプレッドシートを更新しました！")
            st.rerun()
else:
    st.info("💡 上の表の行をクリックすると、入出庫フォームが表示されます。")

# --- 履歴セクション ---
st.divider()
st.subheader("📜 入出庫履歴")
if not df_log.empty:
    st.dataframe(df_log.sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
