import streamlit as st

from tsptw.pages.base import BasePage

from firebase_admin import firestore
from streamlit_auth0 import login_button
from tsptw.const import hash_client, AUTH0_CLIENT_ID, AUTH0_DOMAIN
from google.cloud.firestore_v1.client import Client


class MultiPageApp:
    def __init__(self, pages: list[BasePage], nav_label: str = "ページ一覧") -> None:
        self.pages = {page.page_id: page for page in pages}
        self.nav_label = nav_label

    def connect_to_database(self, key: str):
        db = firestore.client()
        return db.collection(key).document("user_info")

    def render(self) -> None:
        # ログインボタン
        with st.sidebar:
            user_info = login_button(client_id=AUTH0_CLIENT_ID, domain=AUTH0_DOMAIN)
            if user_info:
                if not user_info["email_verified"]:
                    st.error("Email is not verified")
                    return

                st.session_state["user_info"] = user_info
                self.connect_to_database(user_info["email"]).set(user_info, merge=True)
            else:
                if "user_info" in st.session_state and st.session_state["user_info"]["email"] is None:
                    del st.session_state["user_info"]["email"]
                st.warning("Please login to continue")

        # ページ選択ボックスを追加
        page_id = st.sidebar.selectbox(
            self.nav_label,
            list(self.pages.keys()),
            format_func=lambda page_id: self.pages[page_id].title,
        )

        # ページ描画
        try:
            self.pages[page_id].render()
        except Exception as e:
            st.error(e)
