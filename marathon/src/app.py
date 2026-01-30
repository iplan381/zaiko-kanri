import streamlit as st
import pandas as pd
import os
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="マラソン予測AI", layout="centered")

st.title("🏃 マラソンタイム予測AI")
st.write("今の練習状況からフルマラソンのタイムを予測します。")

# データの読み込み（パスを調整）
base_dir = os.path.dirname(__file__)
data_path = os.path.join(base_dir, "..", "data", "training_log.csv")

if os.path.exists(data_path):
    df = pd.read_csv(data_path)
    
    # AIの学習
    X = df[['distance', 'avg_pace', 'avg_hr']]
    y = df['race_time']
    model = LinearRegression().fit(X, y)

    # 入力フォーム
    with st.form("my_form"):
        dist = st.slider("今月の走行距離 (km)", 0, 500, 200)
        pace = st.number_input("平均ペース (秒/km) ※5分0秒なら300", value=300)
        hr = st.slider("平均心拍数", 100, 200, 145)
        submitted = st.form_submit_button("予測する！")

    if submitted:
        pred = model.predict([[dist, pace, hr]])
        # 分を「○時間○分」に変換
        h = int(pred[0] // 60)
        m = int(pred[0] % 60)
        st.success(f"予測タイム: {h}時間{m}分 ({pred[0]:.1f}分)")
else:
    st.error("練習データ(CSV)が見つかりません。")
