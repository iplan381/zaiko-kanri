import streamlit as st
import schedule
import time

# 画面にタイトルを表示
st.title("エイコースケジュール")
st.write("アプリは正常に起動しています！")

def job():
    # ログとして画面に出力（実際にはバックグラウンドで動くよ）
    st.toast("予定の時間だよ！仕事中...")

# スケジュールの設定
if 'scheduled' not in st.session_state:
    schedule.every(10).minutes.do(job)
    schedule.every().day.at("10:30").do(job)
    st.session_state['scheduled'] = True

st.write("現在のタスクを監視中...")

# Streamlitでは無限ループを使わずに、
# 最後にこれを入れるか、ボタンで実行させるのが一般的だよ
if st.button('今すぐタスクをチェック'):
    schedule.run_pending()
    st.success("チェック完了！")
