import datetime
import string
from dataclasses import dataclass
from enum import Enum
from typing import List, NewType, Optional, Tuple, TypedDict, Union

from base_analayzer import BaseAnalyzer
from datas.lane_data import *
from utils.rdf_graph_creator import RdfGraphCreator
from utils.scanner import Scanner

from Zipc_airflow.src.analyzer.my_dataclass import (Measurement,
                                                    NineBlockAnalyzerData,
                                                    Vehicles)


@dataclass
class ImportedData():
    measurement: string
    mapid: int
    imported_data_id: int
    status: int

@dataclass
class Connection():
    type: string # type takes string "successor" or "predecessor"
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

@dataclass
class Lane():
    name: string
    width: int
    connection: List[Connection]
    waypoints: List[Waypoint_]

@dataclass
class Road():
    name: string
    lanes: List[Lane]

@dataclass
class WaypointData():
    gid: string
    direction: string  # "left" or "right"
    roads: List[Road]

@dataclass
class _Type():
    road: string
    lane: string

@dataclass
class Lane_Dict():
    successor: _Type
    predecessor: _Type

@dataclass
class Road_Dict():
    index: int
    lane_name: Lane_Dict

@dataclass
class Data_Dict():
    road_name: Road_Dict

@dataclass
class _Vehicle():
    direction: string  # DirectionType.*.value
    position: int   #おそらく　egoが0, frontが1, frontfrontが2, backが1, backbackが2となる

@dataclass
class Time_Dict():
    vehicle: _Vehicle  # 複数の種類の名前のvehicleがある

@dataclass
class Vehicle_Dict():
    time: Time_Dict

@dataclass
class NineBlockAnalyzerData():
    time: datetime.datetime
    ego_road: string
    ego_lane: string
    ego_waypoint_index: int
    vehicle_road: string
    vehicle_lane: string
    vehicle_waypoint_index: int



@dataclass
class Rdf_Data():
	vehicle: List[SceneData] # SceneDataには、start, end, behaviorTypeが記載されている


from datas.behaivor_type import BehaviorType
from datas.direction_type import DirectionType
from datas.lane_data import *
from datas.roadgeometry_type import RoadGeometryType
from datas.scenario_schema import ScenarioSchema
from datas.scene_type import SceneType
from datas.surrounding_vehicle_motion_type import SurroundingVehicleMotionType
from datas.waypoint import Waypoint


