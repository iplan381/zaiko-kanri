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

@st.cache_data(ttl=600)
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

    # --- 🔍 サイドバー設定 ---
    st.sidebar.header("🔍 基本表示条件")
    year_list = sorted(df_out_all["年"].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 表示年を選択", year_list)
    
    month_options = [f"{m}月" for m in range(1, 13)]
    sel_month_str = st.sidebar.selectbox("📆 メイン表示月 (各タブ用)", ["すべて表示"] + month_options)

    st.sidebar.divider()
    st.sidebar.header("⚖️ 2ヶ月間 比較設定")
    compare_m1 = st.sidebar.selectbox("比較月A", month_options, index=0)
    compare_m2 = st.sidebar.selectbox("比較月B", month_options, index=1)
    
    # フィルタリングのベース
    df_this_year = df_out_all[df_out_all["年"] == sel_year]

    # --- 商品などの絞り込み ---
    st.sidebar.divider()
    item_list = ["すべて表示"] + sorted(df_this_year["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 商品名で絞り込む", item_list)
    
    work_df = df_this_year.copy()
    if sel_item != "すべて表示":
        work_df = work_df[work_df["商品名"] == sel_item]
    
    # メイン表示用のデータ作成 (タブ1,2,4,5,6用)
    if sel_month_str != "すべて表示":
        m_int = int(sel_month_str.replace("月", ""))
        df_final = work_df[work_df["月"] == m_int]
    else:
        df_final = work_df

    # --- タブの作成 (ここを外に出すことで確実に表示) ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 傾向・シェア", "📈 トレンド推移", "⚖️ 2ヶ月間 比較分析", 
        "🏆 ABC分析", "⚠️ 不動・安全在庫", "🔢 履歴明細"
    ])

    # --- ⚖️ Tab 3: 比較分析 (グラフ + 増減明細) ---
    with tab3:
        st.subheader(f"⚖️ {compare_m1} と {compare_m2} の直接比較 ({sel_year}年)")
        m1_int = int(compare_m1.replace("月", ""))
        m2_int = int(compare_m2.replace("月", ""))
        
        comp_df1 = work_df[work_df["月"] == m1_int]
        comp_df2 = work_df[work_df["月"] == m2_int]
        
        mc1, mc2, mc3 = st.columns(3)
        q1, q2 = comp_df1["数量"].sum(), comp_df2["数量"].sum()
        mc1.metric(f"{compare_m1} 合計出荷", f"{int(q1):,}")
        mc2.metric(f"{compare_m2} 合計出荷", f"{int(q2):,}")
        mc3.metric("2ヶ月の差分", f"{int(q2-q1):+,}")

        st.divider()
        
        # グラフ表示
        st.write("📝 **日次推移の重ね合わせ**")
        d1 = comp_df1.groupby(comp_df1["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時":"日", "数量":compare_m1})
        d2 = comp_df2.groupby(comp_df2["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時":"日", "数量":compare_m2})
        merged_d = pd.merge(d1, d2, on="日", how="outer").fillna(0).sort_values("日")
        
        if not merged_d.empty:
            fig_c = px.line(merged_d, x="日", y=[compare_m1, compare_m2], markers=True)
            st.plotly_chart(fig_c, use_container_width=True)
        
        st.divider()
        
        # 商品別増減明細
        st.write("📋 **項目別 増減明細**")
        item_m1 = comp_df1.groupby("項目詳細")["数量"].sum().reset_index().rename(columns={"数量": f"{compare_m1}実績"})
        item_m2 = comp_df2.groupby("項目詳細")["数量"].sum().reset_index().rename(columns={"数量": f"{compare_m2}実績"})
        
        diff_table = pd.merge(item_m1, item_m2, on="項目詳細", how="outer").fillna(0)
        diff_table["増減数"] = diff_table[f"{compare_m2}実績"] - diff_table[f"{compare_m1}実績"]
        
        def get_status(x):
            if x > 0: return "📈 増加"
            elif x < 0: return "📉 減少"
            return "💨 変化なし"
        
        diff_table["状態"] = diff_table["増減数"].apply(get_status)
        st.dataframe(diff_table.sort_values("増減数", ascending=False), use_container_width=True, hide_index=True)

    # --- 他のタブ (データがある場合のみ中身を表示) ---
    if not df_final.empty:
        with tab1:
            st.subheader("📦 項目別ランキング (上位20件)")
            res = df_final.groupby("項目詳細")["数量"].sum().reset_index().sort_values("数量", ascending=False).head(20)
            st.plotly_chart(px.bar(res, x="数量", y="項目詳細", orientation='h', text_auto=True), use_container_width=True)

        with tab2:
            st.subheader("📈 日次トレンド")
            daily = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            st.plotly_chart(px.line(daily, x="日時", y="数量", markers=True), use_container_width=True)
            st.divider()
            st.subheader(f"📊 {sel_year}年 月別出荷ボリューム")
            m_sum = work_df.groupby("月")["数量"].sum().reset_index()
            m_sum["月表示"] = m_sum["月"].astype(str) + "月"
            st.plotly_chart(px.bar(m_sum, x="月表示", y="数量", text_auto=True), use_container_width=True)

        with tab4:
            st.subheader("🏆 ABC分析")
            abc = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
            abc["累積%"] = abc["数量"].cumsum() / abc["数量"].sum() * 100
            abc["ランク"] = abc["累積%"].apply(lambda x: "A" if x<=80 else "B" if x<=95 else "C")
            st.plotly_chart(px.bar(abc, x="数量", y="項目詳細", color="ランク", orientation='h', 
                                   color_discrete_map={"A":"#D55E00","B":"#009E73","C":"#F0E442"}), use_container_width=True)

        with tab5:
            st.subheader("⚠️ 在庫分析")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**不動在庫 (長い間動いていない項目)**")
                dead = work_df.groupby("項目詳細")["日時"].max().reset_index()
                dead["経過日数"] = (pd.Timestamp.now() - dead["日時"]).dt.days
                st.dataframe(dead.sort_values("経過日数", ascending=False), use_container_width=True, hide_index=True)
            with col_b:
                st.write("**推奨在庫数 (統計的計算)**")
                sf = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index()
                sf["推奨在庫"] = (sf["mean"] + 2 * sf["std"]).fillna(0).round(0)
                st.dataframe(sf[["項目詳細", "推奨在庫"]].sort_values("推奨在庫", ascending=False), use_container_width=True, hide_index=True)

        with tab6:
            st.subheader("🔢 履歴明細")
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        # メイン月が空の場合のメッセージ
        msg = "メイン表示月のデータがないため、このタブは表示できません。サイドバーで月を選択してください。"
        with tab1: st.info(msg)
        with tab2: st.info(msg)
        with tab4: st.info(msg)
        with tab5: st.info(msg)
        with tab6: st.info(msg)

else:
    st.error("データの読み込みに失敗しました。GitHubの設定を確認してください。")
