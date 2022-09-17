import streamlit as st
from .base import BasePage


class TopPage(BasePage):
    def render(self):
        col1, mid = st.columns([1, 10])
        with col1:
            st.image("./tsptw/assets/medical_oushin_car_woman.png", width=120)
        st.markdown(
            """
            ## 往診経路最適化さん
            組合せ最適化問題の一種である「時間枠付き[巡回セールスマン問題](https://ja.wikipedia.org/wiki/%E5%B7%A1%E5%9B%9E%E3%82%BB%E3%83%BC%E3%83%AB%E3%82%B9%E3%83%9E%E3%83%B3%E5%95%8F%E9%A1%8C)(Traveling Salesman Problem with Time Windows)」に帰着させることにより，所要時間が最短となる巡回経路を機械的に提案します．

            ### 特徴
             - 患者宅での訪問可能時間帯（例：10時〜12時など）の指定が可能！
             - 診察予定時間の設定で精度アップ！
             - 最大25箇所の経由地点に対応！

            ### 使い方
             1. 左メニューからGoogleアカウントでログイン
             1. 「経由地点」ページにて，経由地点を登録してください
             1. 「ルート探索」ページにて，登録した経由地点を選択し「ルート探索」を実行してください
            """
        )
        st.image(
            "./tsptw/assets/3559926564_Illust__of_many_markers_on_GoogleMap_with_a_directed_graph_which_has_a_transparent_background.png",
        )
