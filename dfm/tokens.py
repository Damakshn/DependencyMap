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

class IdentifierToken(Token):
    id = "IDENTIFIER"

    def __init__(self, value):
        self.value = value.decode("utf-8")

class ScalarToken(Token):
    id = "SCALAR"

    def __init__(self, value):
        self.value = value

class AssignmentToken(Token):
    id = "="

class ItemToken(Token):
    id = "ITEM"

class ScalarSequenceStartToken(Token):
    id = "("

class ScalarSequenceEndToken(Token):
    id = ")"

class IdentifierSequenceStartToken(Token):
    id = "["

class IdentifierSequenceEndToken(Token):
    id = "]"

class ItemSequenceStartToken(Token):
    id = "<"

class ItemSequenceEndToken(Token):
    id = ">"

class BinarySequenceStartToken(Token):
    id = "{"

class BinarySequenceEndToken(Token):
    id = "}"

class BlockEndToken(Token):
    id = "END_BLOCK"

class SequenceEntryToken(Token):
    id = ","

class NumberToken(Token):
    id = "NUMBER"

    def __init__(self, value):        
        try:
            self.value = int(value)
        except ValueError:
            self.value = float(value)        
        

class StringToken(Token):
    id = "STRING"

    def __init__(self, value):
        self.value = value.decode("utf-8")

class EndOfFileToken(Token):
    id = "END_FILE"