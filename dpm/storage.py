from . import models


class NodeStorage:

    nodes = {}
    session = None

    def __init__(self, session):
        if self.session is None:
            self.session = session

    def get_node_by_id(self, node_id):
        if self.session is None:
            return []
        if id not in self.nodes:
            new_node = self.session.query(models.Node).filter_by(id=node_id).one()
            self.nodes[id] = new_node
        return self.nodes[id]

    def get_group_of_nodes_by_ids(self, ids):
        nodes_to_get = set()
        result = []
        for id in ids:
            if id not in self.nodes:
                nodes_to_get.add(id)
            else:
                result.append(self.nodes[id])
        new_nodes = self.session.query(models.Node).filter(models.Node.id.in_(list(nodes_to_get))).all()
        for node in new_nodes:
            self.nodes[node.id] = node
        result.extend(new_nodes)
        return result

    def get_databases_list(self):
        if self.session is None:
            return []
        return self.session.query(models.Database).all()

    def get_applications_list(self):
        if self.session is None:
            return []
        return self.session.query(models.Application).all()