class NineBlockAnalyzer(BaseAnalyzer):

    def road_lane_check(self, diff_pos: int, diff_lane: int) -> str:
        """

        :param diff_pos:
        :param diff_lane:
        :return:
        """
        result = None
        if 3 < diff_pos:
            # FrontFront, Front, LeftFront, RightFront
            if diff_lane == 0:
                result = DirectionType.FRONT
            elif diff_lane == 1:
                result = DirectionType.LEFT_FRONT
            elif diff_lane == -1:
                result = DirectionType.RIGHT_FRONT
        elif diff_pos < -3:
            # Back, LeftBack, RightBack
            if diff_lane == 0:
                result = DirectionType.BACK
            elif diff_lane == 1:
                result = DirectionType.LEFT_BACK
            elif diff_lane == -1:
                result = DirectionType.RIGHT_BACK
        elif (-4 < diff_pos) and (diff_pos < 4):
            # Left, Right
            if diff_lane == 1:
                result = DirectionType.LEFT
            elif diff_lane == -1:
                result = DirectionType.RIGHT
        return result

    def direction_check(self, ego_lane, obs_lane):
        """
        進行方向が同じかどうか判定する
        :param ego_lane:
        :param obs_lane:
        :return:
        """
        if ego_lane[0] == obs_lane[0]:
            return True
        return False

    def get_road_info(self, waypoint_data: WaypointData):
        # 右側通行、左側通行を特定
        direction: string = waypoint_data['direction']

        data_dict: Data_Dict = {}
        for road in waypoint_data['roads']:
            road_dict: Road_Dict = {}
            road_name: string = road['name']
            index = None
            for lane in road['lanes']:
                # RoadのIndex数を取得
                if index is None:
                    index = len(lane['waypoints'])

                lane_dict: Lane_Dict = {}
                lane_name: string = lane['name']
                if (direction == 'left' and lane_name.startswith('L')) \
                        or (direction == 'right' and lane_name.startswith('R')):
                    # 道路の進行方向とレーンの進行方向が同じ場合
                    for connection in lane['connection']:
                        lane_dict[connection['type']] = {'road': connection['road'], 'lane': connection['lane']}
                else:
                    # 道路の進行方向とレーンの進行方向が異なる場合
                    # successor, predecessorを入れ替えることで、解析しやすくする
                    for connection in lane['connection']:
                        _type = None
                        if connection['type'] == 'successor':
                            _type = 'predecessor'
                        else:
                            _type = 'successor'
                        lane_dict[_type] = {'road': connection['road'], 'lane': connection['lane']}
                road_dict[lane_name] = lane_dict
            road_dict['index'] = index
            data_dict[road_name] = road_dict
        return data_dict

    def get_nine_block_data(self, measurement: string, road_data_dict: Data_Dict, vehicles: List[str]) -> Vehicle_Dict:
        vehicle_dict: Vehicle_Dict = {}
        for vehicle in vehicles:
            if vehicle == "ego":
                continue
            col_ego_road: str = "ego_road"
            col_ego_lane: str = "ego_lane"
            col_ego_waypoint_index: str = "ego_waypoint_index"
            col_obs_road: str = "{}_road".format(vehicle)
            col_obs_lane: str = "{}_lane".format(vehicle)
            col_obs_waypoint_index: str = "{}_waypoint_index".format(vehicle)
            query : str= 'select {}, {}, {}, {}, {}, {} from "{}"'.format(col_ego_road,
                                                                     col_ego_lane,
                                                                     col_ego_waypoint_index,
                                                                     col_obs_road,
                                                                     col_obs_lane,
                                                                     col_obs_waypoint_index,
                                                                     measurement)
            datas: List[NineBlockAnalyzerData] = self.influxdb_accessor.query(query)
            if datas is None:
                continue
            for data in datas:
                time: datetime.datetime  = data['time']
                time_dict: Time_Dict = vehicle_dict.get(time)
                if time_dict is None:
                    time_dict = {}
                    vehicle_dict[time] = time_dict

                ego_road: str = data[col_ego_road]
                ego_lane: str = data[col_ego_lane]
                ego_index: int = data[col_ego_waypoint_index]
                obs_road: str = data[col_obs_road]
                obs_lane: str = data[col_obs_lane]
                obs_index: int = data[col_obs_waypoint_index]

                if not self.direction_check(ego_lane, obs_lane):
                    # 進行方向が逆のため、評価不要
                    continue
                if ego_road is None or obs_road is None:
                    # 情報が正しくないため、評価不可
                    continue

                # 自車両より前を評価
                scanner: Scanner = Scanner(road_data_dict, obs_road, obs_lane)
                index, lane_diff = scanner.successor(ego_road, ego_lane)
                diff_pos = None
                if not (index is None or lane_diff is None):
                    # 横または前方（Road跨ぎ含む）
                    diff_pos: int = (index + obs_index) - ego_index
                    result: DirectionType = self.road_lane_check(diff_pos, lane_diff)
                else:
                    # 後方（Road跨ぎ）
                    index, lane_diff = scanner.predecessor(ego_road, ego_lane)
                    if not (index is None or lane_diff is None):
                        # 後方（Road跨ぎ）
                        diff_pos: int = (index - obs_index) + ego_index
                        result: DirectionType = self.road_lane_check(diff_pos, lane_diff)

                time_dict[vehicle]: _Vehicle = {"direction": result if result is None else result.value,
                                      "position": diff_pos
                                      }
        return vehicle_dict

    def nine_block_classification(self, time_series_vehicle_dict: Vehicle_Dict) -> Vehicle_Dict: # 減量したVehicle_Dictが返される(Vehicle_dict.timeからFrontFront以外が削除される)
        """
        FrontFront, Backの解析
        FrontFront:obsB
        direction ->
            ego - obsA - obsB - obsC
            Back:obsB
            direction ->
            obsA - obsB - ego - obsC
        :param time_series_vehicle_dict:
        :return:
        """
        for time, vehicle_dict in time_series_vehicle_dict.items():  # time, Time_Dict
            front_dict: Time_Dict = {}
            back_dict : Time_Dict = {}
            for vehicle, data in vehicle_dict.items():  # vehicle, _Vehicle
                if data.get('direction') == DirectionType.FRONT.value:
                    front_dict[vehicle] = data
                elif data.get('direction') == DirectionType.BACK.value:
                    back_dict[vehicle] = data
            # Front解析
            sorted_front: List[Tuple[str, _Vehicle]] = sorted(front_dict.items(), key=lambda x: x[1].get('position')) # Time_Dict.items()　# positionでソート
            sorted_back: List[Tuple[str, _Vehicle]] = sorted(back_dict.items(), key=lambda x: x[1].get('position'))

            # egoの2つ前の車両をFrontFrontにし、以降は排除
            for num in range(1, len(sorted_front)):
                data: Tuple[str, _Vehicle] = sorted_front[num]
                if num == 1:
                    vehicle_data: _Vehicle = vehicle_dict.get(data[0]) # data[0] は　Time_Dictのvehicle
                    vehicle_data['direction'] = DirectionType.FRONT_FRONT.value
                else:
                    vehicle_dict.pop(data[0])
            # egoの直後以降の他車両を排除
            for num in range(1, len(sorted_back)):
                data: Tuple[str, _Vehicle] = sorted_back[num]
                vehicle_dict.pop(data.key())
        return time_series_vehicle_dict

    def create_direction_data(self, direction: DirectionType, time: str):
        """

        :param direction:
        :param time:
        :return:
        """
        data = None
        if direction == DirectionType.FRONT_FRONT.value:
            data = FrontFrontData(start=time)
        elif direction == DirectionType.FRONT.value:
            data = FrontData(start=time)
        elif direction == DirectionType.LEFT_FRONT.value:
            data = LeftFrontData(start=time)
        elif direction == DirectionType.RIGHT_FRONT.value:
            data = RightFrontData(start=time)
        elif direction == DirectionType.LEFT.value:
            data = LeftData(start=time)
        elif direction == DirectionType.RIGHT.value:
            data = RightData(start=time)
        elif direction == DirectionType.BACK.value:
            data = BackData(start=time)
        elif direction == DirectionType.LEFT_BACK:
            data = LeftBackData(start=time)
        elif direction == DirectionType.RIGHT_BACK:
            data = RightBackData(start=time)
        return data

    def create_rdf_data(self, time_series_vehicle_dict: Vehicle_Dict, vehicles: List[str]) -> Rdf_Data:
        rdf_data: Rdf_Data = {}
        for vehicle in vehicles:
            if vehicle == "ego":
                continue
            vehicle_rdf_data_list = rdf_data.get(vehicle)
            if vehicle_rdf_data_list is None:
                vehicle_rdf_data_list: List[SceneData] = []
                rdf_data[vehicle] = vehicle_rdf_data_list

            prev_time: Optional[str] = None
            direction_data: SceneData = None
            for time, time_series_data in time_series_vehicle_dict.items():
                vehicle_data = time_series_data.get(vehicle)
                if vehicle_data is None:
                    if direction_data is not None:
                        direction_data.set_end(prev_time)
                        vehicle_rdf_data_list.append(direction_data)
                        direction_data = None
                else:
                    direction: DirectionType = vehicle_data.get('direction')

                    if direction_data is None:
                        direction_data = self.create_direction_data(direction, time) # SceneData

                    elif not direction_data.equals(direction):
                        direction_data.set_end(prev_time)
                        vehicle_rdf_data_list.append(direction_data)
                        direction_data = self.create_direction_data(direction, time)
                prev_time = time
            if direction_data is not None:
                direction_data.set_end(prev_time)
                vehicle_rdf_data_list.append(direction_data)
        return rdf_data

    def execute(self, imported_data_id: int=-1):
        """
        各車両のレーンキープ、レーンチェンジを解析
        :param imported_data_id:
        :return:
        """
        # 走行データ管理DBからレコードを取得
        imported_data: ImportedData = self.get_imported_data(imported_data_id)
        measurement: Measurement = imported_data.measurement
        map_id: int = imported_data.mapid

        # waypointsから対象のwaypointを取得
        waypoint_data: WaypointData = self.mongo_accessor.get_waypoints_from_map_id(map_id)

        # 各RoadのWaypointのIndex最大値, Successor, Predecessorを取得
        road_data_dict: Data_Dict = self.get_road_info(waypoint_data)

        # 車両取得
        vehicles: Vehicles = self.influxdb_accessor.get_vehicles(measurement)

        # 車両ごとの走行Lane情報を取得
        time_series_vehicle_dict: Vehicle_Dict = self.get_nine_block_data(measurement, road_data_dict, vehicles)

        # FrontFront, Backの分類
        time_series_vehicle_dict: Vehicle_Dict = self.nine_block_classification(time_series_vehicle_dict)

        rdf_data: Rdf_Data = self.create_rdf_data(time_series_vehicle_dict, vehicles)

        # RDFへ書き込み
        creator : RdfGraphCreator = RdfGraphCreator("garden_ts", measurement)
        creator.build_direction(rdf_data, "ego") # creator.build_direction(rdf_data, ego, SceneType.DIRECTION)


# ひとことメモ　nine_block_analyzerは、Rdf_Dataを作成している。vehicle: List[SceneData], SceneDataには、DirectionType(9種類(frontfront, front, back, leftfront, left, leftback, rightfront, right, rightback)), start, endがある。

def execute(**kwargs):
    """

    :param kwargs:
    :return:
    """
    print('Record ID:{}'.format(kwargs['record_id']))
    record_id = int(kwargs['record_id'])
    analyzer = NineBlockAnalyzer()
    analyzer.execute(imported_data_id=record_id)


if __name__ == '__main__':
    # for debug
    NineBlockAnalyzer().execute(imported_data_id=2)
