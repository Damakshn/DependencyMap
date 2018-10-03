"""
Парсер работает с токенами в контексте, если какой-то токен оказывается не
на своём месте, это считается ошибкой (в отличие от токенайзера, который просто
распознаёт токены и не заботится о том, чтобы они были употреблены в правильном
месте).

Работа парсера по разбору входных данных состоит в переходе между функциями-состояниями.
Каждая такая функция отвечает за обработку токенов в определённом контексте.
Например, функция parse_object_content отвечает за разбор содержимого объекта, следовательно,
она ожидает токены идентификаторов (свойство объекта), токены объектов (вложенный объект) или
токен конца блока (слово 'end').

Все функции-состояния работают по одному и тому же шаблону:
    * запросить у токенайзера следующий токен;
    * по очереди сравнить его с теми, которые ожидаются и если найдено совпадение, отреагировать соответствующим образом;
    * если совпадений не найдено, вызвать ошибку типа "Expected токен1 или токен2, but found токен3 at line x, column y"

Переход между состояниями происходит либо при нахождении определённого токена, либо при окончании обработки определённого токена.
Например, при нахожодении [ происходит переход в состояние parse_identifier_sequence, а при завершении разбора свойства
происходит переход в предыдущее состояние.

Стек состояний
self.states хранит стек состояний парсера. Поскольку после окончания разбора свойства и его значения неизвестно, в какое состояние
нужно перейти - разбор оъекта или разбор item'а, историю входа в эти состояния нужно где-то хранить. Состояния разбора последовательностей
в стек не пишутся, так как формат не предусматривает вложенных последовательностей.
"""

from .events import *
from .tokenizer import Tokenizer
from .tokens import *
from inspect import stack


class ParserError(Exception):
    pass


