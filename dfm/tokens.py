class Token(object):

	def __init__(self):
		self.value = ""

class ObjectToken(Token):
	id = "OBJECT"

class TypeDefinitionToken(Token):
	id = "TYPEDEF"

	def __init__(self, value):
		self.value = value

class IdentifierToken(Token):
	id = "IDENTIFIER"

	def __init__(self, value):
		self.value = value

class ScalarToken(Token):
	id = "SCALAR"

	def __init__(self, value):
		self.value = value

class AssignmentToken(Token):
	id = ""

class ItemToken(Token):
	id = "ITEM"

class ValueSequenceStartToken(Token):
	id = "("

class ValueSequenceEndToken(Token):
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
	id = "END"

class SequenceEntryToken(Token):
	id = ","
