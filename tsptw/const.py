import os
import googlemaps
import datetime as dt
from typing import List
from enum import Enum, IntEnum, auto
from datetime import datetime, date
from collections import namedtuple


AUTH0_CLIENT_ID = "ciFCosdQaze8Vwz2CQRci6Xa4Or1GTuu"
AUTH0_DOMAIN = "tk42.jp.auth0.com"

gmaps = googlemaps.Client(key=os.environ.get("GOOGLEMAP_API_KEY"))

Location = namedtuple("Location", ["lat", "lng"])
baseCls = namedtuple(
    "StepPoint", 
    ["id", "timestamp", "name", "address", "lat", "lng", "staying_min", "start_time", "end_time"]
)

today = datetime.now().date()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def create_datetime(t: dt.time or str, fromisoformat=False):
    if fromisoformat:
        t = dt.time.fromisoformat(t)
    return datetime.combine(today, t)


def geocode(address: str) -> Location:
    results = gmaps.geocode(address)
    print(results)
    location = results[0]["geometry"]["location"]
    return Location(location["lat"], location["lng"])


class StepPoint(baseCls):
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "name": self.name,
            "address": self.address,
            "lat": self.lat,
            "lng": self.lng,
            "staying_min": self.staying_min,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }

    @staticmethod
    def from_dict(source: dict):
        return StepPoint(
            source["id"],
            source["timestamp"],
            source["name"],
            source["address"],
            source["lat"],
            source["lng"],
            source["staying_min"],
            datetime.fromisoformat(str(date.today()) + "T" + source["start_time"]),
            datetime.fromisoformat(str(date.today()) + "T" + source["end_time"]),
        )

    def __repr__(self) -> str:
        return (
            f"StepPoint({self.id}, {self.timestamp}, {self.name}, {self.address}, {self.lat}, {self.lng}"
            + f" {self.staying_min}, {self.start_time}, {self.end_time})"
        )


def get_route(step_points: List[StepPoint]):
    result = gmaps.directions(
        step_points[0].address,
        step_points[-1].address,
        waypoints=[sp.address for sp in step_points[1:-1]],
        avoid="highways",
    )
    print(result)
    return [
        [step["start_location"]["lng"], step["start_location"]["lat"]]
        for step in result[0]["legs"][0]["steps"]
    ]


def hash_client(ref):
    return hash(ref)


class PageId(Enum):
    TOP = auto()
    EDIT = auto()
    FIND_ROUTE = auto()


class ActorId(IntEnum):
    NONE = 0
    ADD = 1
    UPDATE = 2
    DELETE = 3

    def __str__(self):
        return ["追加", "更新", "削除"][int(self) - 1]
