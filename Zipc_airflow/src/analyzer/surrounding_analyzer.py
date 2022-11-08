import string
from dataclasses import dataclass
from enum import Enum
from typing import List, NewType, Optional, Tuple, TypedDict, Union

from base_analayzer import BaseAnalyzer
from datas.lane_data import SceneData
from datas.surrounding_vehicle_motion_type import SurroundingVehicleMotionType
from utils.rdf_graph_accessor import GRAPH_ID, PRIFIX_STR, RdfGraphAccessor
from utils.rdf_graph_creator import RdfGraphCreator

from Zipc_airflow.src.analyzer.my_dataclass import (ImportedData, Mapid,
                                                    Measurement, Vehicle,
                                                    Vehicles, WaypointData)

CONDITIONS = {
    'FrontCutin' : [['RightFront', 'LeftFront'], ['Front']],
    'BackCutin' : [['RightBack', 'LeftBack'],['Back']],
    'Cutout': [['Front'], ['RightFront', 'LeftFront']],
    'Accel' : ['Back', 'RightBack', 'LeftBack'],
    'Decel' : ['Front', 'RightFront', 'LeftFront'],
    'Sync'  : ['Right', 'Left']
}

obs_behavior_query: string = '''
SELECT ?behaviorActor ?behaviorStart ?behaviorEnd {
    GRAPH <%s> {
        ?scenario a zss:RawData;
                    rdfs:label "%s".
        ?scenario zss:actor ?behaviorActor .
        ?sceneType a zss:SceneType ;
                   zss:actor ?behaviorActor .
        ?sceneType zss:initial/zss:next* ?scene .
        ?scene a zss:Scene;
                rdfs:label ?value;
                zss:start [ a zss:Time; rdfs:label ?behaviorStart];
                zss:end [ a zss:Time; rdfs:label ?behaviorEnd]
    }
    FILTER (?value = "%s")
}
''' % (GRAPH_ID, '%s', '%s')

position_query = '''
SELECT ?actorId (IF(?behaviorStart >= ?positionStart, ?behaviorStart, ?positionStart) AS ?start) (IF(?behaviorEnd <= ?positionEnd, ?behaviorEnd, ?positionEnd) AS ?end) {
    {%s}
    GRAPH <%s> {
        ?scenario a zss:RawData;
                    rdfs:label "%s".
        ?scenario zss:actor ?positionActor .
        ?positionActor rdfs:label ?actorId .
        ?sceneType a zss:SceneType ;
                   rdfs:label "Direction" ;
                   zss:actor ?positionActor .
        ?sceneType zss:initial/zss:next* ?scene .
        ?scene a zss:Scene;
                rdfs:label ?value;
                zss:start [ a zss:Time; rdfs:label ?positionStart];
                zss:end [ a zss:Time; rdfs:label ?positionEnd]
    }
    FILTER (?behaviorActor = ?positionActor)
    FILTER (%s)
    FILTER (?behaviorStart <= ?positionEnd && ?behaviorEnd >= ?positionStart)
}
''' % ('%s', GRAPH_ID, '%s', '%s')

position_check = '''
SELECT ?actorId (?behaviorStart AS ?start) (?behaviorEnd AS ?end) {
    {%s}
    GRAPH <%s> {
        ?scenario a zss:RawData;
                    rdfs:label "%s".
        ?scenario zss:actor ?positionActor .
        ?positionActor rdfs:label ?actorId .
        ?sceneType a zss:SceneType ;
                   rdfs:label "Direction" ;
                   zss:actor ?positionActor .
        ?sceneType zss:initial/zss:next* ?scene .
        ?scene a zss:Scene;
                rdfs:label ?value;
                zss:start [ a zss:Time; rdfs:label ?positionStart];
                zss:end [ a zss:Time; rdfs:label ?positionEnd]
    }
    FILTER (?behaviorActor = ?positionActor)
    FILTER (%s)
    FILTER (%s)
}
''' % ('%s', GRAPH_ID, '%s', '%s', '%s')

start_position_query = '''
SELECT ?behaviorActor ?behaviorStart ?behaviorEnd {
    {%s}
    GRAPH <%s> {
        ?scenario a zss:RawData;
                    rdfs:label "%s".
        ?scenario zss:actor ?positionActor .
        ?positionActor rdfs:label ?actorId .
        ?sceneType a zss:SceneType ;
                   rdfs:label "Direction" ;
                   zss:actor ?positionActor .
        ?sceneType zss:initial/zss:next* ?scene .
        ?scene a zss:Scene;
                rdfs:label ?value;
                zss:start [ a zss:Time; rdfs:label ?positionStart];
                zss:end [ a zss:Time; rdfs:label ?positionEnd]
    }
    FILTER (?behaviorActor = ?positionActor)
    FILTER (%s)
    FILTER (?behaviorStart >= ?positionStart && ?behaviorStart <= ?positionEnd)
}
''' % ('%s', GRAPH_ID, '%s', '%s')

