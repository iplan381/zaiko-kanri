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
FILE_PATH_STAFF = "staff_master.csv"

HAKUOSHI_COLS = ["日時", "商品名", "サイズ", "地名", "枚数", "ミス数", "担当者"]
SEIKAN_COLS = [
    "日時",
    "商品名",
    "サイズ",
    "地名",
    "製函数",
    "ミス_フタ",
    "ミス_身",
    "担当者",
]
STAFF_COLS = ["区分", "担当者"]
DEFAULT_USERS = {
    "箔押し": ["佐藤", "中村"],
    "製函": ["佐藤", "佐野"],
}

st.set_page_config(
    page_title="製造記録（箔押し・製函）",
    layout="wide",
    page_icon="🏭",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&display=swap');

    :root {
        --note-desk: #eaf4fb;
        --note-cover: #bdeee4;
        --note-paper: #ffffff;
        --note-rule: #bfe0f2;
        --note-border: #bfe0ef;
        --note-ink: #22384a;
        /* 箔押しタブ（暖色・金箔をイメージ） */
        --note-desk-h: #fbead2;
        /* 製函タブ（寒色・段ボールの青みをイメージ） */
        --note-desk-s: #eaf4fb;
    }

    [data-testid="stAppViewContainer"] { background: var(--note-desk); }

    /* 箔押しタブ（1つ目）と製函タブ（2つ目）でページ背景の色味を少し変える。
       紙自体（--note-paper）は白のまま。表示中のタブパネルには hidden 属性が付かないことを利用する */
    [data-testid="stAppViewContainer"]:has([id$="-tabpanel-0"]:not([hidden])) {
        background: var(--note-desk-h) !important;
    }
    [data-testid="stAppViewContainer"]:has([id$="-tabpanel-1"]:not([hidden])) {
        background: var(--note-desk-s) !important;
    }

    [data-testid="stSidebar"] {
        background: var(--note-cover);
        border-right: 1px solid var(--note-border);
    }

    h1, h2, h3, [data-testid="stHeading"] {
        font-family: 'Klee One', sans-serif !important;
        color: var(--note-ink) !important;
    }

    [data-testid="stLayoutWrapper"][height="850px"] {
        background-color: var(--note-paper);
        background-image: repeating-linear-gradient(
            transparent 0px, transparent 31px, var(--note-rule) 32px
        );
        border: 1px solid var(--note-border) !important;
        border-radius: 10px !important;
        box-shadow: 2px 4px 10px rgba(0, 0, 0, 0.12);
        color: var(--note-ink);
    }

    /* パネル・サイドバーは常に明色固定の背景なので、OSのダークテーマでも文字色を強制的に読める色にする。
       ただしボタンの中身は対象から除外し、Streamlitのテーマ配色（背景とセットの文字色）をそのまま使わせる。
       ("color: revert" はブラウザによって挙動が割れるため使わない) */
    [data-testid="stLayoutWrapper"][height="850px"] p:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stLayoutWrapper"][height="850px"] label:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stLayoutWrapper"][height="850px"] span:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stLayoutWrapper"][height="850px"] [data-testid="stWidgetLabel"],
    [data-testid="stLayoutWrapper"][height="850px"] [data-testid="stMarkdownContainer"]:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stLayoutWrapper"][height="850px"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] p:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stSidebar"] label:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stSidebar"] span:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:not([data-testid="stButton"] *):not([data-testid="stLinkButton"] *),
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--note-ink) !important;
    }

    /* タブは常に明るい背景（--note-desk）の上に乗るので、テーマに関係なく文字色を固定する */
    [data-testid="stTab"] p,
    [data-testid="stTab"] [data-testid="stMarkdownContainer"] {
        color: var(--note-ink) !important;
        font-family: 'Klee One', sans-serif !important;
    }

    hr { border: none; border-top: 2px dashed var(--note-border); }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 🔗 クイック移動")
    c1, c2, c3 = st.columns(3)
    c1.link_button("📦 在庫管理", "https://zaiko-kanri.streamlit.app/")
    c2.link_button(
        "📊 分析画面", "https://zaiko-kanri-f8bgjer2kscsa9ack7ervi.streamlit.app/"
    )
    c3.link_button(
        "🚚 発注管理", "https://zaiko-kanri-qzelakcnxralslk3ac27ex.streamlit.app/"
    )
    st.divider()

    def _calc_apply(a, b, op):
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "×":
            return a * b
        if op == "÷":
            return a / b if b != 0 else float("nan")
        return b

    def _calc_fmt(value):
        if value != value:  # NaN
            return "エラー"
        value = round(value, 6)
        if value == int(value):
            return str(int(value))
        return str(value)

    def _calc_press(key):
        disp = st.session_state.calc_display
        if key.isdigit():
            if st.session_state.calc_new_entry or disp in ("0", "エラー"):
                st.session_state.calc_display = key
            else:
                st.session_state.calc_display = disp + key
            st.session_state.calc_new_entry = False
        elif key == ".":
            if st.session_state.calc_new_entry or disp == "エラー":
                st.session_state.calc_display = "0."
                st.session_state.calc_new_entry = False
            elif "." not in disp:
                st.session_state.calc_display = disp + "."
        elif key == "C":
            st.session_state.calc_display = "0"
            st.session_state.calc_prev = None
            st.session_state.calc_op = None
            st.session_state.calc_new_entry = False
        elif key in ("+", "-", "×", "÷"):
            current = float(st.session_state.calc_display)
            if (
                st.session_state.calc_prev is not None
                and not st.session_state.calc_new_entry
            ):
                result = _calc_apply(
                    st.session_state.calc_prev, current, st.session_state.calc_op
                )
                st.session_state.calc_display = _calc_fmt(result)
                st.session_state.calc_prev = None if result != result else result
            else:
                st.session_state.calc_prev = current
            st.session_state.calc_op = key
            st.session_state.calc_new_entry = True
        elif key == "=":
            if (
                st.session_state.calc_prev is not None
                and st.session_state.calc_op is not None
            ):
                current = float(st.session_state.calc_display)
                result = _calc_apply(
                    st.session_state.calc_prev, current, st.session_state.calc_op
                )
                st.session_state.calc_display = _calc_fmt(result)
                st.session_state.calc_prev = None
                st.session_state.calc_op = None
                st.session_state.calc_new_entry = True

    if "calc_display" not in st.session_state:
        st.session_state.calc_display = "0"
        st.session_state.calc_prev = None
        st.session_state.calc_op = None
        st.session_state.calc_new_entry = False

    st.markdown("### 🧮 簡易電卓")
    st.markdown(
        f"""
        <div style="
            background: var(--note-paper);
            border: 1px solid var(--note-border);
            border-radius: 8px;
            padding: 10px 12px;
            text-align: right;
            font-size: 26px;
            font-family: ui-monospace, monospace;
            color: var(--note-ink);
            margin-bottom: 8px;
            overflow-x: auto;
            white-space: nowrap;
        ">{st.session_state.calc_display}</div>
        """,
        unsafe_allow_html=True,
    )

    # 「-」「+」単体はStreamlitのMarkdown箇条書き記号と解釈され表示が消えるため、
    # 見た目がほぼ同じ別のUnicode文字（全角プラス／マイナス記号）をボタンラベルに使う
    calc_label_to_op = {"－": "-", "＋": "+"}
    for row in (
        ["7", "8", "9", "÷"],
        ["4", "5", "6", "×"],
        ["1", "2", "3", "－"],
        ["C", "0", ".", "＋"],
    ):
        cols = st.columns(4)
        for col, label in zip(cols, row):
            if col.button(label, key=f"calc_btn_{label}", use_container_width=True):
                _calc_press(calc_label_to_op.get(label, label))
                st.rerun()

    if st.button("=", key="calc_btn_eq", type="primary", use_container_width=True):
        _calc_press("=")
        st.rerun()
    st.divider()

