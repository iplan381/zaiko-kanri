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
    st.sidebar.header("🔍 基本表示条件")
    year_list = sorted(df_out_all["年"].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 表示年を選択", year_list)
    
    month_options = [f"{m}月" for m in range(1, 13)]
    sel_month_str = st.sidebar.selectbox("📆 メイン表示月", ["すべて表示"] + month_options)

    st.sidebar.divider()
    st.sidebar.header("⚖️ 2ヶ月間 比較設定")
    compare_m1 = st.sidebar.selectbox("比較月A", month_options, index=0)
    compare_m2 = st.sidebar.selectbox("比較月B", month_options, index=1)

    show_compare_lastyear = st.sidebar.checkbox("🔄 前年同期比を有効にする", value=True)

    # 初期化
    sel_item = "すべて表示"
    sel_size = "すべて表示"
    sel_loc = "すべて表示"

    # メインフィルタリング
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
        df_this_year_base = df_this_year_base[df_this_year_base["商品名"] == sel_item]
        
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
        
        cols = st.columns(4 if show_compare_lastyear else 3)
        with cols[0]: st.metric(f"{sel_month_str} 合計", f"{int(qty_this):,}")
        if show_compare_lastyear:
            with cols[1]: st.metric("前年同期実績", f"{int(qty_last):,}")
            with cols[2]: 
                diff_pct = f"{round(((qty_this - qty_last) / qty_last) * 100, 1)}%" if qty_last > 0 else "---"
                st.metric("前年比", diff_pct)
            with cols[3]: st.metric("項目数", f"{df_final['項目詳細'].nunique()}")
        else:
            with cols[1]: st.metric("項目数", f"{df_final['項目詳細'].nunique()}")
            with cols[2]: st.metric("平均出荷", f"{round(df_final['数量'].mean(), 1)}")

        # --- タブ構成 (確実に6つ定義) ---
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 傾向・シェア", 
            "📈 トレンド推移", 
            "⚖️ 2ヶ月間 比較分析", 
            "🏆 ABC分析", 
            "⚠️ 不動・安全在庫", 
            "🔢 履歴明細"
        ])

        with tab1:
            st.subheader("📦 項目別ランキング")
            summary_rank = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(20).reset_index()
            fig_rank = px.bar(summary_rank, y="項目詳細", x="数量", orientation='h', text_auto=True)
            st.plotly_chart(fig_rank, use_container_width=True)

        with tab2:
            st.subheader("📅 日次トレンド")
            df_daily = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            fig_daily = px.line(df_daily, x="日時", y="数量", markers=True)
            st.plotly_chart(fig_daily, use_container_width=True)
            
            st.divider()
            st.subheader(f"📊 {sel_year}年 月別実績")
            df_m_summary = df_this_year_base.groupby("月")["数量"].sum().reset_index()
            df_m_summary["月表示"] = df_m_summary["月"].astype(str) + "月"
            fig_m = px.bar(df_m_summary, x="月表示", y="数量", text_auto=True)
            st.plotly_chart(fig_m, use_container_width=True)

        # --- 【ここがポイント】tab3を完全に独立させて記述 ---
        with tab3:
            st.subheader(f"⚖️ {compare_m1} と {compare_m2} の比較")
            m1_val = int(compare_m1.replace("月", ""))
            m2_val = int(compare_m2.replace("月", ""))
            
            df_m1 = df_this_year_base[df_this_year_base["月"] == m1_val]
            df_m2 = df_this_year_base[df_this_year_base["月"] == m2_val]
            
            mc1, mc2, mc3 = st.columns(3)
            q1 = df_m1["数量"].sum()
            q2 = df_m2["数量"].sum()
            with mc1: st.metric(f"{compare_m1} 合計", f"{int(q1):,}")
            with mc2: st.metric(f"{compare_m2} 合計", f"{int(q2):,}")
            with mc3: st.metric("2ヶ月の差分", f"{int(q2 - q1):+,}")

            st.write("📝 **日次の動きを重ねて比較**")
            d1 = df_m1.groupby(df_m1["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時": "日", "数量": compare_m1})
            d2 = df_m2.groupby(df_m2["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時": "日", "数量": compare_m2})
            df_comp = pd.merge(d1, d2, on="日", how="outer").fillna(0).sort_values("日")
            
            fig_c = px.line(df_comp, x="日", y=[compare_m1, compare_m2], markers=True)
            st.plotly_chart(fig_c, use_container_width=True)

        with tab4:
            st.subheader("🏆 ABC分析")
            abc_df = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
            if not abc_df.empty:
                abc_df["累積比"] = abc_df["数量"].cumsum() / abc_df["数量"].sum() * 100
                abc_df["ランク"] = abc_df["累積比"].apply(lambda x: "A" if x <= 80 else ("B" if x <= 95 else "C"))
                fig_abc = px.bar(abc_df, x="数量", y="項目詳細", orientation='h', color="ランク")
                st.plotly_chart(fig_abc, use_container_width=True)

        with tab5:
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.subheader("⚠️ 不動在庫（長い間動いていないもの）")
                df_db = df_out_all.copy()
                if sel_item != "すべて表示": df_db = df_db[df_db["商品名"] == sel_item]
                if sel_size != "すべて表示": df_db = df_db[df_db["サイズ"] == sel_size]
                now = pd.Timestamp.now()
                dead = df_db.groupby("項目詳細")["日時"].max().reset_index().rename(columns={"日時": "最終日"})
                dead["経過日数"] = (now - dead["最終日"]).dt.days
                st.dataframe(dead.sort_values("経過日数", ascending=False), use_container_width=True, hide_index=True)
            with col_w2:
                st.subheader("💡 推奨在庫（出荷の偏りから計算）")
                sf = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
                sf["推奨在庫"] = (sf["mean"] + 2 * sf["std"]).round(0)
                st.dataframe(sf[["項目詳細", "推奨在庫"]], use_container_width=True, hide_index=True)

        with tab6:
            st.subheader("🔢 履歴明細")
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。絞り込み条件を変えてみてください。")
