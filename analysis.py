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

@st.cache_data(ttl=60) # 更新を反映しやすくするため一時的に短くします
def get_github_data(file_path):
    try:
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = res.json()
            csv_text = base64.b64decode(content["content"]).decode("utf-8")
            # データ読み込み時に不要な空白を削除
            df = pd.read_csv(StringIO(csv_text)).fillna("")
            return df
    except Exception as e:
        st.error(f"GitHub接続エラー: {e}")
    return pd.DataFrame()

df_log_raw = get_github_data(FILE_PATH_LOG)

st.title("📈 階層別 在庫動態分析")

if not df_log_raw.empty:
    # --- データ前処理 (安全策) ---
    df = df_log_raw.copy()
    # 全列に対して前後の空白を削除
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    df["日時"] = pd.to_datetime(df["日時"], errors='coerce')
    df = df.dropna(subset=["日時"]) # 日付が不正な行を除外
    df["年"] = df["日時"].dt.year
    df["月"] = df["日時"].dt.month
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ抽出
    df_out_all = df[df["区分"].astype(str).str.contains("出庫")].copy()
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
    
    # 選択された年のデータ
    df_this_year = df_out_all[df_out_all["年"] == sel_year]

    # --- 商品名での絞り込み ---
    item_list = ["すべて表示"] + sorted(df_this_year["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 商品名で絞り込む", item_list)
    
    work_df = df_this_year.copy()
    if sel_item != "すべて表示":
        work_df = work_df[work_df["商品名"] == sel_item]
    
    # メイン表示月(df_final)の作成
    if sel_month_str != "すべて表示":
        m_int = int(sel_month_str.replace("月", ""))
        df_final = work_df[work_df["月"] == m_int]
    else:
        df_final = work_df

    # --- タブ作成 (確実に表示させる) ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 傾向・シェア", "📈 トレンド推移", "⚖️ 2ヶ月間 比較分析", 
        "🏆 ABC分析", "⚠️ 不動・安全在庫", "🔢 履歴明細"
    ])

    # --- ⚖️ Tab 3: 比較分析 (ここを最優先で処理) ---
    with tab3:
        m1_val = int(compare_m1.replace("月", ""))
        m2_val = int(compare_m2.replace("月", ""))
        
        c_df1 = work_df[work_df["月"] == m1_val]
        c_df2 = work_df[work_df["月"] == m2_val]
        
        st.subheader(f"⚖️ {compare_m1} vs {compare_m2} ({sel_year}年)")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        q1, q2 = c_df1["数量"].sum(), c_df2["数量"].sum()
        kpi1.metric(f"{compare_m1} 合計", f"{int(q1):,}")
        kpi2.metric(f"{compare_m2} 合計", f"{int(q2):,}")
        kpi3.metric("差分", f"{int(q2-q1):+,}")

        if not c_df1.empty or not c_df2.empty:
            # グラフ
            d1 = c_df1.groupby(c_df1["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時":"日","数量":compare_m1})
            d2 = c_df2.groupby(c_df2["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時":"日","数量":compare_m2})
            m_graph = pd.merge(d1, d2, on="日", how="outer").fillna(0).sort_values("日")
            st.plotly_chart(px.line(m_graph, x="日", y=[compare_m1, compare_m2], markers=True), use_container_width=True)
            
            # 明細表
            st.write("📋 **商品別の増減内訳**")
            i1 = c_df1.groupby("項目詳細")["数量"].sum().reset_index().rename(columns={"数量":f"{compare_m1}"})
            i2 = c_df2.groupby("項目詳細")["数量"].sum().reset_index().rename(columns={"数量":f"{compare_m2}"})
            diff_df = pd.merge(i1, i2, on="項目詳細", how="outer").fillna(0)
            diff_df["増減"] = diff_df[f"{compare_m2}"] - diff_df[f"{compare_m1}"]
            st.dataframe(diff_df.sort_values("増減", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.warning("選択された2ヶ月間のデータが見つかりません。")

    # --- 他のタブ (データがあるときだけ中身を表示) ---
    if not df_final.empty:
        with tab1:
            st.subheader("📦 項目別ランキング (Top20)")
            res = df_final.groupby("項目詳細")["数量"].sum().reset_index().sort_values("数量", ascending=False).head(20)
            st.plotly_chart(px.bar(res, x="数量", y="項目詳細", orientation='h', text_auto=True), use_container_width=True)
        with tab2:
            st.subheader("📈 トレンド")
            daily = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            st.plotly_chart(px.line(daily, x="日時", y="数量", markers=True), use_container_width=True)
        with tab4:
            st.subheader("🏆 ABC分析")
            abc = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
            abc["累積%"] = abc["数量"].cumsum() / abc["数量"].sum() * 100
            abc["ランク"] = abc["累積%"].apply(lambda x: "A" if x<=80 else "B" if x<=95 else "C")
            st.plotly_chart(px.bar(abc, x="数量", y="項目詳細", color="ランク", orientation='h'), use_container_width=True)
        with tab5:
            st.subheader("⚠️ 不動・推奨在庫")
            c_a, c_b = st.columns(2)
            dead = work_df.groupby("項目詳細")["日時"].max().reset_index()
            dead["経過日数"] = (pd.Timestamp.now() - dead["日時"]).dt.days
            c_a.write("不動在庫（最終出荷からの日数）")
            c_a.dataframe(dead.sort_values("経過日数", ascending=False), use_container_width=True)
            sf = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index()
            sf["推奨"] = (sf["mean"] + 2*sf["std"]).fillna(0).round(0)
            c_b.write("推奨在庫目安")
            c_b.dataframe(sf[["項目詳細", "推奨"]], use_container_width=True)
        with tab6:
            st.subheader("🔢 履歴明細")
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量"]].sort_values("日時", ascending=False), use_container_width=True)
    else:
        # df_finalが空の場合、各タブにメッセージを表示
        empty_msg = f"選択された条件（{sel_year}年 {sel_month_str}）に該当するデータがありません。"
        for t in [tab1, tab2, tab4, tab5, tab6]:
            with t: st.info(empty_msg)

else:
    st.error("GitHubからデータを取得できませんでした。CSVの中身が空か、トークンの権限、ファイル名を確認してください。")
