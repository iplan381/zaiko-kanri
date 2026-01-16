import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO
import datetime

# --- 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="詳細階層分析ボード", layout="wide")

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

st.title("📈 階層別 在庫動態分析")

if not df_log_raw.empty:
    # --- データ前処理 ---
    df = df_log_raw.copy()
    df["日時"] = pd.to_datetime(df["日時"])
    df["年"] = df["日時"].dt.year
    df["月"] = df["日時"].dt.month
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ（分析用）
    df_out_all = df[df["区分"].str.contains("出庫")].copy()
    df_out_all["項目詳細"] = df_out_all["商品名"].astype(str) + " | " + df_out_all["サイズ"].astype(str) + " | " + df_out_all["地名"].astype(str)

    # --- 🔍 絞り込み条件（サイドバー） ---
    st.sidebar.header("🔍 絞り込み条件")
    
    # 年・月の初期フィルタ
    year_list = sorted(df_out_all["年"].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 ① 年を選択", year_list)
    
    month_options = ["すべて表示"] + [f"{m}月" for m in range(1, 13)]
    sel_month_str = st.sidebar.selectbox("📆 ② 月を選択", month_options)

    # 昨年対比スイッチ（画像3枚目の%表示用）
    st.sidebar.divider()
    show_compare = st.sidebar.checkbox("🔄 昨年対比を表示する", value=True)

    # 変数の初期化（エラー防止）
    sel_item = "すべて表示"
    sel_size = "すべて表示"
    sel_loc = "すべて表示"

    # フィルタリング（年・月）
    df_step1 = df_out_all[df_out_all["年"] == sel_year]
    if sel_month_str != "すべて表示":
        m_int = int(sel_month_str.replace("月", ""))
        df_step2 = df_step1[df_step1["月"] == m_int]
        df_last_base = df_out_all[(df_out_all["年"] == (sel_year - 1)) & (df_out_all["月"] == m_int)]
    else:
        df_step2 = df_step1
        df_last_base = df_out_all[df_out_all["年"] == (sel_year - 1)]

    # 商品名以降の絞り込み
    item_list = ["すべて表示"] + sorted(df_step2["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 ③ 商品名を選択", item_list)
    
    df_final = df_step2.copy()
    df_last = df_last_base.copy()

    if sel_item != "すべて表示":
        df_final = df_final[df_final["商品名"] == sel_item]
        df_last = df_last[df_last["商品名"] == sel_item]
        
        size_list = ["すべて表示"] + sorted(df_final["サイズ"].unique().tolist())
        sel_size = st.sidebar.selectbox("📏 ④ サイズを選択", size_list)
        
        if sel_size != "すべて表示":
            df_final = df_final[df_final["サイズ"] == sel_size]
            df_last = df_last[df_last["サイズ"] == sel_size]
            
            loc_list = ["すべて表示"] + sorted(df_final["地名"].unique().tolist())
            sel_loc = st.sidebar.selectbox("📍 ⑤ 地名を選択", loc_list)
            if sel_loc != "すべて表示":
                df_final = df_final[df_final["地名"] == sel_loc]
                df_last = df_last[df_last["地名"] == sel_loc]

    st.divider()

    if not df_final.empty:
        # --- KPIエリア ---
        qty_this = df_final["数量"].sum()
        qty_last = df_last["数量"].sum()
        
        k1, k2, k3 = st.columns(3)
        if show_compare and qty_last > 0:
            diff_pct = f"{round(((qty_this - qty_last) / qty_last) * 100, 1)}%"
            # 画像3枚目のスタイル: deltaを使って緑色の%を表示
            with k1: st.metric("期間内 合計出荷", f"{int(qty_this):,}", delta=diff_pct)
            with k2: st.metric("前年同期実績", f"{int(qty_last):,}")
        else:
            with k1: st.metric("期間内 合計出荷", f"{int(qty_this):,}")
            with k2: st.metric("稼働項目数", f"{df_final['項目詳細'].nunique()}")
        with k3: st.metric("平均出荷量", f"{round(df_final['数量'].mean(), 1)}")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 傾向・シェア", "📈 トレンド推移", "🏆 ABC分析", "⚠️ 不動・安全在庫", "🔢 履歴明細"])

        with tab1:
            st.subheader("📦 詳細項目別ランキング（上位20件）")
            summary_rank = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(20).reset_index()
            fig_rank = px.bar(summary_rank, y="項目詳細", x="数量", orientation='h', text_auto=True, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_rank, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📍 地名別シェア")
                fig_pie = px.pie(df_final, values='数量', names='地名', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                st.subheader("📅 曜日別傾向")
                df_final["曜日"] = df_final["日時"].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_jp = {'Monday':'月','Tuesday':'火','Wednesday':'水','Thursday':'木','Friday':'金','Saturday':'土','Sunday':'日'}
                summary_day = df_final.groupby("曜日")["数量"].sum().reindex(day_order).reset_index()
                summary_day["表示曜日"] = summary_day["曜日"].map(day_jp)
                fig_day = px.bar(summary_day, x="表示曜日", y="数量", text_auto=True, color_discrete_sequence=['#56B4E9'])
                st.plotly_chart(fig_day, use_container_width=True)

        with tab2:
            st.subheader("📈 トレンド推移 (年月絞り込み内)")
            df_trend_this = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            df_trend_this["年区分"] = str(sel_year)
            
            if show_compare and not df_last.empty:
                df_trend_last = df_last.groupby(df_last["日時"].dt.date)["数量"].sum().reset_index()
                df_trend_last["年区分"] = str(sel_year - 1)
                df_trend_last["日時"] = pd.to_datetime(df_trend_last["日時"]) + pd.offsets.DateOffset(years=1)
                df_combined = pd.concat([df_trend_this, df_trend_last])
                fig_trend = px.line(df_combined, x="日時", y="数量", color="年区分", markers=True, color_discrete_map={str(sel_year): "#D55E00", str(sel_year-1): "#999999"})
            else:
                fig_trend = px.line(df_trend_this, x="日時", y="数量", markers=True, color_discrete_sequence=['#0072B2'])
            st.plotly_chart(fig_trend, use_container_width=True)

        with tab3:
            st.subheader("🏆 ABC分析（項目別）")
            abc_df = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
            abc_df["累積"] = abc_df["数量"].cumsum() / abc_df["数量"].sum() * 100
            abc_df["ランク"] = abc_df["累積"].apply(lambda x: "A" if x <= 80 else ("B" if x <= 95 else "C"))
            fig_abc = px.bar(abc_df.sort_values("数量"), y="項目詳細", x="数量", orientation='h', color="ランク", color_discrete_map={"A": "#D55E00", "B": "#009E73", "C": "#F0E442"})
            st.plotly_chart(fig_abc, use_container_width=True)

        with tab4:
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.subheader("⚠️ 不動在庫分析")
                # 期間絞り込みを無視し、商品・サイズに連動
                df_db = df_out_all.copy()
                if sel_item != "すべて表示": df_db = df_db[df_db["商品名"] == sel_item]
                if sel_size != "すべて表示": df_db = df_db[df_db["サイズ"] == sel_size]
                
                now = pd.Timestamp.now()
                dead = df_db.groupby("項目詳細")["日時"].max().reset_index()
                dead = dead.rename(columns={"日時": "最終出荷日"})
                dead["経過日数"] = (now - dead["最終出荷日"]).dt.days
                dead.loc[dead["経過日数"] < 0, "経過日数"] = 0
                dead = dead.sort_values("経過日数", ascending=False)
                dead["最終出荷日"] = dead["最終出荷日"].dt.strftime('%Y-%m-%d')
                st.dataframe(dead, use_container_width=True, hide_index=True)
            with col_w2:
                st.subheader("💡 推奨・安全在庫")
                safety = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
                safety["推奨在庫"] = (safety["mean"] + 2 * safety["std"]).round(0)
                st.dataframe(safety[["項目詳細", "推奨在庫"]].sort_values("推奨在庫", ascending=False), use_container_width=True, hide_index=True)

        with tab5:
            st.subheader("🔢 履歴明細")
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。")
