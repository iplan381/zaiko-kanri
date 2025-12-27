import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import requests
from io import StringIO

# --- 設定：ご自身のリポジトリ名に変更してください ---
REPO_NAME = "ご自身のユーザー名/zaiko-kanri"
FILE_PATH = "stock.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# あなたが元々定義していたリスト
USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- GitHubからCSVを読み書きするための関数 ---
def get_github_data():
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        df = pd.read_csv(StringIO(csv_text))
        return df.fillna(""), content["sha"]
    else:
        st.error("GitHub上のファイルが見つかりません。リポジトリ名とファイル名を確認してください。")
        st.stop()

def update_github_data(df, sha):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    data = {
        "message": f"Update stock: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"),
        "sha": sha
    }
    res = requests.put(url, headers=headers, json=data)
    return res.status_code == 200

# 3. 並び替え（あいうえお順に整列）
def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

# データの読み込み
df_stock, current_sha = get_github_data()

st.title("📦 在庫管理システム")

# サイドバー：登録（元の形を維持＋GitHub書き込み機能）
with st.sidebar:
    st.header("✨ 新商品登録")
    new_item = st.text_input("商品名")
    new_size = st.selectbox("サイズ", SIZES_MASTER)
    new_loc = st.text_input("地名")
    new_vendor = st.selectbox("取引先", VENDORS_MASTER)
    new_stock = st.number_input("初期在庫", min_value=0, value=0)
    new_alert = st.number_input("アラート基準", min_value=0, value=5)

    if st.button("登録"):
        if new_item and new_loc:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_row = pd.DataFrame([{
                "最終更新日": now, "商品名": new_item, "サイズ": new_size,
                "地名": new_loc, "在庫数": new_stock, "アラート基準": new_alert, "取引先": new_vendor
            }])
            updated_df = pd.concat([df_stock, new_row], ignore_index=True)
            
            if update_github_data(updated_df, current_sha):
                st.success("GitHub上のデータを更新しました！")
                st.rerun()
            else:
                st.error("GitHubへの保存に失敗しました。")

# メイン表示（地名をあいうえお順に）
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)

with c1:
    s_item = st.selectbox("商品名", get_opts(df_stock["商品名"]))
with c2:
    s_size = st.selectbox("サイズ", get_opts(df_stock["サイズ"]))
with c3:
    # これで 青森→北海道→和歌山 の順になります
    s_loc = st.selectbox("地名", get_opts(df_stock["地名"]))
with c4:
    s_vendor = st.selectbox("取引先", get_opts(df_stock["取引先"]))

# 絞り込み処理
df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc != "すべて": df_disp = df_disp[df_disp["地名"] == s_loc]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

# 表の表示
st.dataframe(df_disp, use_container_width=True, hide_index=True)
