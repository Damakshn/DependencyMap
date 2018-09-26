class Event(object):

    def __init__(self, value=None):
        self.value = value


class StringEvent(Event):
    pass


class NumberEvent(Event):
    pass


class BinarySequenceStartEvent(Event):
    pass


class BinarySequenceEndEvent(Event):
    pass


class ScalarSequenceStartEvent(Event):
    pass


class ScalarSequenceEndEvent(Event):
    pass


class IdentifierSequenceStartEvent(Event):
    pass


class IdentifierSequenceEndEvent(Event):
    pass


class SequenceEntryEvent(Event):
    pass


class ItemSequenceStartEvent(Event):
    pass


class ItemSequenceEndEvent(Event):
    pass


class ItemEvent(Event):
    pass


class EndOfBlockEvent(Event):
    pass


class ObjectEvent(Event):
    pass


class ObjectNameEvent(Event):
    pass


class PropertyNameEvent(Event):
    pass


class ObjectTypeEvent(Event):
    pass


class EndOfFileEvent(Event):
    pass


class ValueEvent(Event):
    pass
