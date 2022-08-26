import os
import googlemaps

# from googlemaps import LatLng
import numpy as np
import streamlit as st
from typing import List
from datetime import time, datetime, timedelta
from collections import namedtuple

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# import folium
# from streamlit_folium import st_folium

# from sample import sample_mat, sample_mat2, sample_tw

gmaps = googlemaps.Client(key=os.environ.get("GOOGLEMAP_API_KEY"))

Location = namedtuple("Location", ["lat", "lng"])
StepPoint = namedtuple("StepPoint", ["name", "address", "staying_min", "start_time", "end_time"])


def create_step_point(num: int, default_address: str) -> StepPoint | None:
    col1, col2, col3, col4, col5 = st.columns([1, 4, 1, 1, 1])
    with col1:
        step_name = st.text_input(f"Name {num}", f"餃子の王将 No.{num}", key=f"name{num}")
    with col2:
        step_address = st.text_input(f"Address {num}", default_address, key=f"address{num}")
    with col3:
        staying_min = st.number_input("Staying time [min.]", min_value=0, max_value=180, step=5, key=f"staying{num}")
    with col4:
        start_time = st.time_input("Available start time", time(hour=8, minute=45), key=f"start{num}")
    with col5:
        end_time = st.time_input("Available end time", time(hour=19, minute=0), key=f"end{num}")
    if step_address == "":
        return None
    return StepPoint(
        name=step_name,
        address=step_address,
        staying_min=int(staying_min),
        start_time=start_time,
        end_time=end_time,
    )


def create_time_matrix(*step_points: List[StepPoint]):
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


def diff_min(end: time, start: time) -> int:
    return int(
        (datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)).total_seconds() / 60
    )


def create_time_windows(*step_points: List[StepPoint]):
    return [
        (diff_min(sp.start_time, step_points[0].start_time), diff_min(sp.end_time, step_points[0].start_time))
        for sp in step_points
    ]


# Stores the data for the problem.
def create_data_model(*step_points: List[StepPoint]):
    data = {}
    data["name"] = [sp.name for sp in step_points]
    data["start_time"] = datetime.combine(datetime.today(), step_points[0].start_time)
    data["time_matrix"] = create_time_matrix(*step_points)
    # https://developers.google.com/optimization/reference/python/constraint_solver/pywrapcp#intvar
    data["time_windows"] = create_time_windows(*step_points)
    data["num_vehicles"] = 1
    data["depot"] = 0
    return data


def print_solution(data, manager, routing, solution):
    st.header("Timeschedule")
    st.info("A ~ B : 到着時刻の解の範囲．すなわち「車両は時刻AとBの間にそこに到着していれば良い」という意味．滞在時間帯ではないので注意！")
    # st.write("Objective:", solution.ObjectiveValue())
    time_dimension = routing.GetDimensionOrDie("Time")
    total_time = 0
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        st.write("Route for vehicle", vehicle_id)
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            st.write(
                data["start_time"] + timedelta(minutes=solution.Min(time_var)),
                " ~ ",
                data["start_time"] + timedelta(minutes=solution.Max(time_var)),
                " @ ",
                data["name"][manager.IndexToNode(index)],
                " ➡ ",
            )
            index = solution.Value(routing.NextVar(index))
        time_var = time_dimension.CumulVar(index)
        st.write(
            "From ",
            data["start_time"] + timedelta(minutes=solution.Min(time_var)),
            " To ",
            data["start_time"] + timedelta(minutes=solution.Max(time_var)),
            " @ ",
            data["name"][manager.IndexToNode(index)],
        )
        st.write("Time of the route: ", solution.Min(time_var), "min")
        total_time += solution.Min(time_var)
    st.write("Total time of all routes: ", total_time, "min")