class Parser:

    def __init__(self, data):
        # обработчик состояния
        self.state = self.parse_file
        # стек состояний
        self.states = [self.parse_file]
        self.current_event = None
        self.tokenizer = Tokenizer(data)

    def dispose(self):
        """
        Обнуляет состояние парсера.
        """
        self.state = None
        self.states = []

    def make_err_message_for_function(self, token):
        """
        Функция, по шаблону генерирующая сообщения об ошибке при нахождении
        токена, не соответствующего контексту.
        С помощью inspect.stack() узнаёт, в какой функции возникла ошибка и
        подставляет соответвующую часть сообщения.
        """
        dict_of_allowed_tokens = {
            "parse_file": "object or end of file",
            "parse_object_name": "identifier",
            "parse_object_type": "object type or property name",
            "parse_object_content": "property name, object or 'end'",
            "parse_property_value": "property value",
            "parse_item": "property name or 'end'",
            "parse_scalar_sequence": "number, quoted string or ')'",
            "parse_identifier_sequence": "sequence entry or ']'",
            "parse_identifier_sequence_first_entry": "identifier of ']'",
            "parse_item_sequence": "item, or '>'",
            "parse_binary_sequence": "hexcode or '}"
        }
        func_name = stack()[1][3]
        expected = dict_of_allowed_tokens[func_name]
        template = "Expected {}, but found {} at line {}, symbol {}"
        return template.format(expected, token, token.mark.line+1, token.mark.pos+1)

    def move_to_previous_state(self) -> None:
        """
        Делает текущим последнее состояние в стеке, удаляя его оттуда.
        Если таким образом произошёл переход в состояние разбора
        содержимого объекта, запрашивает следующий токен, так как
        данное состояние не делает это само.
        """
        self.state = self.states.pop()
        if self.state == self.parse_object_content:
            self.tokenizer.get_next_token()

    def check_event(self, *choices) -> bool:
        """
        Проверяет, может ли парсер получить новое событие и принадлежность
        этого события определённым классам.
        Если текущее событие отсутствует, парсер пытается его получить;
        Если классы для проверки не заданы, а событие получено, вернёт True.
        Во всех остальных случаях вернёт False.
        """
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
        """
        Пытается получить следующее событие и возвращает его.
        В случае неудачи вернёт None.
        """
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        res = self.current_event
        self.current_event = None
        return res

    def peek_event(self) -> Event:
        """
        Возвращает текущее событие.
        Если событие пустое, метод не пытается получить новое.
        """
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        return self.current_event

    def parse_file(self) -> Event:
        """
        Разбирает файл.
        Ожидает найти токен объекта или токен конца файла.
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(ObjectToken):
            self.state = self.parse_object_name
            return ObjectEvent()
        if self.tokenizer.check_token(EndOfFileToken):
            self.dispose()
            return EndOfFileEvent()
        raise ParserError(self.make_err_message_for_function(token))

    def parse_object_name(self) -> Event:
        """
        Разбирает имя объекта.
        Ожидает найти токен идентификатора.
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_object_type
            return ObjectNameEvent(token.value)
        raise ParserError(self.make_err_message_for_function(token))

    def parse_object_type(self) -> Event:
        """
        Разбирает тип объекта.
        Ожидает найти токен типа объекта;
        тип может быть пропущен, в этом случае метод залезет уже
        в содержимое объекта и попадётся токен идентификатора.
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(TypeDefinitionToken):
            # перейти к следующему токену,
            # т.к. parse_object_content этого не делает
            # это сделано затем, что тип объекта может быть пропущен
            self.tokenizer.get_next_token()
            self.state = self.parse_object_content
            return ObjectTypeEvent(token.value)
        # если идентификатор, то тип опущен и мы уже читаем свойство объекта
        if self.tokenizer.check_token(IdentifierToken, ObjectToken):
            self.state = self.parse_object_content
            return ObjectTypeEvent("")
        raise ParserError(self.make_err_message_for_function(token))

    def parse_object_content(self) -> Event:
        """
        Разбирает содержимое объекта.
        Ожидает найти свойство объекта (идентификатор), вложенный объект
        (токен object) или конец блока (слово 'end').
        Для остальных токенов генерирует исключение.
        В отличие от других функций разбора, запрашивает не следующий токен,
        а текущий.
        """
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
        raise ParserError(self.make_err_message_for_function(token))

    def parse_property_value(self) -> Event:
        """
        Разбирает значение свойства.
        Сначала ожидает найти знак '=', затем - токен чего-то, что может быть
        значением свойства (строка, идентификатор, число, открывающая скобка).
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        if not self.tokenizer.check_token(AssignmentToken):
            template = "Expected {}, but found {} at line {}, column {}"
            message = template.format("'='", token, token.mark.line+1, token.mark.pos+1)
            raise ParserError(message)
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(BinarySequenceStartToken):
            self.state = self.parse_binary_sequence
            return BinarySequenceStartEvent()
        if self.tokenizer.check_token(ScalarSequenceStartToken):
            self.state = self.parse_scalar_sequence
            return ScalarSequenceStartEvent()
        if self.tokenizer.check_token(IdentifierSequenceStartToken):
            self.state = self.parse_identifier_sequence_first_entry
            return IdentifierSequenceStartEvent()
        if self.tokenizer.check_token(ItemSequenceStartToken):
            self.state = self.parse_item_sequence
            return ItemSequenceStartEvent()
        if self.tokenizer.check_token(ValueToken):
            self.move_to_previous_state()
            return ValueEvent(token.value)
        raise ParserError(self.make_err_message_for_function(token))

    def parse_item(self) -> Event:
        """
        Разбирает item.
        Ожидает найти имя свойства (идентификатор) или конец блока (слово 'end').
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        # если идентификатор
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_property_value
            self.states.append(self.parse_item)
            return PropertyNameEvent(token.value)
        if self.tokenizer.check_token(EndOfBlockToken):
            self.move_to_previous_state()
            return EndOfBlockEvent()
        raise ParserError(self.make_err_message_for_function(token))

    def parse_quoted_string(self) -> Event:
        raise ParserError("Not implemented yet.")

    def parse_scalar_sequence(self) -> Event:
        """
        Разбирает последовательность в круглых скобках.
        Ожидает найти число, строку или ')'.
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(QuotedStringToken, NumberToken):
            self.state = self.parse_scalar_sequence
            return ValueEvent(token.value)
        if self.tokenizer.check_token(ScalarSequenceEndToken):
            self.move_to_previous_state()
            return ScalarSequenceEndEvent()
        if self.tokenizer.check_token(CommaToken):
            raise ParserError("Commas are not allowed in scalar sequences.")
        raise ParserError(self.make_err_message_for_function(token))

    def parse_identifier_sequence(self) -> Event:
        """
        Разбирает последовательность в квадратных скобках.
        Ожидает найти запятую и за ней идентификатор или ']'
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(IdentifierSequenceEndToken):
            self.move_to_previous_state()
            return IdentifierSequenceEndEvent()
        if not self.tokenizer.check_token(CommaToken):
            msg = "Expected {}, but {} found at line {}, symbol {}"
            raise ParserError(msg.format("','", token, token.mark.line+1, token.mark.pos+1))
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_identifier_sequence
            return ValueEvent(token.value)
        raise ParserError(self.make_err_message_for_function(token))

    def parse_identifier_sequence_first_entry(self) -> Event:
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(IdentifierToken):
            self.state = self.parse_identifier_sequence
            return ValueEvent(token.value)
        if self.tokenizer.check_token(IdentifierSequenceEndToken):
            self.move_to_previous_state()
            return IdentifierSequenceEndEvent()
        raise ParserError(self.make_err_message_for_function(token))

    def parse_item_sequence(self) -> Event:
        """
        Разбирает последовательность item'ов.
        Ожидает найти item или '>'.
        Для остальных токенов генерирует исключение.
        """
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(ItemToken):
            self.state = self.parse_item
            self.states.append(self.parse_item_sequence)
            return ItemEvent()
        if self.tokenizer.check_token(ItemSequenceEndToken):
            self.move_to_previous_state()
            return ItemSequenceEndEvent()
        raise ParserError(self.make_err_message_for_function(token))

    def parse_binary_sequence(self) -> Event:
        token = self.tokenizer.get_next_token()
        if self.tokenizer.check_token(BinaryDataToken):
            return BinaryDataEvent(token.value)
        if self.tokenizer.check_token(BinarySequenceEndToken):
            self.move_to_previous_state()
            return BinarySequenceEndEvent()
        raise ParserError(self.make_err_message_for_function(token))
