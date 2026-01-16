# --- 💡 ここからメイン表示（正しいインデント位置） ---
    st.divider()

    if not df_final.empty:
        # 1. 基本単位（ユニークキー）の作成：全項目を結合
        df_final["項目詳細"] = df_final["商品名"] + " | " + df_final["サイズ"] + " | " + df_final["地名"]

        # KPIカード
        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("期間内 合計出荷", f"{int(df_final['数量'].sum()):,}")
        with k2:
            st.metric("稼働詳細項目数", f"{df_final['項目詳細'].nunique()}")
        with k3:
            avg_val = round(df_final["数量"].mean(), 1)
            st.metric("1件あたりの平均量", f"{avg_val}")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 傾向・シェア", "📈 トレンド・前年比較", "🏆 ABC分析", "⚠️ 不動在庫・安全在庫", "🔢 履歴明細"
        ])

        with tab1:
            st.subheader("📦 詳細項目別（商品・サイズ・地名）ランキング")
            # 項目が多い場合に備え、上位30件を表示
            summary_full = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=True).tail(30).reset_index()
            fig_full = px.bar(summary_full, y="項目詳細", x="数量", orientation='h', 
                             text_auto=True, color="数量", color_continuous_scale="Viridis")
            st.plotly_chart(fig_full, use_container_width=True)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("📍 地名別出荷シェア")
                fig_pie = px.pie(df_final, values='数量', names='地名', hole=0.4, 
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_g2:
                st.subheader("📅 曜日別の出荷傾向")
                df_final["曜日名"] = df_final["日時"].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_jp = {'Monday': '月', 'Tuesday': '火', 'Wednesday': '水', 'Thursday': '木', 'Friday': '金', 'Saturday': '土', 'Sunday': '日'}
                summary_day = df_final.groupby("曜日名")["数量"].sum().reindex(day_order).reset_index()
                summary_day["曜日"] = summary_day["曜日名"].map(day_jp)
                fig_day = px.bar(summary_day, x="曜日", y="数量", text_auto=True, color_discrete_sequence=['#FF8C00'])
                st.plotly_chart(fig_day, use_container_width=True)

        with tab2:
            st.subheader("📈 時系列推移")
            df_trend = df_final.groupby(df_final["日時"].dt.date)["数量"].sum().reset_index()
            fig_trend = px.line(df_trend, x="日時", y="数量", markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)

        with tab3:
            st.subheader("🏆 ABC分析（詳細項目別）")
            abc_df = df_final.groupby("項目詳細")["数量"].sum().sort_values(ascending=False).reset_index()
            abc_df["累計構成比"] = (abc_df["数量"].cumsum() / abc_df["数量"].sum()) * 100
            abc_df["ランク"] = abc_df["累計構成比"].apply(lambda x: "A (最重要)" if x <= 80 else ("B (重要)" if x <= 95 else "C (一般)"))
            fig_abc = px.bar(abc_df, x="項目詳細", y="数量", color="ランク", title="詳細項目パレート図")
            st.plotly_chart(fig_abc, use_container_width=True)

        with tab4:
            st.subheader("💡 詳細別・安全在庫の目安")
            safety_df = df_final.groupby("項目詳細")["数量"].agg(['mean', 'std']).reset_index().fillna(0)
            safety_df["推奨在庫数"] = (safety_df["mean"] + 2 * safety_df["std"]).round(0)
            st.dataframe(safety_df[["項目詳細", "推奨在庫数"]].sort_values("推奨在庫数", ascending=False), 
                         use_container_width=True, hide_index=True)

        with tab5:
            st.subheader("🔢 履歴明細")
            view_df = df_final[["日時", "商品名", "サイズ", "地名", "数量", "担当者"]].copy()
            view_df["日時"] = view_df["日時"].dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(view_df.sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("選択された条件に一致する出荷データがありません。サイドバーで条件を変えてみてください。")

else:
    st.warning("データが読み込めません。")
