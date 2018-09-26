"""
Тесты должны проверять обработку различных типовых конструкций формата,
а также выдавать правильные сообщения об ошибках в тех случаях, когда представлены некорректные данные.
"""
import unittest
from dfm.parser import Parser
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

    @unittest.skip("moved to test_tokenizer")
    def test_parse_object_property_with_no_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_with_identifier_sequence_value(self):        
        data = b"someProperty = [qw, er, ty]"
        events = [
            PropertyNameEvent,
            IdentifierSequenceStartEvent,
            ValueEvent,
            SequenceEntryEvent,
            ValueEvent,
            SequenceEntryEvent,
            ValueEvent,
            IdentifierSequenceEndEvent]
        values = ["someProperty", None, "qw", None, "er", None, "ty", None]
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

    @unittest.skip("not implemented yet")
    def test_parse_object_property_with_binary_sequence_value(self):
        self.fail("not implemented yet")

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

    @unittest.skip("moved to test_tokenizer")
    def test_parse_object_property_no_assign(self):
        pass

    @unittest.skip("not implemented yet")
    def test_binary_sequence_not_closed(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_scalar_sequence_not_closed(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_identifier_sequence_not_closed(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_item_sequence_not_closed(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_sequence_with_open_bracket(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_identifier_sequence_no_comma(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_comma_in_non_identifier_sequence(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_empty_itentifier_sequence(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_empty_binary_sequence(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_empty_scalar_sequence(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_empty_item_sequence(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_item_property_with_string_value(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_item_property_with_numeric_value(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_item_property_with_sequence_value(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_item_property_with_no_value(self):
        self.fail("not implemented yet")

    @unittest.skip("moved to test_tokenizer")
    def test_parse_item_property_no_assign(self):
        pass

    @unittest.skip("not implemented yet")
    def test_parse_object_content_with_simple_properties(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_object_content_with_sequence_properties(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_object_content_with_nested_objects(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_object_content_complete(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_empty_object(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_object_with_omitted_type_definition(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_empty_object_wit_omitted_type_definition(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_object_with_no_end(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_item(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_parse_item_with_no_end(self):
        self.fail("not implemented yet")

    @unittest.skip("not implemented yet")
    def test_state_transition(self):
        self.fail("not implemented yet")