# データ読み込み
df_stock, sha_stock = get_github_data(FILE_PATH_STOCK)
df_log, sha_log = get_github_data(FILE_PATH_LOG)
df_hakuoshi, sha_hakuoshi = get_github_data(
    FILE_PATH_HAKUOSHI, default_cols=HAKUOSHI_COLS
)
df_seikan, sha_seikan = get_github_data(FILE_PATH_SEIKAN, default_cols=SEIKAN_COLS)
df_staff, sha_staff = get_github_data(FILE_PATH_STAFF, default_cols=STAFF_COLS)

# マスタ未登録の区分にはデフォルトの担当者を補って表示用に使う（保存はしない）
_staff_frames = [df_staff]
for _section, _names in DEFAULT_USERS.items():
    if not (df_staff["区分"] == _section).any():
        _staff_frames.append(
            pd.DataFrame([{"区分": _section, "担当者": n} for n in _names])
        )
df_staff = pd.concat(_staff_frames, ignore_index=True)


def get_users(section):
    sub = df_staff[df_staff["区分"] == section]
    return list(dict.fromkeys(sub["担当者"].tolist()))


def staff_manager(section, key_prefix):
    # st.expanderはこのStreamlitバージョンではstate保持ができず、
    # 中のセレクトボックスを操作するたびに閉じてしまうため、チェックボックスで開閉を管理する
    show = st.checkbox(
        f"👤 担当者を追加・削除する（{section}）", key=f"{key_prefix}_staff_toggle"
    )
    if not show:
        return

    current = get_users(section)
    new_name = st.text_input("追加する名前", key=f"{key_prefix}_staff_add")
    if st.button("➕ 追加", key=f"{key_prefix}_staff_add_btn"):
        name = new_name.strip()
        if not name:
            st.warning("名前を入力してください")
        elif name in current:
            st.warning("すでに登録されています")
        else:
            updated = pd.concat(
                [df_staff, pd.DataFrame([{"区分": section, "担当者": name}])],
                ignore_index=True,
            )
            if update_github_data(
                FILE_PATH_STAFF, updated, sha_staff, f"Add Staff ({section})"
            ) in (200, 201):
                st.cache_data.clear()
                st.success("追加しました")
                st.rerun()

    if current:
        remove_name = st.selectbox(
            "削除する名前", current, key=f"{key_prefix}_staff_remove_sel"
        )
        if len(current) <= 1:
            st.caption("※ 最後の1人は削除できません。")
        elif st.button("🗑 削除", key=f"{key_prefix}_staff_remove_btn"):
            mask = ~(
                (df_staff["区分"] == section) & (df_staff["担当者"] == remove_name)
            )
            updated = df_staff[mask]
            if update_github_data(
                FILE_PATH_STAFF, updated, sha_staff, f"Remove Staff ({section})"
            ) in (200, 201):
                st.cache_data.clear()
                st.success("削除しました")
                st.rerun()


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
        "リストにない組み合わせを入力する",
        key=f"{key_prefix}_manual",
        value=not item_opts,
    )

    col1, col2, col3 = st.columns(3)
    if manual or not item_opts:
        if not item_opts:
            st.info(
                "在庫管理システムにまだ商品が登録されていません。手入力してください。"
            )
        with col1:
            item = st.text_input("商品名", key=f"{key_prefix}_item_manual")
        with col2:
            size = st.text_input("サイズ", key=f"{key_prefix}_size_manual")
        with col3:
            loc = st.text_input("地名", key=f"{key_prefix}_loc_manual")
        matched = False
    else:
        with col1:
            item = st.selectbox(
                "商品名",
                item_opts,
                index=None,
                placeholder="選択してください",
                key=f"{key_prefix}_item_sel",
            )
        size_opts = get_stock_options(df_stock, "サイズ", {"商品名": item}) if item else []
        with col2:
            size = (
                st.selectbox(
                    "サイズ",
                    size_opts,
                    index=None,
                    placeholder="選択してください",
                    key=f"{key_prefix}_size_sel",
                )
                if size_opts
                else ""
            )
        loc_opts = (
            get_stock_options(df_stock, "地名", {"商品名": item, "サイズ": size})
            if size
            else []
        )
        with col3:
            loc = (
                st.selectbox(
                    "地名",
                    loc_opts,
                    index=None,
                    placeholder="選択してください",
                    key=f"{key_prefix}_loc_sel",
                )
                if loc_opts
                else ""
            )
        matched = bool(item and size and loc)

    return item, size, loc, matched


