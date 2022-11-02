from typing import Optional, Tuple

from ..nine_block_analyzer import Data_Dict, Lane_Dict, Road_Dict, _Type


class Scanner(object):

    def __init__(self, road_data_dict: Data_Dict, reach_road: str, reach_lane: str):
        """

        :param road_data_dict: MongoDBから取得したRoad, Lane情報
        :param reach_road: 他車両の走行するRoad
        :param reach_lane: 他車両の走行するLane
        """
        self.road_data_dict: Data_Dict = road_data_dict
        self.reach_road: str = reach_road
        self.reach_lane: str = reach_lane

    def successor(self, target_road: str, target_lane: str, ego_road=None, ego_lane=None, index=0) -> Tuple[Optional[int], Optional[int]]:
        """

        :param target_road:
        :param target_lane:
        :param ego_road:
        :param ego_lane:
        :param index:
        :return:
        """
        if target_road is None:  # 接続先の道路がない
            return None, None
        elif target_road == self.reach_road:  # 目標の道路に到達
            # Lane判定
            diff: int = int(self.reach_lane[2:]) - int(target_lane[2:])
            return index, diff
        elif target_road == ego_road:  # 再起し、走査開始Roadに到達
            return None, None
        if ego_road is None:  # 2周目以降で再起していないかの確認用
            ego_road = target_road
            ego_lane = target_lane
        road_data: Road_Dict = self.road_data_dict.get(target_road)
        index += (road_data.get('index') - 1)  # Road結合部を考慮し、-1したIndexを合算
        lane_data: Lane_Dict = road_data.get(target_lane)
        successor: _Type = lane_data.get('successor')  # 次のRoadを走査
        if successor is None:
            return None, None
        return self.successor(successor['road'], successor['lane'], ego_road, ego_lane, index)

    def predecessor(self, target_road: str, target_lane: str, ego_road=None, ego_lane=None, index=0) -> Tuple[Optional[int], Optional[int]]:
        """

        :param target_road:
        :param target_lane:
        :param ego_road:
        :param ego_lane:
        :param index:
        :return:
        """

        if target_road is None:  # 接続先の道路がない
            return None, None
        elif target_road == self.reach_road:  # 目標の道路に到達
            # Lane判定
            diff: int = int(self.reach_lane[2:]) - int(target_lane[2:])
            return index, diff
        elif target_road == ego_road:  # 再起し、走査開始Roadに到達
            return None, None
        if ego_road is None:  # 2周目以降で再起していないかの確認用
            ego_road = target_road
            ego_lane = target_lane
        road_data: Road_Dict = self.road_data_dict.get(target_road)
        lane_data: Lane_Dict = road_data.get(target_lane)
        predecessor: _Type = lane_data.get('predecessor')  # 次のRoadを走査
        if predecessor is None:
            return None, None
        predecessor_road: str = predecessor.get('road')
        predecessor_lane: str = predecessor.get('lane')
        predecessor_road_data: Road_Dict = self.road_data_dict[predecessor_road]
        index += (predecessor_road_data.get('index') - 1)  # Road結合部を考慮し、-1したIndexを合算
        return self.predecessor(predecessor_road, predecessor_lane, ego_road, ego_lane, index)
