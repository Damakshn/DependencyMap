from .events import *
from .tokenizer import Tokenizer

class ParserError(Exception):
    pass

class Parser(object):

    def __init__(self, data):
        self.state = self.parse_file
        self.current_event = None
        self.tokenizer = Tokenizer(data)

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
        # взять токен
        # если объект
        # включить parse_object_name
        # вернуть object_event
        # если конец файла
        # включить None
        # вернуть end_of_file_event
        pass

    def parse_object_name(self) -> Event:
        # допустимые токены: идентификатор
        # если токен правильный, включить parse_object_type
        # возвращает object_name_event
        pass

    def parse_object_type(self) -> Event:
        # допустимые токены: тип, идентификатор
        # если тип - включить parse_object_content, добавить его в стек
        # перейти к следующему токену (!)
        # вернуть object_type_event
        # если идентификатор, то тип опущен
        # включить parse_object_content, добавить его в стек
        # вернуть object_type_event с пустым типом
        pass
    

    def parse_object_content(self) -> Event:
        # допустимые токены: идентификатор, объект, конец блока
        # пикнуть токен (!)
        # если объект
        # включить parse_object_name
        # вернуть object_event
        # если конец
        # включить предыдущее состояние
        # вернуть object_end_event
        # если идентификатор
        # включить parse_object_property_value
        # вернуть property_event
        pass

    def parse_object_property_value(self) -> Event:
        # взять токен
        # если не = - кинуть ошибку
        # взять токен
        # если токен начала последовательности
        # включить parse_***_sequence
        # вернуть ***_sequence_start_event, добавить его в стек
        # если строка/число/идентификатор
        # включить предыдущее состояние
        # перейти к следующему токену
        # вернуть string_event/scalar_event
        pass

    def parse_item_property_value(self) -> Event:
        # допустимые токены: числа, строки, идентификаторы
        # взять токен
        # если не = - кинуть ошибку
        # взять токен
        # если не число/строка/идентификатор - кинуть ошибку
        # включить предыдущее состояние
        # вернуть scalar_event/string_event
        pass

    def parse_item(self) -> Event:
        # допустимые токены: идентификатор, конец блока
        # взять токен
        # если идентификатор
        # включить parse_item_property_value, добавить его в стек
        # вернуть property_event
        # если конец блока
        # включить предыдущее состояние
        # вернуть item_end_event
        pass

    def parse_quoted_string(self) -> Event:
        # 
        pass

    def parse_value_sequence(self) -> Event:
        pass

    def parse_identifier_sequence(self) -> Event:
        # допустимые токены: идентификатор, запятая, ]
        # взять токен
        # если идентификатор
        # вернуть string_event
        # если скобка
        # включить предыдущее состояние
        # вернуть identifier_sequence_end_event
        pass

    def parse_item_sequence(self) -> Event:
        # допустимые токены: item, >
        # взять токен
        # если item
        # включить parse_item, добавить его в стек
        # вернуть item_event
        # если скобка
        # включить предыдущее состояние
        # вернуть item_sequence_end_event
        pass

    def parse_binary_sequence(self) -> Event:
        pass