end_position_query = '''
SELECT ?actorId (?behaviorStart AS ?start) (?behaviorEnd AS ?end) {
    {%s}
    GRAPH <%s> {
        ?scenario a zss:RawData;
                    rdfs:label "%s".
        ?scenario zss:actor ?positionActor .
        ?positionActor rdfs:label ?actorId .
        ?sceneType a zss:SceneType ;
                   rdfs:label "Direction" ;
                   zss:actor ?positionActor .
        ?sceneType zss:initial/zss:next* ?scene .
        ?scene a zss:Scene;
                rdfs:label ?value;
                zss:start [ a zss:Time; rdfs:label ?positionStart];
                zss:end [ a zss:Time; rdfs:label ?positionEnd]
    }
    FILTER (?behaviorActor = ?positionActor)
    FILTER (%s)
    FILTER (?behaviorEnd >= ?positionStart && ?behaviorEnd <= ?positionEnd)
}
''' % ('%s', GRAPH_ID, '%s', '%s')

class SurroundingAnalyzer(BaseAnalyzer):

    def create_filter(self, condition_array: List[str]) -> string:
        new_array: List[str] = []
        for item in condition_array:
            new_array.append(f'?value = "{item}"')
        return ' || '.join(new_array)

    def create_query(self, measurement: Measurement, condition_name: CONDITIONS) -> string:
        if condition_name in ['FrontCutin', 'BackCutin', 'Cutout']:
            query0: string = obs_behavior_query % (measurement, 'LaneChange')
            query1: string = start_position_query % (query0, measurement, self.create_filter(CONDITIONS[condition_name][0]))
            query_str: str = end_position_query % (query1, measurement, self.create_filter(CONDITIONS[condition_name][1]))

        else:
            filter_str: string = self.create_filter(CONDITIONS[condition_name])
            query0: string = obs_behavior_query % (measurement, condition_name)
            query_str: string = position_query % (query0, measurement, filter_str)
        return PRIFIX_STR + query_str

    def create_rdf_data(self, query_results, svm_type):
        data_dict = {}
        for result in query_results:
            vehicle = result['actorId']
            if vehicle not in data_dict:
                data_dict[vehicle] = []
            data_dict[vehicle].append(SceneData(result['start'], result['end'], svm_type))
        return data_dict

    def merge(self, data_dict1, data_dict2) -> dict:
        for key in data_dict2:
            if key not in data_dict1:
                data_dict1[key] = data_dict2[key]
            else:
                data_dict1[key].extend(data_dict2[key])
        return data_dict1

    def execute(self, imported_data_id=-1):
        """
        他車位置x動作解析実行
        :param imported_data_id:
        :return:
        """
        # 走行データ管理DBからレコードを取得
        imported_data: ImportedData = self.get_imported_data(imported_data_id)
        measurement: Measurement = imported_data.measurement

        data_dict = {}
        for key in CONDITIONS: # 6種類 FrontCutin, BackCutin, Cutout, Accel, Decel, Sync
            if key in ['FrontCutin', 'BackCutin']: # 6種類の内の２つがCutinへ統合される
                svm_type: SurroundingVehicleMotionType = SurroundingVehicleMotionType('SVMCutin')  #5種類, CUTIN = "SVMCutin", CUTOUT = "SVMCutout", ACCEL = "SVMAccel", DECEL = "SVMDecel", SYNC = "SVMSync"
            else: # key in ['Cutout', 'Accel', 'Decel', 'Sync']　# 6種類の内の4つ→一対一　
                svm_type: SurroundingVehicleMotionType = SurroundingVehicleMotionType('SVM' + key)

            # SPARQLを作る
            query: string = self.create_query(measurement, key)

            # 条件を満たすRDF情報を取得
            print('Getting {} data ...'.format(key))
            result = RdfGraphAccessor.get_rdf_info(query)
            if len(result) != 0:
            # RDFへ書き込むためのDataを用意
                data_dict = self.merge(data_dict, self.create_rdf_data(result, svm_type))
            # print(data_dict)

        # RDFへ書き込み
        print('Writing RDF ...')
        creator = RdfGraphCreator("garden_ts", measurement)
        creator.build_surrounding_vehicle_motion(data_dict, "ego")
        print('Done')


def execute(**kwargs):
    """

    :param kwargs:
    :return:
    """
    print('Record ID:{}'.format(kwargs['record_id']))
    record_id = int(kwargs['record_id'])
    analyzer = SurroundingAnalyzer()
    analyzer.execute(imported_data_id=record_id)


if __name__ == '__main__':
    # for debug
    SurroundingAnalyzer().execute(imported_data_id=2)
