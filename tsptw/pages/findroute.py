import numpy as np
import datetime as dt
from datetime import timedelta

import streamlit as st
from typing import List
from .base import BasePage
from tsptw.const import hash_client, StepPoint, gmaps, PageId, create_datetime
from firebase_admin import firestore
from google.cloud.firestore_v1.client import Client


from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


class FindRoutePage(BasePage):
    def __init__(self, page_id: PageId, title: str) -> None:
        super().__init__(page_id, title)
        self.step_points = []

    def create_time_matrix(self, *step_points: List[StepPoint]):
        n = len(step_points)
        arr = np.zeros((n, n))
        items = [sp.address for sp in step_points]
        split_arrs = np.array_split(items, (n // 10) + 1)
        split_arrs_len = [len(a) for a in split_arrs]
        for i, a in enumerate(split_arrs):
            for j, b in enumerate(split_arrs):
                resp = gmaps.distance_matrix(
                    list(a),
                    list(b),
                )
                for k, r in enumerate(resp["rows"]):
                    for l, c in enumerate(r["elements"]):
                        p, q = (
                            sum(split_arrs_len[:i]) + k,
                            sum(split_arrs_len[:j]) + l,
                        )
                        if p == q:
                            continue
                        arr[p][q] = step_points[p].staying_min + int(c["duration"]["value"] / 60)  # sec -> min
        return arr.astype(int)

    def diff_min(self, end: dt.datetime, start: dt.datetime) -> int:
        return int((end - start).total_seconds() / 60)

    def create_time_windows(self, start_time: dt.time, *step_points: List[StepPoint]):
        # 滞在先の見積診察時間を，滞在可能時間帯から予め引いておく
        return [
            (
                self.diff_min(sp.start_time, start_time),
                self.diff_min(sp.end_time - timedelta(minutes=sp.staying_min), start_time),
            )
            for sp in step_points
        ]

    # Stores the data for the problem.
    def create_data_model(self, start_time: dt.datetime, end_time: dt.datetime, *step_points: List[StepPoint]):
        data = {}
        data["name"] = [sp.name for sp in step_points]
        data["start_time"] = start_time
        data["depot_opening_time"] = self.diff_min(end_time, start_time)
        data["time_matrix"] = self.create_time_matrix(*step_points)
        # https://developers.google.com/optimization/reference/python/constraint_solver/pywrapcp#intvar
        data["time_windows"] = self.create_time_windows(start_time, *step_points)
        data["num_vehicles"] = 1
        data["depot"] = 0
        return data

    def print_solution(self, data, manager, routing, solution):
        time_dimension = routing.GetDimensionOrDie("Time")
        total_time = 0
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            # st.write("Route for vehicle", vehicle_id)
            while not routing.IsEnd(index):
                time_var = time_dimension.CumulVar(index)
                if solution.Min(time_var) == solution.Max(time_var):
                    st.write(
                        data["name"][manager.IndexToNode(index)],
                        "さん宅．最短で",
                        data["start_time"] + timedelta(minutes=solution.Min(time_var)),
                        "に到着することができます",
                    )
                else:
                    st.write(
                        data["name"][manager.IndexToNode(index)],
                        "さん宅．最短で",
                        data["start_time"] + timedelta(minutes=solution.Min(time_var)),
                        "に到着することができますが，遅くとも",
                        data["start_time"] + timedelta(minutes=solution.Max(time_var)),
                        "までには到着しなければなりません"
                    )
                index = solution.Value(routing.NextVar(index))
            time_var = time_dimension.CumulVar(index)
            st.write(
                "最終地点(=出発地点) ",
                data["name"][manager.IndexToNode(index)],
                "．最短で",
                data["start_time"] + timedelta(minutes=solution.Min(time_var)),
                "に到着することができます",
            )
            st.write("この経路の所要時間: ", solution.Min(time_var), "分")
            total_time += solution.Min(time_var)
        # st.write("全経路の所要時間: ", total_time, "分")

    # Solve the VRP with time windows.
    def solve_vrp(self, *step_points: List[StepPoint]):
        assert len(step_points) > 0, "There is no step point."

        # Instantiate the data problem.
        start_time = create_datetime(st.session_state.start_time)
        end_time = create_datetime("23:59:59", fromisoformat=True)

        data = self.create_data_model(start_time, end_time, *step_points)

        # Create the routing index manager.
        manager = pywrapcp.RoutingIndexManager(len(data["time_matrix"]), data["num_vehicles"], data["depot"])

        # Create Routing Model.
        routing = pywrapcp.RoutingModel(manager)

        # Create and register a transit callback.
        def time_callback(from_index, to_index):
            """Returns the travel time between the two nodes."""
            # Convert from routing variable Index to time matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["time_matrix"][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(time_callback)

        # Define cost of each arc.
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add Time Windows constraint.
        dimension_name = "Time"
        routing.AddDimension(
            transit_callback_index,
            data["depot_opening_time"],  # allow waiting time [min]
            data["depot_opening_time"],  # maximum time [min] per vehicle until return
            True,  # Force start cumul to zero.
            dimension_name,
        )
        time_dimension = routing.GetDimensionOrDie(dimension_name)
        # Add time window constraints for each location except depot.
        for location_idx, time_window in enumerate(data["time_windows"]):
            if location_idx == data["depot"]:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        # Add time window constraints for each vehicle start node.
        depot_idx = data["depot"]
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data["time_windows"][depot_idx][0], data["time_windows"][depot_idx][1]
            )

        # Instantiate route start and end times to produce feasible times.
        for i in range(data["num_vehicles"]):
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.Start(i)))
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

        # Add SpanCost to minimize total wait time. See https://stackoverflow.com/questions/62411546/google-or-tools-minimize-total-time
        time_dimension.SetGlobalSpanCostCoefficient(1)
        
        # Setting first solution heuristic.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC

        # Solve the problem.
        solution = routing.SolveWithParameters(search_parameters)

        # Print solution on console.
        if solution:
            self.print_solution(data, manager, routing, solution)
        else:
            st.error("Not found the solution")
            st.warning(data["time_matrix"])  # for debug
        return solution

    @st.cache(hash_funcs={Client: hash_client}, allow_output_mutation=True)
    def connect_to_database(self, key: str):
        db = firestore.client()
        return db.collection(key).document("contact")

    def sort_data(self, ref):
        doc = ref.get()
        if doc.exists:
            return {k: v for k, v in sorted(doc.to_dict().items(), key=lambda x: x[1]["timestamp"])}
        else:
            return None

    def render(self):
        st.title("ルート探索")

        st.markdown(
            """
        経由地点を一度ずつすべて経由して，出発地点に戻ってくる巡回経路を求めます
        ### 使い方
         1. 最初に「出発地点」および「出発時刻」を指定してください
         1. 経由地点（出発地点は除く）を複数追加してください（最大25箇所）
         1. 途中で出発地点を経由する場合は経由地点に新規追加してください

            例：出発地点で昼休みを取る場合「お昼休み」という経由地点を新規追加．滞在時間帯は昼休みを開始しても良い時間帯(例えば11:30-13:30)．見積診察時間はそのまま昼休憩の時間と読み替える
         1. 「ルート探索」ボタンを実行してください
         1. ```CP Solver fail``` エラーが出た場合は見積診察時間の条件が厳しすぎることが考えられます．緩和して再度お試しください．
        """
        )

        if "user_info" not in st.session_state:
            st.warning("Please login to continue")
            return

        if "step_points" in st.session_state and st.session_state["step_points"]:
            self.step_points = st.session_state["step_points"]

        contacts = self.sort_data(self.connect_to_database(st.session_state["user_info"]["email"]))

        if contacts:
            col1, col2 = st.columns([6, 1])
            depot = col1.selectbox(
                "出発地点",
                contacts.values(),
                format_func=lambda contact: contact["name"],
                key="depot",
            )
            col2.time_input("出発時刻", dt.time.fromisoformat("09:00:00"), key="start_time")

            self.step_points = st.multiselect(
                "経由地点",
                contacts.values(),
                default=self.step_points,
                format_func=lambda contact: contact["name"],
                key="step_points",
                disabled=len(self.step_points) > 25,
            )

            if st.session_state.depot["id"] in [pt["id"] for pt in st.session_state.step_points]:
                st.warning("経由地点に出発地点を登録することはできません．途中立ち寄る必要がある場合は経由地点を新規で追加してください（上記「使い方」参照）")

            if create_datetime(st.session_state.depot["start_time"], fromisoformat=True) > create_datetime(
                st.session_state.start_time
            ):
                st.warning(
                    f"出発地点の訪問可能時間帯(始){st.session_state.depot['start_time']}よりも出発時刻{st.session_state.start_time}が早いです．出発時刻を見直すか出発地点を見直してください．"
                )

            all_points = [StepPoint.from_dict(p) for p in [depot] + self.step_points]

            if st.button("ルート探索 🔍"):
                self.solve_vrp(*all_points)
            # hist_ref.set(
            #     {"timestamp": int(time.time()), "step_points": [sp.to_dict() for sp in step_points if sp is not None]}
            # )

        else:
            st.warning("1件も見つかりませんでした．「経由地点」ページにて経由地点の登録を先に実施してください")
            return
