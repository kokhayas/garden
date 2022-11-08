import datetime
import string
from dataclasses import dataclass
from enum import Enum
from typing import List, NewType, Optional, Tuple, TypedDict, Union

from base_analayzer import BaseAnalyzer
from datas.lane_data import *
from utils.rdf_graph_creator import RdfGraphCreator
from utils.scanner import Scanner

from Zipc_airflow.src.analyzer.datas.roadgeometry_type import RoadGeometryType

Measurement = str
Vehicle = str
Vehicles = List[Vehicle]
# Velocity = float
Mapid = str

@dataclass
class ImportedData():
    measurement: Measurement
    mapid: Mapid
    imported_data_id: int
    status: int


@dataclass
class Connection():
    type: string # type takes string "successor" or "predecessor", Union("successor", "predecessor")
    road: string
    lane: string

@dataclass
class Point():
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float

@dataclass
class Waypoint_():
    index: int
    point: Point
    roadGeo: RoadGeometryType #

@dataclass
class Lane_Dict():
    name: string
    width: int
    connection: List[Connection] # connection key自体が、Union("successor", "predecessor")
    waypoints: List[Waypoint_]

@dataclass
class Road_Dict():
    name: string
    lanes: List[Lane_Dict]

@dataclass
class WaypointData():
    gid: string
    direction: string  # "left" or "right", Union("left", "right")
    roads: List[Road_Dict]

# @dataclass
# class _Type():
#     road: string
#     lane: string

# @dataclass
# class Lane_Dict():
#     successor: _Type
#     predecessor: _Type

# @dataclass
# class Road_Dict():
#     index: int
#     lane_name: Lane_Dict

# @dataclass
# class Data_Dict():
#     road_name: Road_Dict

# @dataclass
# class _Vehicle():
#     direction: string  # DirectionType.*.value
#     position: int   #おそらく　egoが0, frontが1, frontfrontが2, backが1, backbackが2となる

# @dataclass
# class Time_Dict():
#     vehicle: _Vehicle  # 複数の種類の名前のvehicleがある

# @dataclass
# class Vehicle_Dict():
#     time: Time_Dict

# @dataclass
# class NineBlockAnalyzerData(): # influxdbから取得したデータ
#     time: datetime.datetime 			# default
#     ego_road: string 					# default
#     ego_lane: string 					# default
#     ego_waypoint_index: int 			# default
#     vehicle_road: string 				# default
#     vehicle_lane: string 				# default
#     vehicle_waypoint_index: int 		# default


# @dataclass
# class Rdf_Data():
# 	vehicle: List[SceneData] # SceneDataには、start, end, behaviorTypeが記載されている
