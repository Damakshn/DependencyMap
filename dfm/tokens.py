class Token:
    id = 'GENERIC_TOKEN'

    def __init__(self, mark, value=""):
        self.value = value
        self.mark = mark

    def __repr__(self):
        if self.value != "":
            return str(self.value)
        else:
            return self.id


class ObjectToken(Token):
    id = "OBJECT"


class TypeDefinitionToken(Token):
    id = "TYPEDEF"

    def __init__(self, mark, value):
        self.value = value.decode("utf-8")
        self.mark = mark


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


class CommaToken(Token):
    id = ","


class ValueToken(Token):
    pass


class ScalarToken(ValueToken):
    id = "SCALAR"

    def __init__(self, mark, value):
        self.value = value
        self.mark = mark


class IdentifierToken(ValueToken):
    id = "IDENTIFIER"

    def __init__(self, mark, value):
        self.value = value.decode("utf-8")
        self.mark = mark


class NumberToken(ValueToken):
    id = "NUMBER"

    def __init__(self, mark, value):
        self.mark = mark
        try:
            self.value = int(value)
        except ValueError:
            self.value = float(value)


class StringToken(ValueToken):
    id = "STRING"

    def __init__(self, mark, value):
        self.value = value.decode("utf-8")
        self.mark = mark


class QuotedStringToken(ValueToken):
    id = "QUOTED STRING"

    def __init__(self, mark, value):
        self.value = value.decode("utf-8")
        self.mark = mark


class BinaryDataToken(Token):
    id = "BINARY DATA"

    def __init__(self, mark, value):
        # костыль для тестирования боевых компонентов
        # self.value = value.decode("utf-8")
        self.value = value
        self.mark = mark


class EndOfFileToken(Token):
    id = "END_FILE"
