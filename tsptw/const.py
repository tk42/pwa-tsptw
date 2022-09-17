import os
import googlemaps
from enum import Enum, IntEnum, auto
from datetime import datetime, date
from collections import namedtuple


AUTH0_CLIENT_ID = "ciFCosdQaze8Vwz2CQRci6Xa4Or1GTuu"
AUTH0_DOMAIN = "tk42.jp.auth0.com"

gmaps = googlemaps.Client(key=os.environ.get("GOOGLEMAP_API_KEY"))

Location = namedtuple("Location", ["lat", "lng"])
baseCls = namedtuple("StepPoint", ["id", "timestamp", "name", "address", "staying_min", "start_time", "end_time"])


class StepPoint(baseCls):
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "name": self.name,
            "address": self.address,
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
            source["staying_min"],
            datetime.fromisoformat(str(date.today()) + "T" + source["start_time"]),
            datetime.fromisoformat(str(date.today()) + "T" + source["end_time"]),
        )

    def __repr__(self) -> str:
        return (
            f"StepPoint({self.id}, {self.timestamp}, {self.name}, {self.address},"
            + f" {self.staying_min}, {self.start_time}, {self.end_time})"
        )


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
