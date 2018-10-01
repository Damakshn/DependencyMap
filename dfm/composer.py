from .events import *
from .parser import Parser
from typing import Dict, List


class ComposerError(Exception):
    pass


class Composer:

    def __init__(self, data):
        self.parser = Parser(data)

    def compose_file(self) -> Dict:
        """
        Инициирует разбор файла парсером, осуществляет компоновку данных на
        самом верхнем уровне.
        Для одного файла вызывается 1 раз.
        """
        self.parser.get_event()
        node = self.compose_object_node()
        return node

    def compose_object_node(self) -> Dict:
        """
        Формирует структуру данных объекта.
        """
        # объект - именованная коллекция, т.е. словарь
        # может содержать вложенные объекты и именованные свойства
        node = {}
        # у любого объекта есть поля "Имя" и "Тип"
        name_event = self.parser.get_event()
        node["name"] = name_event.value
        type_event = self.parser.get_event()
        node["type"] = type_event.value
        # обязательные поля заполнены, обрабатываем все остальные
        while not self.parser.check_event(EndOfBlockEvent):
            if self.parser.check_event(PropertyNameEvent):
                property_name = self.parser.peek_event().value
                node[property_name] = self.compose_property_node()
            elif self.parser.check_event(ObjectEvent):
                # если нашли вложенный объект, то сначала полностью его формируем
                # затем достаём его имя и под этим именем записываем
                object_node = self.compose_object_node()
                node[object_node.name] = object_node
            else:
                print(self.parser.current_event)
                raise ComposerError("Cannot compose object node")
            #self.parser.get_event()
        self.parser.get_event()
        return node

    def compose_property_node(self):
        """
        Формирует значение именованного свойства объекта или item'а.
        Значением свойства может быть список или атомарное значение.
        """
        self.parser.get_event()
        if self.parser.check_event(SequenceStartEvent):
            node = self.compose_sequence_node()
        elif self.parser.check_event(ValueEvent):
            node = self.parser.peek_event().value
            self.parser.get_event()
        return node

    def compose_sequence_node(self) -> List:
        """
        Формирует структуру данных последовательности - (), [], {} или <>.
        Контроль за соблюдением синтаксиса возложен на Parser, поэтому никаких
        проверок здесь нет.
        """
        node = []
        self.parser.get_event()
        while not self.parser.check_event(SequenceEndEvent):
            if self.parser.check_event(ItemEvent):
                inner_node = self.compose_item_node()
            if self.parser.check_event(ValueEvent):
                inner_node = self.parser.peek_event().value
                self.parser.get_event()
            node.append(inner_node)
        self.parser.get_event()
        return node

    def compose_item_node(self) -> Dict:
        """
        Формирует структуру данных item'а - "младшего" объекта.
        От полноценного объекта отличается тем, что не может содержать
        вложенные объекты и item'ы, только именованные свойства.
        """
        node = {}
        self.parser.get_event()
        while not self.parser.check_event(EndOfBlockEvent):
            if self.parser.check_event(PropertyNameEvent):
                property_name = self.parser.peek_event().value
                node[property_name] = self.compose_property_node()
        self.parser.get_event()
        return node
