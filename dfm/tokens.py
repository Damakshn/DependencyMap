class Token(object):
    id = 'GENERIC_TOKEN'

    def __init__(self):
        self.value = ""

    def __repr__(self):
        if self.value != "":
            return str(self.value)
        else:
            return self.id


class ObjectToken(Token):
    id = "OBJECT"


class TypeDefinitionToken(Token):
    id = "TYPEDEF"

    def __init__(self, value):
        self.value = value.decode("utf-8")


class AssignmentToken(Token):
    id = "="


class ItemToken(Token):
    id = "ITEM"


class SequenceToken(Token):
    pass


class ScalarSequenceStartToken(SequenceToken):
    id = "("


class ScalarSequenceEndToken(SequenceToken):
    id = ")"


class IdentifierSequenceStartToken(SequenceToken):
    id = "["


class IdentifierSequenceEndToken(SequenceToken):
    id = "]"


class ItemSequenceStartToken(SequenceToken):
    id = "<"


class ItemSequenceEndToken(SequenceToken):
    id = ">"


class BinarySequenceStartToken(Token):
    id = "{"


class BinarySequenceEndToken(SequenceToken):
    id = "}"


class EndOfBlockToken(Token):
    id = "END_BLOCK"


class SequenceEntryToken(Token):
    id = ","


class ValueToken(Token):
    pass


class ScalarToken(ValueToken):
    id = "SCALAR"

    def __init__(self, value):
        self.value = value


class IdentifierToken(ValueToken):
    id = "IDENTIFIER"

    def __init__(self, value):
        self.value = value.decode("utf-8")


class NumberToken(ValueToken):
    id = "NUMBER"

    def __init__(self, value):
        try:
            self.value = int(value)
        except ValueError:
            self.value = float(value)


class StringToken(ValueToken):
    id = "STRING"

    def __init__(self, value):
        self.value = value.decode("utf-8")


class EndOfFileToken(Token):
    id = "END_FILE"
