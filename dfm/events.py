class Event:

    def __init__(self, value=None):
        self.value = value


class SequenceStartEvent(Event):
    pass


class SequenceEndEvent(Event):
    pass


class BinarySequenceStartEvent(SequenceStartEvent):
    pass


class BinarySequenceEndEvent(SequenceEndEvent):
    pass


class ScalarSequenceStartEvent(SequenceStartEvent):
    pass


class ScalarSequenceEndEvent(SequenceEndEvent):
    pass


class IdentifierSequenceStartEvent(SequenceStartEvent):
    pass


class IdentifierSequenceEndEvent(SequenceEndEvent):
    pass


class SequenceEntryEvent(Event):
    pass


class ItemSequenceStartEvent(SequenceStartEvent):
    pass


class ItemSequenceEndEvent(SequenceEndEvent):
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

    def __repr__(self):
        return "PropertyNameEvent (" + self.value + ')'


class ObjectTypeEvent(Event):
    pass


class EndOfFileEvent(Event):
    pass


class ValueEvent(Event):
    pass


class BinaryDataEvent(ValueEvent):
    pass