def today_section(df, qty_cols, title):
    st.markdown(f"### 🗓 本日の{title}")
    if df.empty:
        st.write("本日の記録はまだありません。")
        return

    df_show = df.copy()
    df_show["日時"] = pd.to_datetime(df_show["日時"], errors="coerce")
    df_show = df_show.dropna(subset=["日時"])

    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    df_today = df_show[df_show["日時"].dt.date == today].sort_values(
        "日時", ascending=False
    )

    if df_today.empty:
        st.write("本日の記録はまだありません。")
        return

    totals = "　".join(f"{col}合計 {int(df_today[col].sum())}" for col in qty_cols)
    st.caption(f"{len(df_today)}件　{totals}")
    st.dataframe(
        df_today,
        hide_index=True,
        use_container_width=True,
        column_config={"日時": st.column_config.DatetimeColumn("日時", format="HH:mm")},
    )


def history_section(
    df, sha, file_path, disp_cols, title, delete_key, stock_qty_col=None
):
    st.markdown(f"### 📜 {title}履歴")
    if df.empty:
        st.write("記録はまだありません。")
        return

    df_show = df.copy()
    df_show["日時"] = pd.to_datetime(df_show["日時"], errors="coerce")
    df_show = df_show.dropna(subset=["日時"]).sort_values("日時", ascending=False)

    def _opts(col):
        return ["すべて"] + sorted(
            [str(x) for x in df_show[col].unique() if str(x).strip() != ""]
        )

    fc1, fc2 = st.columns(2)
    with fc1:
        f_item = st.selectbox(
            "商品名", _opts("商品名"), key=f"{delete_key}_filter_item"
        )
    with fc2:
        f_size = st.selectbox(
            "サイズ", _opts("サイズ"), key=f"{delete_key}_filter_size"
        )
    fc3, fc4 = st.columns(2)
    with fc3:
        f_loc = st.selectbox("地名", _opts("地名"), key=f"{delete_key}_filter_loc")
    with fc4:
        f_user = st.selectbox(
            "担当者", _opts("担当者"), key=f"{delete_key}_filter_user"
        )

    min_date = df_show["日時"].min().date()
    max_date = df_show["日時"].max().date()
    fd1, fd2 = st.columns(2)
    with fd1:
        f_start = st.date_input(
            "開始日",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            key=f"{delete_key}_filter_start",
        )
    with fd2:
        f_end = st.date_input(
            "終了日",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            key=f"{delete_key}_filter_end",
        )

    if f_item != "すべて":
        df_show = df_show[df_show["商品名"] == f_item]
    if f_size != "すべて":
        df_show = df_show[df_show["サイズ"] == f_size]
    if f_loc != "すべて":
        df_show = df_show[df_show["地名"] == f_loc]
    if f_user != "すべて":
        df_show = df_show[df_show["担当者"] == f_user]
    df_show = df_show[
        (df_show["日時"].dt.date >= f_start) & (df_show["日時"].dt.date <= f_end)
    ]

    st.caption(f"該当 {len(df_show)} 件（最新100件まで表示）")
    df_show = df_show.head(100)
    df_show.insert(0, "削除", False)

    edited = st.data_editor(
        df_show,
        hide_index=True,
        use_container_width=True,
        disabled=disp_cols,
        column_config={
            "日時": st.column_config.DatetimeColumn("日時", format="YYYY-MM-DD HH:mm")
        },
        key=f"{delete_key}_editor",
    )

    to_delete = edited.index[edited["削除"] == True]
    if len(to_delete) > 0 and st.button(
        f"🗑 チェックした記録を削除（{len(to_delete)}件）",
        key=f"{delete_key}_delete_btn",
        type="secondary",
    ):
        deleted_rows = df.loc[to_delete]
        new_df = df.drop(to_delete)
        deleted_ok = update_github_data(
            file_path, new_df, sha, f"Delete {title} Record"
        ) in (200, 201)

        stock_reverted = False
        if deleted_ok and stock_qty_col:
            now = get_now_jst()
            new_df_stock = df_stock.copy()
            log_rows = []
            for _, row in deleted_rows.iterrows():
                qty = row.get(stock_qty_col, 0)
                if not qty:
                    continue
                mask = (
                    (new_df_stock["商品名"] == row["商品名"])
                    & (new_df_stock["サイズ"] == row["サイズ"])
                    & (new_df_stock["地名"] == row["地名"])
                )
                if mask.any():
                    idx = new_df_stock[mask].index[0]
                    new_df_stock.at[idx, "在庫数"] -= qty
                    new_df_stock.at[idx, "最終更新日"] = now
                    log_rows.append(
                        {
                            "日時": now,
                            "商品名": row["商品名"],
                            "サイズ": row["サイズ"],
                            "地名": row["地名"],
                            "区分": "削除による戻し",
                            "数量": -qty,
                            "在庫数": new_df_stock.at[idx, "在庫数"],
                            "担当者": row.get("担当者", ""),
                        }
                    )

            if log_rows and update_github_data(
                FILE_PATH_STOCK, new_df_stock, sha_stock, f"Delete {title} Stock Revert"
            ) in (200, 201):
                update_github_data(
                    FILE_PATH_LOG,
                    pd.concat([df_log, pd.DataFrame(log_rows)], ignore_index=True),
                    sha_log,
                    f"Delete {title} Stock Log",
                )
                stock_reverted = True

        if deleted_ok:
            st.cache_data.clear()
            if stock_qty_col and stock_reverted:
                st.success("削除しました（在庫からも差し引きました）")
            elif stock_qty_col:
                st.success(
                    "削除しました（在庫マスタに一致しないため在庫は変更していません）"
                )
            else:
                st.success("削除しました")
            st.rerun()


