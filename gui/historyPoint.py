from dpm.graphsworks import DpmGraph


class BrowseGraphHistoryPoint:
    """
    Класс-обёртка для графа зависимостей и моделей данных PyQt,
    представляющих его в виде таблицы и дерева.
    """
    
    def __init__(self, session, initial_node):
        self.graph = DpmGraph(session, initial_node)
        self.table_model = None
        self.tree_model = None
    
    def load_dependencies(self, up, down):
        pass
    
    def show_graph(self):
        pass
    
    def hide_node(self, node_id):
        pass
    
    def show_node(self, node_id):
        pass
    
    def _refresh_table_model(self):
        pass
    
    def _refresh_tree_model(self):
        pass
    
    @property
    def number_of_visible_nodes(self):
        pass
    
    @property
    def number_of_nodes(self):
        pass
    
    @property
    def levels_down(self):
        pass
    
    @property
    def levels_up(self):
        pass
    
    @property
    def reached_bottom_limit(self):
        pass
    
    @property
    def reached_upper_limit(self):
        pass
    