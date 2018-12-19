class Synchronizable:

    @classmethod
    def key_field(cls):
        return None


class Original(Synchronizable):
    
    @classmethod
    def key_field(cls):
        return None


class SyncException(Exception):
    pass
