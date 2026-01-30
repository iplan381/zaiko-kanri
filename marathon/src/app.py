import streamlit as st
import pandas as pd
import os
from sklearn.linear_model import LinearRegression
from datetime import datetime

st.set_page_config(page_title="マラソン予測AI", layout="centered")

st.title("🏃 マラソンタイム予測AI & 練習ログ")

# --- ファイルパスの設定 ---
base_dir = os.path.dirname(__file__)
data_path = os.path.join(base_dir, "..", "data", "training_log.csv")

# --- 1. データの読み込み ---
if os.path.exists(data_path):
    df = pd.read_csv(data_path)
    
    # --- 2. 新しい記録を入力する場所（ここを追加！） ---
    with st.expander("📝 ナイキランの記録を入力する"):
        with st.form("log_form"):
            new_dist = st.number_input("走行距離 (km)", value=10.0)
            new_pace = st.number_input("平均ペース (秒/km) ※5分0秒なら300", value=300)
            new_hr = st.number_input("平均心拍数", value=145)
            new_race = st.number_input("その時のフル予想タイム(分) ※任意", value=240)
            
            if st.form_submit_button("記録を保存する"):
                new_data = pd.DataFrame([[new_dist, new_pace, new_hr, new_race]], columns=df.columns)
                df = pd.concat([df, new_data], ignore_index=True)
                df.to_csv(data_path, index=False)
                st.success("CSVに保存したよ！Reboot後にAIが学習し直します。")

    # --- 3. AIの学習 ---
    X = df[['distance', 'avg_pace', 'avg_hr']]
    y = df['race_time']
    model = LinearRegression().fit(X, y)

    # --- 4. タイム予測フォーム ---
    st.subheader("🏁 未来のタイムを予測")
    with st.form("predict_form"):
        dist = st.slider("今月の目標走行距離 (km)", 0, 500, int(df['distance'].mean()))
        pace = st.number_input("目標ペース (秒/km)", value=int(df['avg_pace'].mean()))
        hr = st.slider("想定心拍数", 100, 200, int(df['avg_hr'].mean()))
        submitted = st.form_submit_button("予測する！")

    if submitted:
        pred = model.predict([[dist, pace, hr]])
        h = int(pred[0] // 60)
        m = int(pred[0] % 60)
        st.balloons()
        st.success(f"予測タイム: {h}時間{m}分")
        
    # 現在のデータ一覧を表示
    if st.checkbox("保存されているデータを見る"):
        st.write(df)

else:
    st.error("練習データ(CSV)が見つかりません。")
