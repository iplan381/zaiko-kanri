# --- ⚖️ Tab 3: 比較分析 (強化版) ---
        with tab3:
            st.subheader(f"⚖️ {compare_m1} と {compare_m2} の直接比較 ({sel_year}年)")
            m1_int = int(compare_m1.replace("月", ""))
            m2_int = int(compare_m2.replace("月", ""))
            
            comp_df1 = work_df[work_df["月"] == m1_int]
            comp_df2 = work_df[work_df["月"] == m2_int]
            
            mc1, mc2, mc3 = st.columns(3)
            q1, q2 = comp_df1["数量"].sum(), comp_df2["数量"].sum()
            mc1.metric(f"{compare_m1} 合計", f"{int(q1):,}")
            mc2.metric(f"{compare_m2} 合計", f"{int(q2):,}")
            mc3.metric("合計の差分", f"{int(q2-q1):+,}")

            st.divider()
            
            # 日次推移のグラフ
            st.write("📝 **日次推移の重ね合わせ**")
            d1 = comp_df1.groupby(comp_df1["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時":"日", "数量":compare_m1})
            d2 = comp_df2.groupby(comp_df2["日時"].dt.day)["数量"].sum().reset_index().rename(columns={"日時":"日", "数量":compare_m2})
            merged_d = pd.merge(d1, d2, on="日", how="outer").fillna(0).sort_values("日")
            
            if not merged_d.empty:
                fig_c = px.line(merged_d, x="日", y=[compare_m1, compare_m2], markers=True)
                st.plotly_chart(fig_c, use_container_width=True)
            
            st.divider()
            
            # 商品別増減明細の作成
            st.write("📋 **項目別 増減明細**")
            item_m1 = comp_df1.groupby("項目詳細")["数量"].sum().reset_index().rename(columns={"数量": f"{compare_m1}実績"})
            item_m2 = comp_df2.groupby("項目詳細")["数量"].sum().reset_index().rename(columns={"数量": f"{compare_m2}実績"})
            
            # 2つの月のデータを商品ごとに合体
            diff_table = pd.merge(item_m1, item_m2, on="項目詳細", how="outer").fillna(0)
            diff_table["増減数"] = diff_table[f"{compare_m2}実績"] - diff_table[f"{compare_m1}実績"]
            
            # 状態ラベルの追加
            def get_status(x):
                if x > 0: return "📈 増加"
                elif x < 0: return "📉 減少"
                return "💨 変化なし"
            
            diff_table["状態"] = diff_table["増減数"].apply(get_status)
            
            # 数字が大きい順（変化が大きい順）に並び替えて表示
            st.dataframe(
                diff_table.sort_values("増減数", ascending=False), 
                use_container_width=True, 
                hide_index=True
            )
