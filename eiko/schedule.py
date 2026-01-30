import schedule
import time

def job():
    print("予定の時間だよ！仕事中...")

# 10分おきに実行
schedule.every(10).minutes.do(job)
# 毎日10:30に実行
schedule.every().day.at("10:30").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