PANEL_HEIGHT = 850

tab_hakuoshi, tab_seikan = st.tabs(["🖨 箔押し記録", "📦 製函記録"])

# --- 箔押し記録 ---
with tab_hakuoshi:
    with st.container(height=PANEL_HEIGHT, border=True):
        st.subheader("🖨 箔押し記録の登録")
        h_item, h_size, h_loc, _ = item_picker("h")

        # 数量・担当者・登録ボタンはフォームにまとめ、入力のたびに画面全体が
        # 再描画される（スクロール位置が飛ぶ）のを防ぎ、登録ボタンを押した時だけ確定させる
        with st.form("h_form", border=False):
            col4, col5, col6 = st.columns(3)
            with col4:
                h_qty = st.number_input("箔押し枚数", min_value=0, value=0, key="h_qty")
            with col5:
                h_miss = st.number_input("ミス数", min_value=0, value=0, key="h_miss")
            with col6:
                h_user = st.selectbox(
                    "担当者",
                    get_users("箔押し"),
                    index=None,
                    placeholder="選択してください",
                    key="h_user",
                )

            h_submitted = st.form_submit_button(
                "✅ 箔押し記録を登録",
                type="primary",
                use_container_width=True,
            )

        staff_manager("箔押し", "h")

        if h_submitted:
            if h_item and h_size and h_loc and h_user:
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
                st.error("商品名・サイズ・地名・担当者を選択してください")

        st.divider()
        today_section(df_hakuoshi, ["枚数", "ミス数"], "箔押し記録")

        st.divider()
        history_section(
            df_hakuoshi,
            sha_hakuoshi,
            FILE_PATH_HAKUOSHI,
            ["日時", "商品名", "サイズ", "地名", "枚数", "ミス数", "担当者"],
            "箔押し記録",
            "hakuoshi",
        )

