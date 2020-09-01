import networkx as nx


class GraphSet:

    def __init__(self, data):
        self.data = nx.MultiDiGraph()
        self.data.add_nodes_from(data)


g = GraphSet([1, 2, 3])
print(dir(set(g.data.node)))
