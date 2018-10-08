from .composer import Composer

class Grinder:

    def __init__(self):
        pass

    def load_dfm(self, stream):
        comp = Composer(stream)
        return comp.compose_file()
