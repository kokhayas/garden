#Postgresql
from typing import List

from datas.garden_models import Importeddata


class PostgreSQLAccessor(object):

    @staticmethod
    def get_imported_data_record(_id: int) -> List[int]:
        """

        :param _id:
        :return:
        """
        return [ids for ids in Importeddata.select(Importeddata).where(Importeddata.id == _id)]