# --- 製函記録 ---
with tab_seikan:
    with st.container(height=PANEL_HEIGHT, border=True):
        st.subheader("📦 製函記録の登録")
        s_item, s_size, s_loc, s_matched = item_picker("s")

        # 数量・担当者・登録ボタンはフォームにまとめ、入力のたびに画面全体が
        # 再描画される（スクロール位置が飛ぶ）のを防ぎ、登録ボタンを押した時だけ確定させる
        with st.form("s_form", border=False):
            col7, col8, col9, col10 = st.columns(4)
            with col7:
                s_qty = st.number_input(
                    "製函数（c/s）", min_value=0, value=0, key="s_qty"
                )
            with col8:
                s_miss_futa = st.number_input(
                    "ミス数（フタ）", min_value=0, value=0, key="s_miss_futa"
                )
            with col9:
                s_miss_mi = st.number_input(
                    "ミス数（身）", min_value=0, value=0, key="s_miss_mi"
                )
            with col10:
                s_user = st.selectbox(
                    "担当者",
                    get_users("製函"),
                    index=None,
                    placeholder="選択してください",
                    key="s_user",
                )

            if not s_matched:
                st.caption(
                    "※ 在庫マスタに一致する商品が無いため、在庫数への反映はスキップされます。"
                )

            s_submitted = st.form_submit_button(
                "✅ 製函記録を登録",
                type="primary",
                use_container_width=True,
            )

        staff_manager("製函", "s")

        if s_submitted:
            if s_item and s_size and s_loc and s_user:
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
                st.error("商品名・サイズ・地名・担当者を選択してください")

        st.divider()
        today_section(df_seikan, ["製函数", "ミス_フタ", "ミス_身"], "製函記録")

        st.divider()
        history_section(
            df_seikan,
            sha_seikan,
            FILE_PATH_SEIKAN,
            [
                "日時",
                "商品名",
                "サイズ",
                "地名",
                "製函数",
                "ミス_フタ",
                "ミス_身",
                "担当者",
            ],
            "製函記録",
            "seikan",
            stock_qty_col="製函数",
        )
