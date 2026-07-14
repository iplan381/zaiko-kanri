import streamlit as st
import pandas as pd
import datetime as dt

from github_data import get_github_data as _get_github_data, update_github_data


@st.cache_data(ttl=30)
def get_github_data(file_path, default_cols=None):
    return _get_github_data(file_path, default_cols=default_cols)


def get_now_jst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# --- 設定 ---
FILE_PATH_STOCK = "inventory_main.csv"
FILE_PATH_LOG = "stock_log_main.csv"
FILE_PATH_HAKUOSHI = "hakuoshi_log.csv"
FILE_PATH_SEIKAN = "seikan_log.csv"

HAKUOSHI_COLS = ["日時", "商品名", "サイズ", "地名", "枚数", "ミス数", "担当者"]
SEIKAN_COLS = ["日時", "商品名", "サイズ", "地名", "製函数", "ミス_フタ", "ミス_身", "担当者"]
USERS = ["佐藤", "中村", "手塚"]

st.set_page_config(page_title="製造記録（箔押し・製函）", layout="wide", page_icon="🏭")

with st.sidebar:
    st.markdown("### 🔗 クイック移動")
    c1, c2, c3 = st.columns(3)
    c1.link_button("📦 在庫管理", "https://zaiko-kanri.streamlit.app/")
    c2.link_button("📊 分析画面", "https://zaiko-kanri-f8bgjer2kscsa9ack7ervi.streamlit.app//")
    c3.link_button("🚚 発注管理", "https://zaiko-kanri-qzelakcnxralslk3ac27ex.streamlit.app/")
    st.divider()

# データ読み込み
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)
df_hakuoshi, sha_hakuoshi = get_github_data(FILE_PATH_HAKUOSHI, default_cols=HAKUOSHI_COLS)
df_seikan, sha_seikan = get_github_data(FILE_PATH_SEIKAN, default_cols=SEIKAN_COLS)

st.title("🏭 製造記録")


def get_stock_options(df, col, filters=None):
    sub = df
    if filters:
        for k, v in filters.items():
            sub = sub[sub[k] == v]
    return sorted([str(x) for x in sub[col].unique() if str(x).strip() != ""])


def item_picker(key_prefix):
    """商品名→サイズ→地名のカスケード選択。マスタ未登録の組み合わせは手入力に切替可。"""
    item_opts = get_stock_options(df_stock, "商品名")
    manual = st.checkbox(
        "リストにない組み合わせを入力する", key=f"{key_prefix}_manual", value=not item_opts
    )

    col1, col2, col3 = st.columns(3)
    if manual or not item_opts:
        if not item_opts:
            st.info("在庫管理システムにまだ商品が登録されていません。手入力してください。")
        with col1:
            item = st.text_input("商品名", key=f"{key_prefix}_item_manual")
        with col2:
            size = st.text_input("サイズ", key=f"{key_prefix}_size_manual")
        with col3:
            loc = st.text_input("地名", key=f"{key_prefix}_loc_manual")
        matched = False
    else:
        with col1:
            item = st.selectbox("商品名", item_opts, key=f"{key_prefix}_item_sel")
        size_opts = get_stock_options(df_stock, "サイズ", {"商品名": item})
        with col2:
            size = st.selectbox("サイズ", size_opts, key=f"{key_prefix}_size_sel") if size_opts else ""
        loc_opts = get_stock_options(df_stock, "地名", {"商品名": item, "サイズ": size}) if size else []
        with col3:
            loc = st.selectbox("地名", loc_opts, key=f"{key_prefix}_loc_sel") if loc_opts else ""
        matched = bool(item and size and loc)

    return item, size, loc, matched


def history_section(df, sha, file_path, disp_cols, title, delete_key):
    st.markdown(f"### 📜 {title}履歴")
    if df.empty:
        st.write("記録はまだありません。")
        return

    df_show = df.copy()
    df_show["日時"] = pd.to_datetime(df_show["日時"], errors="coerce")
    df_show = df_show.dropna(subset=["日時"]).sort_values("日時", ascending=False)

    item_opts = ["すべて"] + sorted(
        [str(x) for x in df_show["商品名"].unique() if str(x).strip() != ""]
    )
    f_item = st.selectbox("商品名で絞り込み", item_opts, key=f"{delete_key}_filter")
    if f_item != "すべて":
        df_show = df_show[df_show["商品名"] == f_item]

    df_show = df_show.head(100)
    df_show.insert(0, "削除", False)

    edited = st.data_editor(
        df_show,
        hide_index=True,
        use_container_width=True,
        disabled=disp_cols,
        column_config={"日時": st.column_config.DatetimeColumn("日時", format="YYYY-MM-DD HH:mm")},
        key=f"{delete_key}_editor",
    )

    to_delete = edited.index[edited["削除"] == True]
    if len(to_delete) > 0 and st.button(
        f"🗑 チェックした記録を削除（{len(to_delete)}件）",
        key=f"{delete_key}_delete_btn",
        type="secondary",
    ):
        new_df = df.drop(to_delete)
        if update_github_data(file_path, new_df, sha, f"Delete {title} Record") in (200, 201):
            st.cache_data.clear()
            st.success("削除しました")
            st.rerun()


PANEL_HEIGHT = 850

col_left, col_right = st.columns(2)

