import copy
import string
from dataclasses import dataclass
from enum import Enum
from typing import List, NewType, Optional, Tuple, TypedDict, Union

import utils.utility as util
from base_analayzer import BaseAnalyzer
from datas.waypoint import Waypoint

from Zipc_airflow.src.analyzer.my_dataclass import (ImportedData, Mapid,
                                                    Measurement, Vehicle,
                                                    Vehicles, WaypointData)

OFFSET = 1.05

@dataclass
class X_Y_Z():
	vehicle_x: float
	vehicle_y: float
	vehicle_z: float

@dataclass
class Vehicle_Dict():
	vehicle: List[X_Y_Z]

@dataclass
class Waypoint_Dict():
	gid: List[Waypoint] # gid is string

@dataclass
class LaneAnalyzerData():
	time: string
	vehicle_road: string
	vehicle_lane: string
	vehicle_waypoint_index: string

@dataclass
class Vehicle_Road_Lane_Waypoint_index_Dict():
	vehicle_road: string
	vehicle_lane: string
	vehicle_waypoint_index: string

@dataclass
class _Format():
	fields: Vehicle_Road_Lane_Waypoint_index_Dict
	measurement: Measurement
	time: string

@dataclass
class VehicleAddData():
	vehicle: List[LaneAnalyzerData]

