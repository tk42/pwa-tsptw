import uuid
import time
import datetime as dt
import streamlit as st
from .base import BasePage
from tsptw.const import StepPoint, ActorId, PageId
from tsptw.const import hash_client
from firebase_admin import firestore
from google.cloud.firestore import DELETE_FIELD
from google.cloud.firestore_v1.client import Client


class EditPage(BasePage):
    def __init__(self, page_id: PageId, title: str) -> None:
        super().__init__(page_id, title)
        self.selected = {}

    def submit(
        self,
        actor: ActorId = ActorId.NONE,
        sp_id: str = "",
        timestamp: int = 0,
        first_set: bool = False,
        last_delete: bool = False,
    ):
        sid = st.session_state["sid"]
        step_name = st.session_state["step_name"]
        step_address = st.session_state["step_address"]
        staying_min = st.session_state["staying_min"]
        start_time = st.session_state["start_time"]
        end_time = st.session_state["end_time"]
        cont_ref = self.connect_to_database(sid)
        if actor == ActorId.ADD:
            sp = StepPoint(
                uuid.uuid4().hex,
                int(time.time()),
                step_name,
                step_address,
                staying_min,
                start_time,
                end_time,
            )

            if first_set:
                cont_ref.set({sp.id: sp.to_dict()})
            else:
                cont_ref.update({sp.id: sp.to_dict()})
        elif actor == ActorId.UPDATE:
            sp = StepPoint(sp_id, timestamp, step_name, step_address, staying_min, start_time, end_time)
            cont_ref.update({sp.id: sp.to_dict()})
        elif actor == ActorId.DELETE:
            if last_delete:
                cont_ref.delete()
            else:
                cont_ref.update({sp_id: DELETE_FIELD})
        return

    @st.cache(hash_funcs={Client: hash_client}, allow_output_mutation=True)
    def connect_to_database(self, sid: str):
        db = firestore.client()
        return db.collection(sid).document("contact")

    def sort_data(self, ref):
        doc = ref.get()
        if doc.exists:
            return {k: v for k, v in sorted(doc.to_dict().items(), key=lambda x: x[1]["timestamp"])}
        else:
            return None

    def render(self):
        st.title("経由地点 登録画面")

        st.markdown(
            """
        ### 説明
         - 「名称」：経由地点の名称．訪問場所の覚えやすい名称を付けることが可能です．
         - 「住所」：経由地点の住所．都道府県から番地まで入力してください．郵便番号は不要です．挙動不審の場合はGoogleMapで住所検索をおこない，想定の場所にドロップピンが指されることを確認してください．
         - 「見積診察時間」：車を停車してから発車するまでのおおよその時間を5分刻みで入力してください
         - 「滞在可能時刻(始)」：経由地点に到着してもよい最も早い時刻を入力してください
         - 「滞在可能時刻(終)」：経由地点に滞在してもよい最も遅い時刻を入力してください
        """
        )
        st.markdown(
            """
        ### 使い方
         - 追加する場合：「名称」「住所」「見積診察時間」「滞在可能時間(始)」「滞在可能時間(終)」を入力し，「追加」ボタンを押してください
         - 編集/削除する場合：上段の「編集/削除対象」で対象の経由地点を選択し，下段で「更新」/「削除」ボタンを押してください
        """
        )

        if "sid" not in st.session_state:
            st.warning("Please login to continue")
            return

        contacts = self.sort_data(self.connect_to_database(st.session_state["sid"]))

        if contacts:
            self.selected = st.selectbox(
                "編集/削除対象",
                contacts.values(),
                format_func=lambda contact: contact["name"],
                key="selected",
            )
        else:
            st.warning("1件も見つかりませんでした")
            self.selected = {
                "id": "",
                "timestamp": 0,
                "name": "",
                "address": "",
                "staying_min": 0,
                "start_time": "08:45:00",
                "end_time": "19:00:00",
            }

        with st.form(key="step_point"):
            col11, col12, col13, col14 = st.columns([4, 1, 1, 1])
            col11.text_input("名称", self.selected["name"], key="step_name")
            col12.number_input(
                "見積診察時間[分]",
                value=self.selected["staying_min"],
                min_value=0,
                max_value=180,
                step=5,
                key="staying_min",
            )
            col13.time_input("滞在可能時刻(始)", dt.time.fromisoformat(self.selected["start_time"]), key="start_time")
            col14.time_input("滞在可能時刻(終)", dt.time.fromisoformat(self.selected["end_time"]), key="end_time")

            st.text_input("住所", self.selected["address"], key="step_address")

            col21, col22, col23, _ = st.columns([1, 1, 1, 6])
            add_button = col21.form_submit_button(
                label=str(ActorId.ADD),
                on_click=self.submit,
                kwargs={
                    "actor": ActorId.ADD,
                    "sp_id": self.selected["id"],
                    "timestamp": self.selected["timestamp"],
                    "first_set": self.selected["id"] == "",
                    "last_delete": contacts is not None and len(contacts) == 1,
                },
            )
            if add_button:
                st.success(f"{str(ActorId.ADD)}に成功しました！")

            update_button = col22.form_submit_button(
                label=str(ActorId.UPDATE),
                on_click=self.submit,
                kwargs={
                    "actor": ActorId.UPDATE,
                    "sp_id": self.selected["id"],
                    "timestamp": self.selected["timestamp"],
                    "first_set": self.selected["id"] == "",
                    "last_delete": contacts is not None and len(contacts) == 1,
                },
            )
            if update_button:
                st.success(f"{str(ActorId.UPDATE)}に成功しました！")

            del_button = col23.form_submit_button(
                label=str(ActorId.DELETE),
                on_click=self.submit,
                kwargs={
                    "actor": ActorId.DELETE,
                    "sp_id": self.selected["id"],
                    "timestamp": self.selected["timestamp"],
                    "first_set": self.selected["id"] == "",
                    "last_delete": contacts is not None and len(contacts) == 1,
                },
            )
            if del_button:
                st.success(f"{str(ActorId.DELETE)}に成功しました！")
