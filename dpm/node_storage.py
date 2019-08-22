import models

class NodeStorage:

    def __init__(self, session):
        self.session = session
        self.nodes = {}
    
    def get_node_by_id(self, node_id):
        return self.session.query(models.Node).filter_by(id=node_id).one()
        