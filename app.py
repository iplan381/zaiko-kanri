# --- 4. メイン：在庫一覧 ---
st.title("📦 在庫管理")
st.subheader("📊 在庫一覧")

# 検索条件
c1, c2, c3, c4 = st.columns(4)
with c1: s_item = st.selectbox("検索:商品名", get_opts(df_stock["商品名"]))
with c2: s_size = st.selectbox("検索:サイズ", get_opts(df_stock["サイズ"]))
with c3:
    # 💡 地名の検索機能を強化（キーワード検索 + プルダウン）
    search_loc = st.text_input("地名をキーワード検索", placeholder="例: 青森")
    s_loc = st.selectbox("またはプルダウンで選択", get_opts(df_stock["地名"]))
with c4: s_vendor = st.selectbox("検索:取引先", get_opts(df_stock["取引先"]))

df_disp = df_stock.copy()

# フィルタリング処理
if s_item != "すべて": 
    df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": 
    df_disp = df_disp[df_disp["サイズ"] == s_size]

# 💡 地名の絞り込み（キーワード or プルダウン）
if search_loc:
    # 入力された文字が含まれている地名をすべて抽出
    df_disp = df_disp[df_disp["地名"].str.contains(search_loc, na=False)]
elif s_loc != "すべて":
    df_disp = df_disp[df_disp["地名"] == s_loc]

if s_vendor != "すべて": 
    df_disp = df_disp[df_disp["取引先"] == s_vendor]

# 一覧表示（選択機能付き）
event = st.dataframe(df_disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
