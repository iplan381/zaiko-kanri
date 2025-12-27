import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 設定：ファイル名を固定 ---
STOCK_FILE = "inventory_main.csv"
LOG_FILE = "stock_log_main.csv"

USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

# ファイル初期化
if not os.path.exists(STOCK_FILE):
    pd.DataFrame(
        columns=[
            "最終更新日",
            "商品名",
            "サイズ",
            "地名",
            "在庫数",
            "アラート基準",
            "取引先",
        ]
    ).to_csv(STOCK_FILE, index=False)
if not os.path.exists(LOG_FILE):
    pd.DataFrame(
        columns=[
            "日時",
            "商品名",
            "サイズ",
            "地名",
            "変動",
            "担当者",
            "区分",
            "詳細・出荷先",
        ]
    ).to_csv(LOG_FILE, index=False)

df_stock = pd.read_csv(STOCK_FILE)
df_log = pd.read_csv(LOG_FILE)

st.set_page_config(page_title="在庫管理", layout="wide")
st.title("📦 在庫管理")

# --- サイドバー：登録・削除 ---
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
            new_data = pd.DataFrame(
                [[now, new_item, new_size, new_loc, new_stock, new_alert, new_vendor]],
                columns=df_stock.columns,
            )
            new_data.to_csv(STOCK_FILE, index=False, mode="a", header=False)
            st.success("登録しました")
            st.rerun()

    st.divider()
    if not df_stock.empty:
        st.header("🗑 商品の削除")
        target = st.selectbox(
            "削除対象の商品",
            df_stock.apply(
                lambda x: f"{x['商品名']}|{x['サイズ']}|{x['地名']}", axis=1
            ),
        )
        if st.button("商品を削除"):
            i, s, l = target.split("|")
            df_stock = df_stock[
                ~(
                    (df_stock["商品名"] == i)
                    & (df_stock["サイズ"] == s)
                    & (df_stock["地名"] == l)
                )
            ]
            df_stock.to_csv(STOCK_FILE, index=False)
            st.rerun()

    st.divider()
    if not df_log.empty:
        st.header("📜 履歴の削除")
        # 履歴を新しい順に並べて、特定しやすいように情報を連結
        df_log_sort = df_log.sort_values("日時", ascending=False)
        target_log = st.selectbox(
            "削除する履歴を選択",
            df_log_sort.apply(
                lambda x: f"{x['日時']} | {x['商品名']}({x['サイズ']}) | {x['変動']} | {x['担当者']}",
                axis=1,
            ),
        )
        if st.button("履歴を削除"):
            # 日時をキーにして削除（日時は秒まで含んでいるため、重複の可能性は低いです）
            t_time = target_log.split(" | ")[0]
            df_log = df_log[df_log["日時"] != t_time]
            df_log.to_csv(LOG_FILE, index=False)
            st.warning("履歴を削除しました")
            st.rerun()

# --- メイン：在庫一覧 ---
st.subheader("📊 在庫一覧")


def get_opts(series):
    return (
        ["すべて"] + sorted(series.unique().tolist())
        if not series.empty
        else ["すべて"]
    )


c1, c2, c3, c4 = st.columns(4)
with c1:
    s_item = st.selectbox("商品名", get_opts(df_stock["商品名"]))
with c2:
    s_size = st.selectbox("サイズ", get_opts(df_stock["サイズ"]))
with c3:
    s_loc = st.selectbox("地名", get_opts(df_stock["地名"]))
with c4:
    s_vendor = st.selectbox("取引先", get_opts(df_stock["取引先"]))

df_disp = df_stock.copy()
if s_item != "すべて":
    df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて":
    df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc != "すべて":
    df_disp = df_disp[df_disp["地名"] == s_loc]
if s_vendor != "すべて":
    df_disp = df_disp[df_disp["取引先"] == s_vendor]


def highlight(row):
    if row["在庫数"] <= row["アラート基準"]:
        return ["background-color: #FF0000; color: white; font-weight: bold"] * len(row)
    return [""] * len(row)


df_disp = df_disp.sort_values(["地名", "商品名"])
selection = st.dataframe(
    df_disp.style.apply(highlight, axis=1),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# --- 入出庫フォーム ---
st.divider()
selected_rows = selection.get("selection", {}).get("rows", [])

if selected_rows:
    target_data = df_disp.iloc[selected_rows[0]]
    st.subheader(f"📥 更新: {target_data['商品名']} ({target_data['サイズ']})")

    with st.form("up_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            val = st.number_input("数量増減 (+/-)", step=1)
            user = st.selectbox("担当者", USERS)
        with col_b:
            dest = st.selectbox(
                "詳細", ["-", "店舗A", "店舗B", "EC倉庫", "返品", "廃棄"]
            )
            note = st.text_input("備考")

        if st.form_submit_button("在庫を更新する"):
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            # 在庫更新
            mask = (
                (df_stock["商品名"] == target_data["商品名"])
                & (df_stock["サイズ"] == target_data["サイズ"])
                & (df_stock["地名"] == target_data["地名"])
            )
            df_stock.loc[mask, "在庫数"] += val
            df_stock.loc[mask, "最終更新日"] = now_str
            df_stock.to_csv(STOCK_FILE, index=False)

            # ログ保存（秒まで記録して削除の際の一意性を高める）
            log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pd.DataFrame(
                [
                    [
                        log_time,
                        target_data["商品名"],
                        target_data["サイズ"],
                        target_data["地名"],
                        val,
                        user,
                        "更新",
                        dest,
                    ]
                ],
                columns=pd.read_csv(LOG_FILE).columns,
            ).to_csv(LOG_FILE, index=False, mode="a", header=False)
            st.success("更新完了")
            st.rerun()
else:
    st.info("💡 上の表の行をクリックすると、入出庫フォームが表示されます。")

# --- 履歴セクション ---
st.divider()
st.subheader("📜 入出庫履歴")

if not df_log.empty:
    lc1, lc2, lc3, lc4 = st.columns(4)
    with lc1:
        l_f_item = st.selectbox(
            "商品名で履歴検索", get_opts(df_log["商品名"]), key="l_item"
        )
    with lc2:
        l_f_loc = st.selectbox("地名で履歴検索", get_opts(df_log["地名"]), key="l_loc")
    with lc3:
        l_f_size = st.selectbox(
            "サイズで履歴検索", get_opts(df_log["サイズ"]), key="l_size"
        )
    with lc4:
        l_f_user = st.selectbox("担当者で履歴検索", ["すべて"] + USERS, key="l_user")

    df_l_f = df_log.copy()
    if l_f_item != "すべて":
        df_l_f = df_l_f[df_l_f["商品名"] == l_f_item]
    if l_f_loc != "すべて":
        df_l_f = df_l_f[df_l_f["地名"] == l_f_loc]
    if l_f_size != "すべて":
        df_l_f = df_l_f[df_l_f["サイズ"] == l_f_size]
    if l_f_user != "すべて":
        df_l_f = df_l_f[df_l_f["担当者"] == l_f_user]

    st.dataframe(
        df_l_f.sort_values("日時", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.write("履歴はまだありません。")
