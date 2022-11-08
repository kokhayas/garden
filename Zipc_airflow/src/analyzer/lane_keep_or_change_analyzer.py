import string
from dataclasses import dataclass
from enum import Enum
from typing import List, NewType, Optional, Tuple, TypedDict, Union

from base_analayzer import BaseAnalyzer
from datas.lane_data import LaneChangeData, LaneKeepData, SceneData
from datas.scene_type import SceneType
from utils.rdf_graph_creator import RdfGraphCreator

from Zipc_airflow.src.analyzer.my_dataclass import (ImportedData, Measurement,
                                                    Vehicles, WaypointData)


@dataclass
class Lane_Info_Dict():
	vehicle: List[SceneData] # start, end, BehaviorType.LANE_CHANGE or BehaviorType.LANE_KEEP

@dataclass
class Vehicle_Road_Lane_Dict():
	time: string
	vehicle_road: string
	vehicle_lane: string

@dataclass
class Vehicle_Dict():
	vehicle: List[Vehicle_Road_Lane_Dict]

@dataclass
class Connection():
	road: string
	lane: string

@dataclass
class Lane_Dict():
	connection: Connection # connection key is "successor" or "predecessor"

@dataclass
class Road_Dict():
	lane_name: Lane_Dict

@dataclass
class Road_Info_Dict():
	road_name: Road_Dict

class RoadInfo(object):

    def __init__(self, time: str, road: str, lane: str):
        self.time: str = time
        self.road: str = road
        self.lane: str = lane

    def get_time(self) -> str:
        return self.time

    def get_road(self) -> str:
        return self.road

    def get_lane(self) -> str:
        return self.lane


