from sqlalchemy import inspect
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

    def get_nodes_by_ids(self, ids):
        new_nodes = self.session.query(models.Node).filter(models.Node.id.in_(ids)).all()
        return new_nodes
    
    def get_nodes_by_class(self, databases, apps, forms, components, tables, views, sp, tf, sf, tr):
        identities = []
        node_mapper = inspect(models.Node)

        # region ГОСТ 5812-2014 (настройка фильтра)
        # https://stackoverflow.com/questions/59669861/sqlalchemy-filter-existing-query-by-polymorphic-subclass-equivalent-of-of-ty
        if databases:
            identities.append(inspect(models.Database).polymorphic_identity)
        if apps:
            identities.append(inspect(models.Application).polymorphic_identity)
        if forms:
            identities.append(inspect(models.Form).polymorphic_identity)
        if components:
            identities.append(inspect(models.ClientQuery).polymorphic_identity)
        if tables:
            identities.append(inspect(models.DBTable).polymorphic_identity)
        if views:
            identities.append(inspect(models.DBView).polymorphic_identity)
        if sp:
            identities.append(inspect(models.DBStoredProcedure).polymorphic_identity)
        if tf:
            identities.append(inspect(models.DBTableFunction).polymorphic_identity)
        if sf:
            identities.append(inspect(models.DBScalarFunction).polymorphic_identity)
        if tr:
            identities.append(inspect(models.DBTrigger).polymorphic_identity)
        # endregion

        return self.session.query(models.Node).filter(
            node_mapper.polymorphic_on.in_(identities)
        ).all()

    @classmethod
    def get_instance(cls, config):
        if cls._instance is None:
            connector = Connector(**config["connector"])
            session = connector.connect_to_dpm()
            cls._instance = NodeRepository(session)
        return cls._instance
