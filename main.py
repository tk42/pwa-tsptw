import os
import streamlit as st

import firebase_admin
from firebase_admin import credentials

from tsptw.init_app import init_app, init_pages


def initialized_sesstion_state():
    st.session_state["is_started"] = True
    st.session_state["app"] = app
    st.session_state["selected"] = {
        "id": "",
        "timestamp": 0,
        "name": "",
        "address": "",
        "start_time": "08:45:00",
        "end_time": "19:00:00",
        "staying_min": 0,
    }


if not st.session_state.get("is_started", False):
    pages = init_pages()
    app = init_app(pages)
    st.set_page_config(page_icon="🗺️", page_title="往診経路最適化さん", layout="wide")
    initialized_sesstion_state()

    if firebase_admin._DEFAULT_APP_NAME not in firebase_admin._apps:
        if os.environ.get("CLOUD_RUN") and os.environ.get("CLOUD_RUN").title() == "True":
            cred = credentials.ApplicationDefault()
        else:
            cred = credentials.Certificate("./serviceAccount.json")
        firebase_admin.initialize_app(cred)


app = st.session_state.get("app", None)
if app is not None:
    app.render()
