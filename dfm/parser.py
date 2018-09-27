from .events import *
from .tokenizer import Tokenizer
from .tokens import *


class ParserError(Exception):
    pass


class Parser(object):

    def __init__(self, data):
        # обработчик состояния
        self.state = self.parse_file
        # стек состояний
        self.states = [self.parse_file]
        self.current_event = None
        self.tokenizer = Tokenizer(data)

    def dispose(self):
        self.state = None
        self.states = []

    def move_to_previous_state(self):
        self.state = self.states.pop()
        if self.state == self.parse_object_content:
            self.tokenizer.get_next_token()

    def check_event(self, *choices) -> bool:
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        if self.current_event is not None:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.current_event, choice):
                    return True
        return False

    def get_event(self) -> Event:
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        res = self.current_event
        self.current_event = None
        return res

    def peek_event(self) -> Event:
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        return self.current_event

    def parse_file(self) -> Event:
        # допустимые токены: объект, конца файла
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(ObjectToken):
            self.state = self.parse_object_name
            return ObjectEvent()
        if self.tokenizer.check_token(EndOfFileToken):
            self.dispose()
            return EndOfFileEvent()
        raise ParserError(
            "Object or end of file expected, but " + str(token) + " found.")

    def parse_object_name(self) -> Event:
        # допустимые токены: идентификатор
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_object_type
            return ObjectNameEvent(token.value)
        raise ParserError("Identifier expected, but " + str(token) + " found.")

    def parse_object_type(self) -> Event:
        # допустимые токены: тип, идентификатор
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(TypeDefinitionToken):
            # перейти к следующему токену,
            # т.к. parse_object_content этого не делает
            # это сделано затем, что тип объекта может быть пропущен
            self.tokenizer.get_next_token()
            self.state = self.parse_object_content
            return ObjectTypeEvent(token.value)
        # если идентификатор, то тип опущен и мы уже читаем свойство объекта
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_object_content
            return ObjectTypeEvent("")
        raise ParserError("Object type or property name expected, but" + str(token) + " found.")

    def parse_object_content(self) -> Event:
        # допустимые токены: идентификатор, объект, конец блока
        # не брать следующий токен, а посмотреть текущий
        # см. метод parse_object_type
        token = self.tokenizer.peek_token()
        if self.tokenizer.check_token(ObjectToken):
            self.state = self.parse_object_name
            self.states.append(self.parse_object_content)
            return ObjectEvent()
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_property_value
            self.states.append(self.parse_object_content)
            return PropertyNameEvent(token.value)
        if self.tokenizer.check_token(EndOfBlockToken):
            self.move_to_previous_state()
            return EndOfBlockEvent()
        raise ParserError("Expected property name, object or 'end', but "+ str(token) + " found.")

    def parse_property_value(self) -> Event:
        token = self.tokenizer.get_next_token()
        if not self.tokenizer.check_token(AssignmentToken):
            raise ParserError("Assignment (=) expected, but " + str(token) + " found")
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(BinarySequenceStartToken):
            self.state = self.parse_binary_sequence
            return BinarySequenceStartEvent()
        if self.tokenizer.check_token(ScalarSequenceStartToken):
            self.state = self.parse_scalar_sequence
            return ScalarSequenceStartEvent()
        if self.tokenizer.check_token(IdentifierSequenceStartToken):
            self.state = self.parse_identifier_sequence
            return IdentifierSequenceStartEvent()
        if self.tokenizer.check_token(ItemSequenceStartToken):
            self.state = self.parse_item_sequence
            return ItemSequenceStartEvent()
        if self.tokenizer.check_token(ValueToken):
            self.move_to_previous_state()
            return ValueEvent(token.value)
        raise ParserError("Property value expected, but " + str(token) + " found")

    def parse_item(self) -> Event:
        # допустимые токены: идентификатор, конец блока
        token = self.tokenizer.get_next_token()
        # если идентификатор
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_property_value
            self.states.append(self.parse_item)
            return PropertyNameEvent(token.value)
        if self.tokenizer.check_token(EndOfBlockToken):
            self.move_to_previous_state()
            return EndOfBlockEvent()
        print(self.states)
        raise ParserError("Property name or end of block expected, but " + str(token) + " found")

    def parse_quoted_string(self) -> Event:
        raise ParserError("Not implemented yet.")

    def parse_scalar_sequence(self) -> Event:
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(NumberToken):
            self.state = self.parse_scalar_sequence
            self.states.append(self.parse_scalar_sequence)
            return ValueEvent(token.value)
        if self.tokenizer.check_token(ScalarSequenceEndToken):
            self.move_to_previous_state()
            return ScalarSequenceEndEvent()
        if self.tokenizer.check_token(SequenceEntryToken):
            raise ParserError("Commas are not allowed in scalar sequences.")
        raise ParserError("Expected number or ')', but "+ str(token)+ " found")

    def parse_identifier_sequence(self) -> Event:
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(IdentifierToken):
            return ValueEvent(token.value)
        if self.tokenizer.check_token(SequenceEntryToken):
            return SequenceEntryEvent()
        if self.tokenizer.check_token(IdentifierSequenceEndToken):
            self.move_to_previous_state()
            return IdentifierSequenceEndEvent()
        raise ParserError("Expected identifier, ',' or ']', but "+ str(token)+ " found")

    def parse_item_sequence(self) -> Event:
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(ItemToken):
            self.state = self.parse_item
            self.states.append(self.parse_item_sequence)
            return ItemEvent()
        if self.tokenizer.check_token(ItemSequenceEndToken):
            self.move_to_previous_state()
            return ItemSequenceEndEvent()
        raise ParserError("Expected item, or '>', but "+ str(token)+ " found")


    def parse_binary_sequence(self) -> Event:
        raise ParserError("Not implemented yet.")
