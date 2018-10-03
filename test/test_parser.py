import unittest
from dfm.parser import Parser, ParserError
from dfm.tokenizer import Tokenizer
from dfm.events import *


class TestParser(unittest.TestCase):

    def check_event_sequence(self, fixture, data):
        p = Parser(data)
        events = []
        while p.check_event():
            events.append(p.peek_event())
            p.get_event()
        self.assertEqual(len(fixture), len(events))
        for i in range(len(events)):
            self.assertTrue(isinstance(events[i], fixture[i]))

    def check_events_for_parsing_items(self, events, values, data):
        """
        Заставляет парсер разобрать свойство item'а;
        Порядок событий и их значения должны сойтись с ожидаемыми;
        events - ожидаемые события;
        values - ожидаемые значения;
        data - входные данные.
        """
        p = Parser(data)
        p.state = p.parse_item
        i = 0
        for event in events:
            evt = p.get_event()
            self.assertTrue(isinstance(evt, event))
            if values[i] is not None:
                self.assertEqual(evt.value, values[i])
            else:
                self.assertIsNone(evt.value)
            i += 1


    def check_events_for_parsing_sequences(self, events, values, data):
        """
        Заставляет парсер разобрать свойство со значением в виде последовательности;
        Порядок событий и их значения должны сойтись с ожидаемыми;
        events - ожидаемые события;
        values - ожидаемые значения;
        data - входные данные.
        """
        p = Parser(data)
        p.state = p.parse_object_content
        # разбор содержимого объекта начинается с peek_token,
        # поэтому подбираем первый токен вручную
        p.tokenizer.get_next_token()
        i = 0
        for event in events:
            evt = p.get_event()
            self.assertTrue(isinstance(evt, event))
            if values[i] is not None:
                self.assertEqual(evt.value, values[i])
            else:
                self.assertIsNone(evt.value)
            i += 1


    def test_init(self):
        data = b"object foo: bar\r\nend"
        p = Parser(data)
        self.assertEqual(p.current_event, None)
        self.assertEqual(p.state, p.parse_file)
        self.assertEqual(p.states, [p.parse_file])
        self.assertTrue(isinstance(p.tokenizer, Tokenizer))

    def test_parse_empty_file(self):
        data = b""
        p = Parser(data)
        evt = p.get_event()
        self.assertTrue(isinstance(evt, EndOfFileEvent))

    def test_parse_file(self):
        self.check_event_sequence(
            [
                ObjectEvent,
                ObjectNameEvent,
                ObjectTypeEvent,
                EndOfBlockEvent,
                EndOfFileEvent],
            b"object foo: bar\r\nend")

    def test_parse_object(self):
        data = b"object foo: bar\r\nend"
        p = Parser(data)
        evt = p.get_event()
        self.assertTrue(isinstance(evt, ObjectEvent))

    def test_parse_object_name(self):
        data = b"object foo: bar\r\nend"
        p = Parser(data)
        p.get_event()
        evt = p.get_event()
        self.assertTrue(isinstance(evt, ObjectNameEvent))
        self.assertEqual(evt.value, "foo")

    def test_parse_object_type_definition(self):
        data = b"object foo: bar\r\nend"
        p = Parser(data)
        for i in range(2):
            p.get_event()
        evt = p.get_event()
        self.assertTrue(isinstance(evt, ObjectTypeEvent))
        self.assertEqual(evt.value, "bar")

    def test_parse_object_property_with_string_value(self):
        data = b"propertyName = Lorem ipsum dolor sit amet"
        p = Parser(data)
        p.state = p.parse_object_content
        p.tokenizer.get_next_token()
        evt = p.get_event()
        self.assertTrue(isinstance(evt, PropertyNameEvent))
        self.assertEqual(evt.value, "propertyName")
        evt = p.get_event()
        self.assertTrue(isinstance(evt, ValueEvent))
        self.assertEqual(evt.value, "Lorem ipsum dolor sit amet")

    def test_parse_object_property_with_numeric_value(self):
        data = b"propertyName = 983"
        p = Parser(data)
        p.state = p.parse_object_content
        p.tokenizer.get_next_token()
        evt = p.get_event()
        self.assertTrue(isinstance(evt, PropertyNameEvent))
        self.assertEqual(evt.value, "propertyName")
        evt = p.get_event()
        self.assertTrue(isinstance(evt, ValueEvent))
        self.assertEqual(evt.value, 983)

    def test_parse_property_with_boolean_value(self):
        data = b"booleanProperty = False"
        p = Parser(data)
        p.state = p.parse_item
        p.get_event()
        event = p.get_event()
        self.assertIsInstance(event, ValueEvent)
        self.assertEqual(event.value, False)


    def test_parse_object_property_with_identifier_sequence_value(self):        
        data = b"someProperty = [qw, er, ty]"
        events = [
            PropertyNameEvent,
            IdentifierSequenceStartEvent,
            ValueEvent,
            ValueEvent,
            ValueEvent,
            IdentifierSequenceEndEvent]
        values = ["someProperty", None, "qw", "er", "ty", None]
        self.check_events_for_parsing_sequences(events, values, data)

    def test_parse_object_property_with_scalar_sequence_value(self):
        data = b"someProperty = (12\r\n13\r\n14)"
        events = [
            PropertyNameEvent,
            ScalarSequenceStartEvent,
            ValueEvent,
            ValueEvent,
            ValueEvent,
            ScalarSequenceEndEvent]
        values = ["someProperty", None, 12, 13, 14, None]
        self.check_events_for_parsing_sequences(events, values, data)

    def test_parse_property_with_binary_sequence_value(self):
        data = b"property = {\r\n3333333333337733333333333330033333333333333773333333333333003333}"
        fixture = [int(d, 16) for d in "3333333333337733333333333330033333333333333773333333333333003333"]
        p = Parser(data)
        p.state = p.parse_item
        for i in range(2):
            p.get_event()
        event = p.get_event()
        self.assertIsInstance(event, BinaryDataEvent)
        self.assertEqual(event.value, fixture)

    def test_parse_object_property_with_item_sequence_value(self):
        data = b"someProperty = <\r\nitem\r\nprop1 = 1\r\nend\r\nitem\r\nprop2 = foo\r\nend>"
        events = [
            PropertyNameEvent,
            ItemSequenceStartEvent,
            ItemEvent,
            PropertyNameEvent,
            ValueEvent,
            EndOfBlockEvent,
            ItemEvent,
            PropertyNameEvent,
            ValueEvent,
            EndOfBlockEvent,
            ItemSequenceEndEvent]
        values = ["someProperty", None, None, "prop1", 1, None, None, "prop2", "foo", None, None]
        self.check_events_for_parsing_sequences(events, values, data)

    def test_binary_sequence_not_closed(self):
        data = b"property = {\r\n3333333333337733333333333330033333333333333773333333333333003333\r\n  anotherProperty = 1"
        p = Parser(data)
        p.state = p.parse_item
        for i in range(3):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)

    def test_scalar_sequence_not_closed(self):
        data = b"property = (\r\n1\r\n2\r\nanotherProperty = [a,b,c]"
        p = Parser(data)
        p.state = p.parse_item
        for i in range(4):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)

    def test_identifier_sequence_not_closed(self):
        data = b"object foo: bar\r\n  property=[qw, er, ty\r\n  property2 = 2\r\nend"
        p = Parser(data)
        for i in range(8):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)

    def test_item_sequence_not_closed(self):
        # незакрытая последовательность item'ов вызывает ошибку
        # т.к. парсер напарывается на название свойства вместо
        # слова 'item' или закрывающей скобки
        data = b"raz = <\r\nitem\r\n  prop1 = 1\r\nend\r\ndva = 2"
        p = Parser(data)
        p.state = p.parse_object_content
        p.tokenizer.get_next_token()
        for i in range(6):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)

    def test_identifier_sequence_no_comma(self):
        data = b"property = [a b c]"
        p = Parser(data)
        p.state = p.parse_item
        for i in range(3):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)

    def test_comma_in_non_identifier_sequence(self):
        data = b"= (1,2,3)"
        p = Parser(data)
        p.state = p.parse_property_value
        for i in range(2):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)

    def test_parse_empty_itentifier_sequence(self):
        data = b"someProperty = []"
        events = [
            PropertyNameEvent,
            IdentifierSequenceStartEvent,
            IdentifierSequenceEndEvent]
        values = ["someProperty", None, None]
        self.check_events_for_parsing_sequences(events, values, data)

    def test_parse_empty_binary_sequence(self):
        data = b"someProperty = {}"
        events = [
            PropertyNameEvent,
            BinarySequenceStartEvent,
            BinarySequenceEndEvent]
        values = ["someProperty", None, None]
        self.check_events_for_parsing_sequences(events, values, data)

    def test_parse_empty_scalar_sequence(self):
        data = b"someProperty = ()"
        events = [
            PropertyNameEvent,
            ScalarSequenceStartEvent,
            ScalarSequenceEndEvent]
        values = ["someProperty", None, None]
        self.check_events_for_parsing_sequences(events, values, data)

    def test_parse_empty_item_sequence(self):
        data = b"someProperty = <>"
        events = [
            PropertyNameEvent,
            ItemSequenceStartEvent,
            ItemSequenceEndEvent]
        values = ["someProperty", None, None]
        self.check_events_for_parsing_sequences(events, values, data)

    def test_parse_item_property_with_string_value(self):
        data = b"itemProperty = here goes the value"
        events = [PropertyNameEvent, ValueEvent]
        values = ["itemProperty", "here goes the value"]
        self.check_events_for_parsing_items(events, values, data)

    def test_parse_item_property_with_numeric_value(self):
        data = b"itemProperty = 557"
        events = [PropertyNameEvent, ValueEvent]
        values = ["itemProperty", 557]
        self.check_events_for_parsing_items(events, values, data)

    def test_parse_object_content_with_nested_objects(self):
        data = b"object foo: bar\r\n  object spam: eggs\r\n  end\r\nend"
        self.check_event_sequence(
            [
                ObjectEvent,
                ObjectNameEvent,
                ObjectTypeEvent,
                ObjectEvent,
                ObjectNameEvent,
                ObjectTypeEvent,
                EndOfBlockEvent,
                EndOfBlockEvent,
                EndOfFileEvent],
            data)

    def test_parse_object_with_omitted_type_definition(self):
        data = b"object foo\r\n  prop1 = val1\r\nend"
        p = Parser(data)
        for i in range(2):
            p.get_event()
        evt = p.get_event()
        self.assertEqual(p.state, p.parse_object_content)
        self.assertEqual(evt.value, "")

    def test_parse_object_with_omitted_type_definition_and_nested_object(self):
        data = b"object foo\r\n  object obj: t1\r\n    prop1 = val1\r\n  end\r\nend"
        p = Parser(data)
        for i in range(2):
            p.get_event()
        evt = p.get_event()
        self.assertEqual(p.state, p.parse_object_content)
        self.assertEqual(evt.value, "")

    def test_parse_empty_object_with_omitted_type_definition(self):
        self.check_event_sequence(
            [
                ObjectEvent,
                ObjectNameEvent,
                ObjectTypeEvent,
                EndOfBlockEvent,
                EndOfFileEvent],
            b"object foo: bar\r\nend")

    def test_parse_object_with_no_end(self):
        data = b"object foo: bar\r\n  p = v\r\n"
        p = Parser(data)
        for i in range(5):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)

    def test_parse_property_with_quoted_string_value(self):
        data = b"object foo: bar\r\n  propertyName = 'quoted value'\r\nend"
        p = Parser(data)
        for i in range(4):
            p.get_event()
        evt = p.get_event()
        self.assertIsInstance(evt, ValueEvent)
        self.assertEqual(evt.value, "quoted value")

    def test_parse_item(self):
        data = b"item\r\n  prop1 = 1\r\n  prop2 = [qw,er,ty]\r\nend"
        p = Parser(data)
        p.state = p.parse_item_sequence
        event = p.get_event()
        self.assertIsInstance(event, ItemEvent)
        event = p.get_event()
        self.assertIsInstance(event, PropertyNameEvent)
        self.assertEqual(event.value, "prop1")
        event = p.get_event()
        self.assertIsInstance(event, ValueEvent)
        self.assertEqual(event.value, 1)
        for i in range(6):
            p.get_event()
        event = p.get_event()
        self.assertIsInstance(event, EndOfBlockEvent)

    def test_parse_item_with_no_end(self):
        data = b"item\r\n  prop1 = 1\r\n  prop2 = 2\r\nitem\r\n  prop3 = 3\r\n  prop4 = 4\r\nend"
        p = Parser(data)
        p.state = p.parse_item_sequence
        for i in range(5):
            p.get_event()
        self.assertRaises(ParserError, p.get_event)
