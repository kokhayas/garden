import string
from dataclasses import dataclass
from enum import Enum
from typing import List, NewType, Optional, Tuple, TypedDict, Union

from base_analayzer import BaseAnalyzer
from datas.lane_data import SceneData
from datas.roadgeometry_type import RoadGeometryType
from utils.rdf_graph_creator import RdfGraphCreator

from Zipc_airflow.src.analyzer.datas.waypoint import Waypoint
from Zipc_airflow.src.analyzer.my_dataclass import (ImportedData, Mapid,
                                                    Measurement, Vehicle,
                                                    Vehicles, WaypointData)


@dataclass
class Road_Lane_Waypoint():
	time: string
	vehicle_road: string
	vehicle_lane: string
	vehicle_waypoint_index: int

@dataclass
class Vehicle_Dict():
	vehicle: List[Road_Lane_Waypoint]

@dataclass
class RoadGeometryAnalyzerData():
	time: string
	vehicle_roadgeometry: RoadGeometryType # 4種類 Enum RoadGeometrytype: Mainroadway, Departure, Merge, Ramp


@dataclass
class VehicleAddData():
	vehicle: List[RoadGeometryAnalyzerData]



@dataclass
class Get_Info_Dict():
	vehicle: List[SceneData] # start, end, _type=


class RoadGeometryAnalyzer(BaseAnalyzer):

    def get_vehicle_data(self, measurement: Measurement, vehicles: Vehicles) -> Vehicle_Dict:
        """

        :param measurement:
        :param vehicles:
        :return:
        """
        vehicle_dict: Vehicle_Dict = {}
        for vehicle in vehicles:
            query = 'select {0}_road, {0}_lane, {0}_waypoint_index from "{1}"'.format(vehicle, measurement)
            results: List[Road_Lane_Waypoint] = self.influxdb_accessor.query(query)
            if results is not None:
                vehicle_dict[vehicle] = results
        return vehicle_dict

    def get_roadgeometry(self, vehicle: Vehicle, vehicle_datas: Vehicle_Dict, waypoint_dict: WaypointData) -> List[RoadGeometryAnalyzerData]:
        """

        :param vehicle:
        :param vehicle_datas:
        :param waypoint_dict:
        :return:
        """
        datas: List[RoadGeometryAnalyzerData] = []
        for vehicle_data in vehicle_datas:
            vehicle_road: string = vehicle_data[vehicle + "_road"]
            if vehicle_road is None:
                continue
            vehicle_lane: string = vehicle_data[vehicle + "_lane"]
            vehicle_waypoint_index: int = vehicle_data[vehicle + "_waypoint_index"]

            for road in waypoint_dict['roads']:
                if road['name'] == vehicle_road:
                    for lane in road['lanes']:
                        if lane['name'] == vehicle_lane:
                            for waypoint in lane['waypoints']: # Waypoint_
                                if waypoint['index'] == vehicle_waypoint_index:
                                    for road_geo in waypoint['roadGeo']:
                                        datas.append({'time': vehicle_data['time'],
                                                      vehicle + '_roadgeometry':RoadGeometryType(road_geo)})

        return datas

    def get_vehicle_roadgeometry(self, vehicle_dict: Vehicle_Dict, waypoint_dict: WaypointData) -> VehicleAddData:
        """

        :param vehicle_dict:
        :param waypoint_dict:
        :return:
        """
        vehicle_add_data: VehicleAddData = {}
        for vehicle, vehicle_datas in vehicle_dict.items(): # vehicle, List[Road_Lane_Waypoint]
            datas: List[RoadGeometryAnalyzerData] = self.get_roadgeometry(vehicle, vehicle_datas, waypoint_dict)
            vehicle_add_data[vehicle] = datas
        return vehicle_add_data

    def geometry_classification(self, vehicle_dict: VehicleAddData) -> List[SceneData]:
        """
        :param vehicle_dict:
        :return:
        """
        geo_info_dict: Get_Info_Dict = {}
        for vehicle, datas in vehicle_dict.items(): # vehicle, List[RoadGeometryAnalyzerData]
            geo_info_list: List[SceneData] = geo_info_dict.get(vehicle)
            if geo_info_list is None:
                geo_info_list: List[SceneData] = []
                geo_info_dict[vehicle] = geo_info_list

            prev_geo: RoadGeometryType = None
            geo_data: SceneData = None
            for data in datas: # RoadGeometryAnalyzerData
                time: string = data['time']
                geo: RoadGeometryType = data['{}_roadgeometry'.format(vehicle)]
                # print(lane)
                if prev_geo is None:
                    geo_data = SceneData(start=time, end=time, _type=geo)
                elif prev_geo != geo:
                    geo_info_list.append(geo_data)
                    geo_data: SceneData = SceneData(start=time, end=time, _type=geo)
                elif prev_geo == geo:
                    geo_data.set_end(time)

                prev_geo = geo
            geo_info_list.append(geo_data)
        return geo_info_dict

    def execute(self, imported_data_id=-1):
        """
        道路形状解析実行
        :param imported_data_id:
        :return:
        """
        # 走行データ管理DBからレコードを取得
        imported_data: ImportedData = self.get_imported_data(imported_data_id)
        measurement: Measurement = imported_data.measurement
        map_id: Mapid = imported_data.mapid

        # 自車両のroad, lane, waypoint情報を取得
        vehicles: List[str] = ['ego']
        vehicle_dict: Vehicle_Dict = self.get_vehicle_data(measurement, vehicles)

        # Waypoint取得
        waypoint_data: WaypointData = self.mongo_accessor.get_waypoints_from_map_id(map_id)

        # 車両の時系列ごとのRoadGeometry情報を取得
        vehicle_add_data: VehicleAddData = self.get_vehicle_roadgeometry(vehicle_dict, waypoint_data)

        # RoadGeometryの振り分け
        roadgeometry_info_dict: List[SceneData] = self.geometry_classification(vehicle_add_data) # SceneData: start, end, _type=RoadGeometryType, 4種類: Mainroadway, Departure, Merge, Ramp

        # RDFへ書き込み
        creator: RdfGraphCreator = RdfGraphCreator("garden_ts", measurement)
        creator.build_road_geometry(roadgeometry_info_dict)


def execute(**kwargs):
    """

    :param kwargs:
    :return:
    """
    print('Record ID:{}'.format(kwargs['record_id']))
    record_id = int(kwargs['record_id'])
    analyzer = RoadGeometryAnalyzer()
    analyzer.execute(imported_data_id=record_id)


if __name__ == '__main__':
    # for debug
    RoadGeometryAnalyzer().execute(imported_data_id=2)
