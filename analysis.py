import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO

# --- 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="在庫動態分析ボード", layout="wide")

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
    
    df_out_all = df[df["区分"].str.contains("出庫")].copy()
    df_out_all["項目詳細"] = df_out_all["商品名"].astype(str) + " | " + df_out_all["サイズ"].astype(str) + " | " + df_out_all["地名"].astype(str)

    # --- 🔍 絞り込み条件 ---
    st.sidebar.header("🔍 絞り込み条件")
    year_list = sorted(df_out_all["年"].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 ① 年を選択", year_list)
    
    month_options = ["すべて表示"] + [f"{m}月" for m in range(1, 13)]
    sel_month_str = st.sidebar.selectbox("📆 ② 月を選択", month_options)

    show_compare = st.sidebar.checkbox("🔄 昨年対比を表示する", value=True)

    # 初期化
    sel_item = "すべて表示"
    sel_size = "すべて表示"
    sel_loc = "すべて表示"

    # フィルタリング（年・月）
    df_this_year_base = df_out_all[df_out_all["年"] == sel_year]
    if sel_month_str != "すべて表示":
        m_int = int(sel_month_str.replace("月", ""))
        df_final = df_this_year_base[df_this_year_base["月"] == m_int]
        df_last = df_out_all[(df_out_all["年"] == (sel_year - 1)) & (df_out_all["月"] == m_int)]
    else:
        df_final = df_this_year_base
        df_last = df_out_all[df_out_all["年"] == (sel_year - 1)]

    # 詳細絞り込み
    item_list = ["すべて表示"] + sorted(df_final["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 ③ 商品名を選択", item_list)
    
    if sel_item != "すべて表示":
        df_final = df_final[df_final["商品名"] == sel_item]
        df_last = df_last[df_last["商品名"] == sel_item]
        df_this_year_base = df_this_year_base[df_this_year_base["商品名"] == sel_item] # 年内比較用

        size_list = ["すべて表示"] + sorted(df_final["サイズ"].unique().tolist())
        sel_size = st.sidebar.selectbox("📏 ④ サイズを選択", size_list)
        if sel_size != "すべて表示":
            df_final = df_final[df_final["サイズ"] == sel_size]
            df_last = df_last[df_last["サイズ"] == sel_size]
            df_this_year_base = df_this_year_base[df_this_year_base["サイズ"] == sel_size]

            loc_list = ["すべて表示"] + sorted(df_final["地名"].unique().tolist())
            sel_loc = st.sidebar.selectbox("📍 ⑤ 地名を選択", loc_list)
            if sel_loc != "すべて表示":
                df_final = df_final[df_final["地名"] == sel_loc]
                df_last = df_last[df_last["地名"] == sel_loc]
                df_this_year_base = df_this_year_base[df_this_year_base["地名"] == sel_loc]

    st.divider()

    if not df_final.empty:
        # --- KPIエリア ---
        qty_this = df_final["数量"].sum()
        qty_last = df_last["数量"].sum()
        
        cols = st.columns(4 if show_compare else 3)
        with cols[0]: st.metric("期間内 合計出荷", f"{int(qty_this):,}")
        if show_compare:
            with cols[1]: st.metric("前年同期実績", f"{int(qty_last):,}")
            with cols[2]: 
                diff_pct = f"{round(((qty_this - qty_last) / qty_last) * 100, 1)}%" if qty_last > 0 else "---"
                st.metric("前年同期比", diff_pct)
            with cols[3]: st.metric("稼働詳細項目数", f"{df_final['項目詳細'].nunique()}")
        else:
            with cols[1]: st.metric("稼働詳細項目数", f"{df_final['項目詳細'].nunique()}")
            with cols[2]: st.metric("期間内 平均出荷", f"{round(df_final['数量'].mean(), 1)}")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 傾向・シェア", "📈 トレンド推移", "🏆 ABC分析", "⚠️ 不動・安全在庫", "🔢 履歴明細"])

        with tab1:
            st.subheader("📦 詳細項目別ランキング（上位20件）")
            summary_rank = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(20).reset_index()
            fig_rank = px.bar(summary_rank, y="項目詳細", x="数量", orientation='h', text_auto=True, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_rank, use_container_width=True)

        with tab2:
            # --- 1. 選択期間内の日次推移 ---
            st.subheader(f"📅 {sel_month_str if sel_month_str != 'すべて表示' else '年間'}の日次トレンド")
            df_daily = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            df_daily["年区分"] = str(sel_year)
            
            if show_compare and not df_last.empty:
                df_daily_last = df_last.groupby(df_last["日時"].dt.date)["数量"].sum().reset_index()
                df_daily_last["年区分"] = str(sel_year - 1)
                df_daily_last["日時"] = pd.to_datetime(df_daily_last["日時"]) + pd.offsets.DateOffset(years=1)
                fig_daily = px.line(pd.concat([df_daily, df_daily_last]), x="日時", y="数量", color="年区分", markers=True, color_discrete_map={str(sel_year): "#D55E00", str(sel_year-1): "#999999"})
            else:
                fig_daily = px.line(df_daily, x="日時", y="数量", markers=True, color_discrete_sequence=['#0072B2'])
            st.plotly_chart(fig_daily, use_container_width=True)

            # --- 2. 同じ年の中での月別比較（新設！） ---
            st.divider()
            st.subheader(f"📊 {sel_year}年 月別出荷ボリューム比較")
            df_monthly = df_this_year_base.groupby("月")["数量"].sum().reset_index()
            # 1月〜12月を確実に表示させる
            all_months = pd.DataFrame({"月": range(1, 13)})
            df_monthly = pd.merge(all_months, df_monthly, on="月", how="left").fillna(0)
            df_monthly["月表示"] = df_monthly["月"].astype(str) + "月"
            
            fig_monthly = px.bar(df_monthly, x="月表示", y="数量", text_auto=True, 
                                 title=f"{sel_year}年内の推移",
                                 color_discrete_sequence=['#56B4E9'])
            # 選択中の月を強調
            if sel_month_str != "すべて表示":
                m_idx = int(sel_month_str.replace("月", "")) - 1
                fig_monthly.data[0].marker.color = ['#56B4E9'] * 12
                # 修正：plotlyのリスト指定
                colors = ['#56B4E9'] * 12
                colors[m_idx] = '#D55E00' # 選択月をオレンジに
                fig_monthly.update_traces(marker_color=colors)

            st.plotly_chart(fig_monthly, use_container_width=True)

        with tab3:
            st.subheader("🏆 ABC分析")
            abc_df = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
            abc_df["累積"] = abc_df["数量"].cumsum() / abc_df["数量"].sum() * 100
            abc_df["ランク"] = abc_df["累積"].apply(lambda x: "A" if x <= 80 else ("B" if x <= 95 else "C"))
            fig_abc = px.bar(abc_df.sort_values("数量"), y="項目詳細", x="数量", orientation='h', color="ランク", color_discrete_map={"A": "#D55E00", "B": "#009E73", "C": "#F0E442"})
            st.plotly_chart(fig_abc, use_container_width=True)

        with tab4:
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.subheader("⚠️ 不動在庫")
                df_db = df_out_all.copy()
                if sel_item != "すべて表示": df_db = df_db[df_db["商品名"] == sel_item]
                if sel_size != "すべて表示": df_db = df_db[df_db["サイズ"] == sel_size]
                now = pd.Timestamp.now()
                dead = df_db.groupby("項目詳細")["日時"].max().reset_index().rename(columns={"日時": "最終出荷日"})
                dead["経過日数"] = (now - dead["最終出荷日"]).dt.days
                dead.loc[dead["経過日数"] < 0, "経過日数"] = 0
                dead["最終出荷日"] = dead["最終出荷日"].dt.strftime('%Y-%m-%d')
                st.dataframe(dead.sort_values("経過日数", ascending=False), use_container_width=True, hide_index=True)
            with col_w2:
                st.subheader("💡 推奨在庫")
                safety = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
                safety["推奨在庫"] = (safety["mean"] + 2 * safety["std"]).round(0)
                st.dataframe(safety[["項目詳細", "推奨在庫"]].sort_values("推奨在庫", ascending=False), use_container_width=True, hide_index=True)

        with tab5:
            st.subheader("🔢 履歴明細")
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。")