# Solve the VRP with time windows.
def solve_vrp(*step_points: List[StepPoint]):
    assert len(step_points) > 0, "There is no step point."

    # Instantiate the data problem.
    data = create_data_model(*step_points)

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
    depot_opening_time = diff_min(step_points[0].end_time, step_points[0].start_time)
    dimension_name = "Time"
    routing.AddDimension(
        transit_callback_index,
        depot_opening_time,  # allow waiting time [min]
        depot_opening_time,  # maximum time [min] per vehicle until return
        False,  # Don't force start cumul to zero.
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
        time_dimension.CumulVar(index).SetRange(data["time_windows"][depot_idx][0], data["time_windows"][depot_idx][1])

    # Instantiate route start and end times to produce feasible times.
    for i in range(data["num_vehicles"]):
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        st.error("Not found the solution")
        st.warning(data["time_matrix"])  # for debug


def main():
    st.set_page_config(page_icon="🗺️", page_title="TSPTW with Streamlit", layout="wide")
    st.title("Traveling Salesman Problem with Time Windows and Steps on Streamlit")
    st.caption("This is a webapp with streamlit to solve the traveling salesman problem with time windows and steps")
    st.info("No. 0 is the depot. Skipped if the address is empty.")

    step_points = []
    # depot
    step_points += [create_step_point(len(step_points), "650-0011 兵庫県神戸市中央区下山手通2丁目11-1")]
    step_points += [create_step_point(len(step_points), "658-0072 兵庫県神戸市東灘区岡本1-5-5 ダイソービル 2階")]
    step_points += [create_step_point(len(step_points), "651-0078 兵庫県神戸市中央区八雲通1-4-35")]
    step_points += [create_step_point(len(step_points), "652-0811 兵庫県神戸市兵庫区新開地3-4-22")]
    step_points += [create_step_point(len(step_points), "651-1101 兵庫県神戸市北区山田町小部 字広苅14-8")]
    step_points += [create_step_point(len(step_points), "654-0111 兵庫県神戸市須磨区車道谷山1-2")]
    step_points += [create_step_point(len(step_points), "655-0852 兵庫県神戸市垂水区名谷町686-2")]
    step_points += [create_step_point(len(step_points), "650-0022 兵庫県神戸市中央区元町通1-10-7")]
    step_points += [create_step_point(len(step_points), "653-0015 兵庫県神戸市長田区菅原通6-2")]
    step_points += [create_step_point(len(step_points), "654-0055 兵庫県神戸市須磨区須磨浦通4-6-20")]

    step_points += [create_step_point(len(step_points), "651-1131 兵庫県神戸市北区北五葉1-1-3")]
    step_points += [create_step_point(len(step_points), "655-0893 兵庫県神戸市垂水区日向1-4")]
    step_points += [create_step_point(len(step_points), "652-0804 兵庫県神戸市兵庫区塚本通6-1-18")]
    step_points += [create_step_point(len(step_points), "657-0027 兵庫県神戸市灘区永手町5-4-16")]
    step_points += [create_step_point(len(step_points), "658-0023 兵庫県神戸市東灘区深江浜町82")]
    step_points += [create_step_point(len(step_points), "658-0054 兵庫県神戸市東灘区御影中町1-13-8")]
    step_points += [create_step_point(len(step_points), "659-0065 兵庫県芦屋市公光町10-14")]
    step_points += [create_step_point(len(step_points), "662-0947 兵庫県西宮市宮前町1-14")]
    step_points += [create_step_point(len(step_points), "662-0043 兵庫県西宮市常磐町1-2")]
    step_points += [create_step_point(len(step_points), "662-0832 兵庫県西宮市甲風園1-5-16")]
    step_points += [create_step_point(len(step_points), "")]
    step_points += [create_step_point(len(step_points), "")]
    step_points += [create_step_point(len(step_points), "")]
    step_points += [create_step_point(len(step_points), "")]
    step_points += [create_step_point(len(step_points), "")]

    if st.button("FIND ROUTE 🔍"):
        solve_vrp(*[stp for stp in step_points if stp is not None])


if __name__ == "__main__":
    main()
