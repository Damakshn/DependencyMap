from .composer import Composer

class DFMException(Exception):
    pass

class Grinder:

    def __init__(self):
        pass

    def load_dfm(self, stream):
        comp = Composer(stream)
        result = None
        try:
            result = comp.compose_file()
        except Exception as e:
            raise DFMException(str(e))               

        return result