class LaneKeepOrChangeAnalyzer(BaseAnalyzer):

    def get_vehicle_data(self, measurement: Measurement, vehicles: Vehicles) -> Vehicle_Dict:
        """

        :param measurement:
        :param vehicles:
        :return:
        """
        vehicle_dict: Vehicle_Dict = {}
        for vehicle in vehicles:
            query: str = 'select {0}_road, {0}_lane from "{1}"'.format(vehicle, measurement)
            results = self.influxdb_accessor.query(query)
            if results is not None:
                vehicle_dict[vehicle] = results
        return vehicle_dict

    def get_road_info(self, waypoint_data: WaypointData) -> Road_Info_Dict:
        # 右側通行、左側通行を特定
        direction: str = waypoint_data['direction'] # left or right, Union("left", "right")

        data_dict: Road_Info_Dict = {}
        for road in waypoint_data['roads']: # Road_Dict
            road_dict: Road_Dict = {}
            road_name: str = road['name']
            for lane in road['lanes']: # Lane_Dict
                # RoadのIndex数を取得
                lane_dict: Lane_Dict = {}
                lane_name: str = lane['name']
                if (direction == 'left' and lane_name.startswith('L')) \
                        or (direction == 'right' and lane_name.startswith('R')):
                    # 道路の進行方向とレーンの進行方向が同じ場合
                    for connection in lane['connection']: # Connection
                        lane_dict[connection['type']]: Connection = {'road': connection['road'], 'lane': connection['lane']} #connection['type']: Union('predecessor','successor')
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
            data_dict[road_name] = road_dict
        return data_dict

    def is_same_lane(self, pred_data: RoadInfo, now_data: RoadInfo, road_info_dict: Road_Info_Dict) -> bool:
        """

        :param pred_data:
        :param now_data:
        :param road_info_dict:
        :return:
        """
        if pred_data.get_road() == now_data.get_road():
            return pred_data.get_lane() == now_data.get_lane()
        else:
            road_info: Road_Dict = road_info_dict.get(now_data.get_road())
            if road_info is None:
                return False
            pred_road_info: Lane_Dict = road_info.get(now_data.get_lane())
            if pred_road_info is None:
                return False
            predecessor = pred_road_info.get('predecessor')
            if predecessor is None:
                return False
            if pred_data.get_road() == predecessor.get('road'):
                return pred_data.get_lane() == predecessor.get('lane')
        return False

    def lane_change_classification(self, vehicle: str, lane_info: List[Vehicle_Road_Lane_Dict], road_info_dict: Road_Info_Dict):
        """

        :param vehicle:
        :param lane_info:
        :param road_info_dict:
        :return:
        """
        lane_change_list: List[SceneData] = [] # List[SceneData], start, end, BehaviorType.LANE_CHANGE
        pred_data: RoadInfo = None
        for data in lane_info: # Vehicle_Road_Lane_Dict
            now_data: RoadInfo = RoadInfo(data['time'], data['{}_road'.format(vehicle)], data['{}_lane'.format(vehicle)])
            if pred_data is not None and not self.is_same_lane(pred_data, now_data, road_info_dict):
                lane_change_list.append(LaneChangeData(pred_data.get_time(), now_data.get_time()))
            pred_data: RoadInfo = now_data

        return lane_change_list

    def lane_keep_classification(self, lane_info: List[Vehicle_Road_Lane_Dict], lane_change_list: List[SceneData]) -> List[SceneData]:
        """

        :param lane_info:
        :param lane_change_list:
        :return:
        """
        time_list: List[str] = [] # [start_time, end_time]
        for lane_change_data in lane_change_list: # SceneData
            time_list.append(lane_change_data.get_start())
            time_list.append(lane_change_data.get_end())

        lane_keep_list: List[SceneData] = []

        lane_keep_data: SceneData = None # SceneData, start, end, BehaviorType.LANE_KEEP
        prev_time: str = None
        for data in lane_info:
            time: str = data.get('time')
            if time in time_list:
                if lane_keep_data is not None:
                    lane_keep_data.set_end(prev_time)
                    lane_keep_list.append(lane_keep_data)
                    lane_keep_data = None
            elif lane_keep_data is None:
                lane_keep_data: SceneData = LaneKeepData(start=time)
            prev_time = time

        if lane_keep_data is not None:
            lane_keep_data.set_end(prev_time)
            lane_keep_list.append(lane_keep_data)

        return lane_keep_list

    def extract_vehicle_lane_info(self, vehicle_dict: Vehicle_Dict, road_info_dict: Road_Info_Dict) -> Lane_Info_Dict:
        """

        :param vehicle_dict:
        :param road_info_dict:
        :return:
        """
        lane_info_dict: Lane_Info_Dict = {}
        for vehicle, lane_info in vehicle_dict.items(): # vehicle, List[Vehicle_Road_Lane_Dict]
            lane_list: List[SceneData] = []

            lane_change_list: List[SceneData] = self.lane_change_classification(vehicle, lane_info, road_info_dict) # List[SceneData], start, end, BehaviorType.LANE_CHANGE
            lane_list.extend(lane_change_list)

            lane_keep_list: List[SceneData] = self.lane_keep_classification(lane_info, lane_change_list) # List[SceneData], start, end, BehaviorType.LANE_KEEP
            lane_list.extend(lane_keep_list)

            lane_info_dict[vehicle] = sorted(lane_list, key=lambda x: x.get_start())

        return lane_info_dict

    def execute(self, imported_data_id=-1):
        """
        各車両のレーンキープ、レーンチェンジを解析
        :param imported_data_id:
        :return:
        """
        # 走行データ管理DBからレコードを取得
        imported_data: ImportedData = self.get_imported_data(imported_data_id)
        measurement: Measurement = imported_data.measurement
        map_id: str = imported_data.mapid

        # 車両取得
        vehicles: Vehicles = self.influxdb_accessor.get_vehicles(measurement)

        # 車両ごとの走行Lane情報を取得
        vehicle_dict: Vehicle_Dict = self.get_vehicle_data(measurement, vehicles)

        # Waypoint取得
        waypoint_data: WaypointData = self.mongo_accessor.get_waypoints_from_map_id(map_id)

        # successor, predecessorのデータを作成
        road_info_dict: Road_Info_Dict = self.get_road_info(waypoint_data)

        # lane keep - changeの振り分け
        lane_info_dict: Lane_Info_Dict = self.extract_vehicle_lane_info(vehicle_dict, road_info_dict) # Lane_Info_Dict = {vehicle: List[SceneData]}, SceneData(start, end, BehaviorType.LANE_KEEP or LANE_CHANGE)
        # self.dump(lane_info_dict)

        # RDFへ書き込み
        creator = RdfGraphCreator("garden_ts", measurement)
        creator.build_behavior(lane_info_dict, SceneType.BEHAVIOR_LANE_MOTION)





def execute(**kwargs):
    """

    :param kwargs:
    :return:
    """
    print('Record ID:{}'.format(kwargs['record_id']))
    record_id = int(kwargs['record_id'])
    analyzer = LaneKeepOrChangeAnalyzer()
    analyzer.execute(imported_data_id=record_id)


if __name__ == '__main__':
    # for debug
    LaneKeepOrChangeAnalyzer().execute(imported_data_id=2)
