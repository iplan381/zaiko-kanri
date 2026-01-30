import pandas as pd
import os
from sklearn.linear_model import LinearRegression
import joblib

# ファイルの場所を特定する（階層を合わせる）
base_dir = os.path.dirname(__file__)
data_path = os.path.join(base_dir, '../data/training_log.csv')
model_dir = os.path.join(base_dir, '../models')

# modelsフォルダがなければ作る
os.makedirs(model_dir, exist_ok=True)

# 1. データの読み込み
df = pd.read_csv(data_path)

# 2. 学習（距離、ペース、心拍数からタイムを予測）
X = df[['distance', 'avg_pace', 'avg_hr']]
y = df['race_time']
model = LinearRegression()
model.fit(X, y)

# 3. 学習済みモデルを保存
joblib.dump(model, os.path.join(model_dir, 'marathon_model.pkl'))

print("AIの学習が完了し、modelsフォルダに保存されました！")
