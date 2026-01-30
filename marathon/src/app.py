import streamlit as st
import pandas as pd
import os
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="マラソン予測AI", layout="centered")

st.title("🏃 マラソンタイム予測AI")
st.write("今の練習状況からフルマラソンのタイムを予測します。")

# --- ファイルパスの探索（最強設定） ---
# 候補1: app.pyから見た相対パス
path1 = os.path.join(os.path.dirname(__file__), "..", "data", "training_log.csv")
# 候補2: リポジトリのルートからのパス
path2 = "marathon/data/training_log.csv"

if os.path.exists(path1):
    data_path = path1
elif os.path.exists(path2):
    data_path = path2
else:
    data_path = None

# --- 実行セクション ---
if data_path:
    # データを読み込む
    df = pd.read_csv(data_path)
    
    # AIの学習
    X = df[['distance', 'avg_pace', 'avg_hr']]
    y = df['race_time']
    model = LinearRegression().fit(X, y)

    # 入力フォーム
    with st.form("my_form"):
        st.subheader("今のコンディションを入力")
        dist = st.slider("今月の走行距離 (km)", 0, 500, 200)
        pace = st.number_input("平均ペース (秒/km) ※5分0秒なら300", value=300)
        hr = st.slider("平均心拍数", 100, 200, 145)
        submitted = st.form_submit_button("予測する！")

    if submitted:
        pred = model.predict([[dist, pace, hr]])
        h = int(pred[0] // 60)
        m = int(pred[0] % 60)
        st.balloons() # 成功のお祝い
        st.success(f"予測タイム: {h}時間{m}分 ({pred[0]:.1f}分)")

else:
    # ここがエラーの時の表示（デバッグ情報付き）
    st.error("🚨 練習データ(CSV)が見つかりません。")
    
    with st.expander("デバッグ情報を表示（ここをスクショして教えて！）"):
        st.write(f"現在の作業ディレクトリ: {os.getcwd()}")
        st.write(f"app.pyのある場所: {os.path.dirname(__file__)}")
        st.write("見えているファイル一覧:")
        # リポジトリの中身を再帰的に表示
        file_list = []
        for root, dirs, files in os.walk("."):
            for file in files:
                file_list.append(os.path.join(root, file))
        st.write(file_list)
