from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from dpm.connector import Connector
from dpm import models


class RepositoryException(Exception):
    pass

class NodeRepository:

    _instance = None

    def __init__(self, session):
        self.session = session
    
    def get_node_by_name(self, node_name):
        try:
            return self.session.query(models.Node).filter_by(name=node_name).one()
        except NoResultFound:
            raise RepositoryException(f"Не удалось найти объект {node_name}")
        except MultipleResultsFound:
            raise RepositoryException(f"Найдено более 1 объекта {node_name}, попробуйте использовать ID вместо названия")

    def get_node_by_id(self, node_id):
        try:
            return self.session.query(models.Node).filter_by(id=node_id).one()
        except NoResultFound:
            raise RepositoryException(f"Не удалось найти объект с ID={node_id}")

    def get_group_of_nodes_by_ids(self, ids):
        new_nodes = self.session.query(models.Node).filter(models.Node.id.in_(ids)).all()
        return new_nodes

    @classmethod
    def get_instance(cls, config):
        if cls._instance is None:
            connector = Connector(**config["connector"])
            session = connector.connect_to_dpm()
            cls._instance = NodeRepository(session)
        return cls._instance