# --- 左側: 箔押し記録 ---
with col_left:
    with st.container(height=PANEL_HEIGHT, border=True):
        st.subheader("🖨 箔押し記録の登録")
        h_item, h_size, h_loc, _ = item_picker("h")

        col4, col5, col6 = st.columns(3)
        with col4:
            h_qty = st.number_input("箔押し枚数", min_value=0, value=0, key="h_qty")
        with col5:
            h_miss = st.number_input("ミス数", min_value=0, value=0, key="h_miss")
        with col6:
            h_user = st.selectbox("担当者", USERS, key="h_user")

        if st.button("✅ 箔押し記録を登録", type="primary", use_container_width=True, key="h_submit"):
            if h_item and h_size and h_loc:
                new_row = pd.DataFrame(
                    [
                        {
                            "日時": get_now_jst(),
                            "商品名": h_item,
                            "サイズ": h_size,
                            "地名": h_loc,
                            "枚数": h_qty,
                            "ミス数": h_miss,
                            "担当者": h_user,
                        }
                    ]
                )
                updated = pd.concat([df_hakuoshi, new_row], ignore_index=True)
                if update_github_data(
                    FILE_PATH_HAKUOSHI, updated, sha_hakuoshi, "Add Hakuoshi Record"
                ) in (200, 201):
                    st.cache_data.clear()
                    st.success("登録しました")
                    st.rerun()
            else:
                st.error("商品名・サイズ・地名を入力してください")

        st.divider()
        history_section(
            df_hakuoshi,
            sha_hakuoshi,
            FILE_PATH_HAKUOSHI,
            ["日時", "商品名", "サイズ", "地名", "枚数", "ミス数", "担当者"],
            "箔押し記録",
            "hakuoshi",
        )

# --- 右側: 製函記録 ---
with col_right:
    with st.container(height=PANEL_HEIGHT, border=True):
        st.subheader("📦 製函記録の登録")
        s_item, s_size, s_loc, s_matched = item_picker("s")

        col7, col8, col9, col10 = st.columns(4)
        with col7:
            s_qty = st.number_input("製函数（c/s）", min_value=0, value=0, key="s_qty")
        with col8:
            s_miss_futa = st.number_input("ミス数（フタ）", min_value=0, value=0, key="s_miss_futa")
        with col9:
            s_miss_mi = st.number_input("ミス数（身）", min_value=0, value=0, key="s_miss_mi")
        with col10:
            s_user = st.selectbox("担当者", USERS, key="s_user")

        if not s_matched:
            st.caption("※ 在庫マスタに一致する商品が無いため、在庫数への反映はスキップされます。")

        if st.button("✅ 製函記録を登録", type="primary", use_container_width=True, key="s_submit"):
            if s_item and s_size and s_loc:
                now = get_now_jst()
                new_row = pd.DataFrame(
                    [
                        {
                            "日時": now,
                            "商品名": s_item,
                            "サイズ": s_size,
                            "地名": s_loc,
                            "製函数": s_qty,
                            "ミス_フタ": s_miss_futa,
                            "ミス_身": s_miss_mi,
                            "担当者": s_user,
                        }
                    ]
                )
                updated_seikan = pd.concat([df_seikan, new_row], ignore_index=True)
                seikan_ok = update_github_data(
                    FILE_PATH_SEIKAN, updated_seikan, sha_seikan, "Add Seikan Record"
                ) in (200, 201)

                stock_reflected = False
                if seikan_ok and s_matched and s_qty > 0:
                    mask = (
                        (df_stock["商品名"] == s_item)
                        & (df_stock["サイズ"] == s_size)
                        & (df_stock["地名"] == s_loc)
                    )
                    if mask.any():
                        idx = df_stock[mask].index[0]
                        new_df_stock = df_stock.copy()
                        new_df_stock.at[idx, "在庫数"] += s_qty
                        new_df_stock.at[idx, "最終更新日"] = now
                        if update_github_data(
                            FILE_PATH_STOCK, new_df_stock, sha_stock, "Seikan Stock In"
                        ) in (200, 201):
                            new_log = pd.DataFrame(
                                [
                                    {
                                        "日時": now,
                                        "商品名": s_item,
                                        "サイズ": s_size,
                                        "地名": s_loc,
                                        "区分": "入庫(製函)",
                                        "数量": s_qty,
                                        "在庫数": new_df_stock.at[idx, "在庫数"],
                                        "担当者": s_user,
                                    }
                                ]
                            )
                            update_github_data(
                                FILE_PATH_LOG,
                                pd.concat([df_log, new_log], ignore_index=True),
                                sha_log,
                                "Seikan Stock Log",
                            )
                            stock_reflected = True

                if seikan_ok:
                    st.cache_data.clear()
                    if stock_reflected:
                        st.success("登録しました（在庫にも反映しました）")
                    else:
                        st.success("登録しました（在庫への反映はスキップされました）")
                    st.rerun()
            else:
                st.error("商品名・サイズ・地名を入力してください")

        st.divider()
        history_section(
            df_seikan,
            sha_seikan,
            FILE_PATH_SEIKAN,
            ["日時", "商品名", "サイズ", "地名", "製函数", "ミス_フタ", "ミス_身", "担当者"],
            "製函記録",
            "seikan",
        )
