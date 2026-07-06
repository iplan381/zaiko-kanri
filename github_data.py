import base64
from io import StringIO

import pandas as pd
import requests
import streamlit as st

REPO_NAME = st.secrets.get("REPO_NAME", "iplan381/zaiko-kanri")
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]


def get_github_data(file_path, default_cols=None, fillna=True):
    """GitHubリポジトリ内のCSVファイルを読み込み、(DataFrame, sha) を返す。

    default_cols を渡すと、不足している列を "" で補い、その列順に揃える。
    fillna=False にすると欠損値の "" 埋めをスキップする（order_app.py互換）。
    """
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        empty = pd.DataFrame(columns=default_cols) if default_cols is not None else pd.DataFrame()
        return empty, None

    content = res.json()
    sha = content["sha"]
    csv_text = base64.b64decode(content["content"]).decode("utf-8")

    if default_cols is not None and not csv_text.strip():
        return pd.DataFrame(columns=default_cols), sha

    df = pd.read_csv(StringIO(csv_text))

    if default_cols is not None:
        for col in default_cols:
            if col not in df.columns:
                df[col] = ""
        df = df[default_cols]

    if fillna:
        df = df.fillna("")

    return df, sha


def update_github_data(file_path, df, sha, message):
    """DataFrameをCSVとしてGitHubリポジトリにコミットする。HTTPステータスコードを返す。"""
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    data = {
        "message": message,
        "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
    }
    res = requests.put(url, headers=headers, json=data)
    return res.status_code
