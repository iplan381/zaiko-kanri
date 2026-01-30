import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO
import datetime as dt

# --- 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="出庫分析", layout="wide")

@st.cache_data(ttl=60)
def get_github_data(file_path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        return pd.read_csv(StringIO(csv_text)).fillna("")
    return pd.DataFrame()

df_log_raw = get_github_data(FILE_PATH_LOG)

st.title("📈 在庫動態分析（期間比較モード）")

if not df_log_raw.empty:
    df = df_log_raw.copy()
    df["日時"] = pd.to_datetime(df["日時"], errors='coerce', format='mixed')
    df = df.dropna(subset=["日時"])
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    df_out_all = df[df["区分"].str.contains("出庫")].copy()
    df_out_all["項目詳細"] = df_out_all["商品名"].astype(str) + " | " + df_out_all["サイズ"].astype(str) + " | " + df_out_all["地名"].astype(str)

   with st.sidebar:
        st.markdown("### 🔗 クイック移動")
        c1, c2 = st.columns(2)
        c1.link_button("📦 在庫管理", "https://zaiko-kanri.streamlit.app/")
        c2.link_button("🚚 発注管理", "https://zaiko-kanri-qzelakcnxralslk3ac27ex.streamlit.app/")
        st.divider()
    
        st.sidebar.header("🔍 期間設定")
        
        # 💡 エラー回避：最小・最大の値を安全に取得
        min_d = df_out_all["日時"].min().date()
        max_d = df_out_all["日時"].max().date()
        
        # もしデータが1日分しかない場合に備えてガード
        if min_d >= max_d:
            min_d = max_d - dt.timedelta(days=1)

        # 📅 メイン期間（期間A）：初期値がmin_dより前にならないように調整
        st.subheader("① 分析期間 (メイン)")
        start_a = max(min_d, max_d - dt.timedelta(days=30)) # 枠外にはみ出さないようガード
        range_a = st.date_input("分析したい期間を選択", [start_a, max_d], min_value=min_d, max_value=max_d, key="range_a")

        # 📅 比較期間（期間B）：同様に枠内ガード
        st.subheader("② 比較期間 (ターゲット)")
        start_b = max(min_d, max_d - dt.timedelta(days=61))
        end_b = max(min_d, max_d - dt.timedelta(days=31))
        # 比較用なので初期値はメインと被らないように設定
        range_b = st.date_input("比較したい過去の期間を選択", [start_b, end_b], min_value=min_d, max_value=max_d, key="range_b")
        st.divider()
        st.header("📦 絞り込み")
        all_item = ["すべて表示"] + sorted(df_out_all["商品名"].unique().tolist())
        all_size = ["すべて表示"] + sorted(df_out_all["サイズ"].unique().tolist())
        all_loc = ["すべて表示"] + sorted(df_out_all["地名"].unique().tolist())

        sel_item = st.selectbox("商品名", all_item)
        sel_size = st.selectbox("サイズ", all_size)
        sel_loc = st.selectbox("地名", all_loc)
        show_compare = st.checkbox("🔄 比較を表示する", value=True)

    # 期間Aの抽出
    if isinstance(range_a, (list, tuple)) and len(range_a) == 2:
        df_final = df_out_all[(df_out_all["日時"].dt.date >= range_a[0]) & (df_out_all["日時"].dt.date <= range_a[1])]
    else:
        st.info("左側メニューで「分析期間」を2箇所選択してください。")
        st.stop()

    # 期間Bの抽出
    if isinstance(range_b, (list, tuple)) and len(range_b) == 2:
        df_compare = df_out_all[(df_out_all["日時"].dt.date >= range_b[0]) & (df_out_all["日時"].dt.date <= range_b[1])]
    else:
        df_compare = pd.DataFrame()

    # フィルタ適用（共通）
    for target_df in [df_final, df_compare]:
        if not target_df.empty:
            if sel_item != "すべて表示": target_df = target_df[target_df["商品名"] == sel_item]
            if sel_size != "すべて表示": target_df = target_df[target_df["サイズ"] == sel_size]
            if sel_loc != "すべて表示": target_df = target_df[target_df["地名"] == sel_loc]

    st.divider()

    if not df_final.empty:
        qty_a = df_final["数量"].sum()
        qty_b = df_compare["数量"].sum() if not df_compare.empty else 0
        
        if show_compare:
            k1, k2, k3, k4 = st.columns(4)
            diff_pct = f"{round(((qty_a - qty_b) / qty_b) * 100, 1)}%" if qty_b > 0 else "---"
            with k1: st.metric("分析期間 合計", f"{int(qty_a):,}")
            with k2: st.metric("比較期間 実績", f"{int(qty_b):,}")
            with k3: st.metric("比較増減率", diff_pct, delta=f"{int(qty_a - qty_b):,}")
            with k4: st.metric("メイン項目数", f"{df_final['項目詳細'].nunique()}")
        else:
            k1, k2, k3 = st.columns(3)
            with k1: st.metric("分析期間 合計", f"{int(qty_a):,}")
            with k2: st.metric("平均出荷量", f"{round(df_final['数量'].mean(), 1)}")
            with k3: st.metric("項目数", f"{df_final['項目詳細'].nunique()}")

        tab1, tab2, tab4, tab5 = st.tabs(["📊 傾向", "📈 トレンド推移", "⚠️ 不動・安全在庫", "🔢 履歴明細"])

        with tab1:
            st.subheader("📦 分析期間のランキング")
            summary = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(20).reset_index()
            st.plotly_chart(px.bar(summary, y="項目詳細", x="数量", orientation='h', text_auto=True), use_container_width=True)

        with tab2:
            st.subheader("📈 トレンド推移")
            # 期間AとBを一つのグラフに重ねるか、別々に出すか選べるけど、まずはメインを表示
            df_trend = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            st.plotly_chart(px.line(df_trend, x="日時", y="数量", markers=True, title="メイン期間の推移"), use_container_width=True)

        with tab4:
            # 不動在庫などはメイン期間に基づいて表示
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.subheader("⚠️ メイン期間内の不動")
                dead = df_final.groupby("項目詳細")["日時"].max().reset_index().rename(columns={"日時": "最終"})
                st.dataframe(dead.sort_values("最終", ascending=False), use_container_width=True, hide_index=True)
            with col_w2:
                st.subheader("💡 推奨在庫 (メイン期間ベース)")
                safety = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
                safety["推奨"] = (safety["mean"] + 2 * safety["std"]).round(0)
                st.dataframe(safety.sort_values("推奨", ascending=False), use_container_width=True, hide_index=True)

        with tab5:
            st.subheader("🔢 履歴明細 (分析期間)")
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("条件に一致するデータがありません。")