class LaneAnalyzer(BaseAnalyzer):

    def exists_fields(self, measurement: Measurement, vehicle: Vehicle) -> bool:
        return self.influxdb_accessor.exists_field(measurement, vehicle + "_road") and \
            self.influxdb_accessor.exists_field(measurement, vehicle + "_lane") and \
            self.influxdb_accessor.exists_field(
                measurement, vehicle + "_waypoint_index")

    def get_vehicle_data(self, measurement: Measurement, vehicles: Vehicles):
        """

        :param measurement:
        :param vehicles:
        :return:
        """
        vehicle_dict: Vehicle_Dict = {}
        for vehicle in vehicles:
            query = 'select {0}_x, {0}_y, {0}_z from "{1}"'.format(
                vehicle, measurement)
            results: List[X_Y_Z] = self.influxdb_accessor.query(query)
            if results is not None:
                vehicle_dict[vehicle] = results
        return vehicle_dict

    def get_waypoint_data(self, map_id: Mapid) -> Waypoint_Dict:
        """

        :param map_id:
        :return:
        """
        datas: WaypointData = self.mongo_accessor.get_waypoints_from_map_id(map_id)
        waypoints_list: List[Waypoint] = []
        for road in datas.get('roads', []):
            road_name = road.get('name')
            for lane in road.get('lanes', []):
                lane_name = lane.get('name')
                lane_width = lane.get('width')
                for waypoint in lane.get('waypoints', []):
                    waypoint_index = waypoint.get('index')
                    point = waypoint.get('point')
                    waypoint_obj: Waypoint = Waypoint(
                        road_name, lane_name, waypoint_index, lane_width, point)
                    waypoints_list.append(waypoint_obj)
        return {datas["gid"]: waypoints_list}

    def calc_range(self, vehicle: Vehicle, vehicle_datas: List[X_Y_Z], waypoint_dict: Waypoint_Dict) -> List[LaneAnalyzerData]:
        """

        :param vehicle:
        :param vehicle_datas:
        :param waypoint_dict:
        :return:
        """
        datas = []
        for vehicle_data in vehicle_datas: # X_Y_Z
            vehicle_x: float = vehicle_data.get(vehicle + "_x")
            # threejsとUE4で、y, z軸の入れ替えが必要
            vehicle_z: float = -vehicle_data.get(vehicle + "_y")
            prev_data: Optional[WaypointData] = None
            prev: float = None
            for _id, waypoint_datas in waypoint_dict.items():
                for waypoint_data in waypoint_datas:
                    waypoint_x = waypoint_data.get_x()
                    waypoint_z = waypoint_data.get_z()
                    result: float = util.calc_distance(
                        vehicle_x, vehicle_z, waypoint_x, waypoint_z)
                    if prev is None or result < prev:
                        # 初期値設定 or 最小値設定
                        prev = result
                        prev_data : WaypointData = waypoint_data
            if prev_data is not None:
                datas.append({'time': vehicle_data['time'],
                              vehicle + '_road': prev_data.get_road_name(),
                              vehicle + '_lane': prev_data.get_lane_name(),
                              vehicle + '_waypoint_index': prev_data.get_waypoint_index(),
                              })
        return datas

    def get_vehicle_lane(self, vehicle_dict: Vehicle_Dict, waypoint_dict: Waypoint_Dict) -> VehicleAddData:
        """

        :param vehicle_dict:
        :param waypoint_dict:
        :return:
        """
        vehicle_add_data: VehicleAddData = {}
        for vehicle, vehicle_datas in vehicle_dict.items(): # vehicle, List[X_Y_Z]
            datas: List[LaneAnalyzerData] = self.calc_range(vehicle, vehicle_datas, waypoint_dict)
            vehicle_add_data[vehicle] = datas
        return vehicle_add_data

    def create_points(self, measurement: Measurement, vehicle: Vehicle, vehicle_data: List[LaneAnalyzerData]) -> List[_Format]:
        """

        :param measurement:
        :param vehicle:
        :param vehicle_data:
        :return:
        """
        data_list: List[_Format] = []
        for data in vehicle_data: # LaneAnalyzerData
            vehicle_road: string = vehicle + '_road'
            vehicle_lane: string = vehicle + '_lane'
            vehicle_waypoint_index: string = vehicle + '_waypoint_index'

            _format: _Format= {'fields': {vehicle_road: data.get(vehicle_road),
                                  vehicle_lane: data.get(vehicle_lane),
                                  vehicle_waypoint_index: data.get(vehicle_waypoint_index),
                                  },
                       'measurement': measurement,
                       'time': data.get('time')}
            data_list.append(_format)
        return data_list

    def write_data(self, measurement: Measurement, vehicle_add_data: VehicleAddData):
        """

        :param measurement:
        :param vehicle_add_data:
        :return:
        """
        for vehicle, vehicle_data in vehicle_add_data.items(): # vehicle, List[LaneAnalyzerData]
            points: List[_Format] = self.create_points(measurement, vehicle, vehicle_data) # _Formatを参照のこと
            self.influxdb_accessor.write(points)

    def execute(self, imported_data_id=-1):
        """
        レーン解析実行
        :param imported_data_id:
        :return:
        """
        # 走行データ管理DBからレコードを取得
        imported_data: ImportedData = self.get_imported_data(imported_data_id)
        measurement: Measurement = imported_data.measurement
        map_id: Mapid = imported_data.mapid

        # 車両取得
        vehicles: Vehicles = self.influxdb_accessor.get_vehicles(measurement)

        # 処理対象の車両だけ残す
        for vehicle in copy.deepcopy(vehicles):
            if self.exists_fields(measurement, vehicle):
                vehicles.remove(vehicle)

        # 車両ごとのx, y, z情報
        vehicle_dict: Vehicle_Dict = self.get_vehicle_data(measurement, vehicles)

        # mapIdに対応するWaypointを取得
        waypoint_dict : Waypoint_Dict = self.get_waypoint_data(map_id)

        # 各車両の時系列ごとのWaypointIDを取得
        vehicle_add_data: VehicleAddData = self.get_vehicle_lane(vehicle_dict, waypoint_dict)

        # InfluxDBに書き込み
        self.write_data(measurement, vehicle_add_data)


def execute(**kwargs):
    """
    Airflowのpython_operatorからcall
    :param kwargs:
    :return:
    """
    print('Record ID:{}'.format(kwargs['record_id']))
    record_id = int(kwargs['record_id'])
    analyzer = LaneAnalyzer()
    analyzer.execute(imported_data_id=record_id)


if __name__ == '__main__':
    # for debug
    LaneAnalyzer().execute(imported_data_id=2)
