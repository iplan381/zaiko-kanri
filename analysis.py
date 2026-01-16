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
    # 月を文字化して変な目盛り（0.5月など）を解消
    df["月"] = df["日時"].dt.month.astype(str) + "月"
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ
    df_out = df[df["区分"].str.contains("出庫")].copy()

    # --- 5段階 階層絞り込み ---
    st.sidebar.header("🔍 絞り込み条件")
    
    year_list = sorted(df_out["年"].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 ① 年を選択", year_list)
    df_y = df_out[df_out["年"] == sel_year]

    month_options = ["すべて表示"] + sorted(df_y["月"].unique().tolist())
    sel_month = st.sidebar.selectbox("📆 ② 月を選択", month_options)
    df_m = df_y if sel_month == "すべて表示" else df_y[df_y["月"] == sel_month]

    item_list = ["すべて表示"] + sorted(df_m["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 ③ 商品名を選択", item_list)
    
    if sel_item != "すべて表示":
        df_i = df_m[df_m["商品名"] == sel_item]
        size_list = ["すべて表示"] + sorted(df_i["サイズ"].unique().tolist())
        sel_size = st.sidebar.selectbox("📏 ④ サイズを選択", size_list)
        
        if sel_size != "すべて表示":
            df_s = df_i[df_i["サイズ"] == sel_size]
            loc_list = ["すべて表示"] + sorted(df_s["地名"].unique().tolist())
            sel_loc = st.sidebar.selectbox("📍 ⑤ 地名を選択", loc_list)
        else:
            df_s = df_i
            sel_loc = "すべて表示"
    else:
        df_i = df_m
        sel_size = "すべて表示"
        sel_loc = "すべて表示"

    # フィルタリング適用
    df_final = df_m.copy()
    if sel_item != "すべて表示": df_final = df_final[df_final["商品名"] == sel_item]
    if sel_size != "すべて表示": df_final = df_final[df_final["サイズ"] == sel_size]
    if sel_loc != "すべて表示": df_final = df_final[df_final["地名"] == sel_loc]

# --- メイン表示 ---
    st.divider()

    # タブを5つに拡張
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 傾向・シェア", "📈 トレンド・前年比較", "🏆 ABC分析", "⚠️ 不動在庫・安全在庫", "🔢 履歴明細"
    ])

    with tab1:
        # (既存のヒートマップ、地名シェア、曜日別グラフ)
        st.subheader("📦 商品・サイズ別の需要集中度")
        summary_heat = df_final.groupby(["商品名", "サイズ"])["数量"].sum().reset_index()
        fig_heat = px.density_heatmap(summary_heat, x="サイズ", y="商品名", z="数量", text_auto=True, color_continuous_scale="Viridis")
        st.plotly_chart(fig_heat, use_container_width=True)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("📍 地名別出荷シェア")
            fig_pie = px.pie(df_final, values='数量', names='地名', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_g2:
            st.subheader("📅 曜日別の出荷傾向")
            df_final["曜日"] = df_final["日時"].dt.day_name()
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_jp = {'Monday': '月', 'Tuesday': '火', 'Wednesday': '水', 'Thursday': '木', 'Friday': '金', 'Saturday': '土', 'Sunday': '日'}
            summary_day = df_final.groupby("曜日")["数量"].sum().reindex(day_order).reset_index()
            summary_day["曜日"] = summary_day["曜日"].map(day_jp)
            fig_day = px.bar(summary_day, x="曜日", y="数量", text_auto=True, color_discrete_sequence=['#FF8C00'])
            st.plotly_chart(fig_day, use_container_width=True)

    with tab2:
        st.subheader("📈 時系列トレンド（前年比較）")
        # 当年と前年の比較用データ作成
        df_out["年月日"] = df_out["日時"].dt.strftime('%m-%d')
        df_this_year = df_out[df_out["年"] == sel_year].groupby("年月日")["数量"].sum().reset_index()
        df_last_year = df_out[df_out["年"] == (sel_year - 1)].groupby("年月日")["数量"].sum().reset_index()
        
        df_compare = pd.merge(df_this_year, df_last_year, on="年月日", how="outer", suffixes=('_今年', '_前年')).sort_values("年月日").fillna(0)
        fig_compare = px.line(df_compare, x="年月日", y=["数量_今年", "数量_前年"], title=f"{sel_year}年 vs {sel_year-1}年 の出荷推移")
        st.plotly_chart(fig_compare, use_container_width=True)

    with tab3:
        st.subheader("🏆 ABC分析（重要商品の特定）")
        # 出荷数量でランク付け
        abc_df = df_final.groupby("商品名")["数量"].sum().sort_values(ascending=False).reset_index()
        abc_df["累計構成比"] = (abc_df["数量"].cumsum() / abc_df["数量"].sum()) * 100
        abc_df["ランク"] = abc_df["累計構成比"].apply(lambda x: "A (最重要)" if x <= 80 else ("B (重要)" if x <= 95 else "C (一般)"))
        
        col_a1, col_a2 = st.columns([2, 1])
        with col_a1:
            fig_abc = px.bar(abc_df, x="商品名", y="数量", color="ランク", title="出荷数パレート図",
                             color_discrete_map={"A (最重要)": "#EF553B", "B (重要)": "#636EFA", "C (一般)": "#00CC96"})
            st.plotly_chart(fig_abc, use_container_width=True)
        with col_a2:
            st.write("ランク別集計")
            st.dataframe(abc_df[["ランク", "商品名", "数量"]], hide_index=True)

    with tab4:
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.subheader("⚠️ デッドストック候補")
            # 選択期間中に出荷が0の商品（マスターと照らし合わせるのが理想ですが、今回はログ全体と比較）
            all_items = set(df_out["商品名"].unique())
            active_items = set(df_final["商品名"].unique())
            dead_items = all_items - active_items
            if dead_items:
                st.warning(f"以下の {len(dead_items)} 商品はこの期間に出荷がありません")
                st.write(list(dead_items))
            else:
                st.success("全商品に出荷がありました！")
        
        with col_w2:
            st.subheader("💡 安全在庫の目安（計算）")
            # 簡易計算：平均出荷量 + 2σ（標準偏差）
            safety_df = df_final.groupby("商品名")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
            safety_df["推奨・安全在庫数"] = (safety_df["mean"] + 2 * safety_df["std"]).round(0)
            st.write("過去の変動から計算した、欠品させないための最低在庫目安です。")
            st.dataframe(safety_df[["商品名", "推奨・安全在庫数"]].sort_values("推奨・安全在庫数", ascending=False), hide_index=True)

    with tab5:
        st.subheader("🔢 履歴明細")
        view_df = df_final[["日時", "商品名", "サイズ", "地名", "数量", "担当者"]].copy()
        view_df["日時"] = view_df["日時"].dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(view_df.sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
