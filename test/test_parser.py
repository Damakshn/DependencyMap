"""
Тесты должны проверять обработку различных типовых конструкций формата,
а также выдавать правильные сообщения об ошибках в тех случаях, когда представлены некорректные данные.
"""
import unittest
from dfm.parser import Parser
from dfm.events import *

class TestParser(unittest.TestCase):

    def test_init(self):
        self.fail("not implemented yet")
    
    def test_parse_object_property_with_string_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_with_numeric_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_with_no_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_with_identifier_sequence_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_with_scalar_sequence_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_with_binary_sequence_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_with_item_sequence_value(self):
        self.fail("not implemented yet")

    def test_parse_object_property_no_assign(self):
        self.fail("not implemented yet")

    def test_binary_sequence_not_closed(self):
        self.fail("not implemented yet")

    def test_scalar_sequence_not_closed(self):
        self.fail("not implemented yet")

    def test_identifier_sequence_not_closed(self):
        self.fail("not implemented yet")

    def test_item_sequence_not_closed(self):
        self.fail("not implemented yet")

    def test_sequence_with_open_bracket(self):
        self.fail("not implemented yet")

    def test_identifier_sequence_no_comma(self):
        self.fail("not implemented yet")

    def test_comma_in_non_identifier_sequence(self):
        self.fail("not implemented yet")

    def test_parse_empty_itentifier_sequence(self):
        self.fail("not implemented yet")

    def test_parse_empty_binary_sequence(self):
        self.fail("not implemented yet")

    def test_parse_empty_scalar_sequence(self):
        self.fail("not implemented yet")

    def test_parse_empty_item_sequence(self):
        self.fail("not implemented yet")

    def test_parse_item_property_with_string_value(self):
        self.fail("not implemented yet")

    def test_parse_item_property_with_numeric_value(self):
        self.fail("not implemented yet")

    def test_parse_item_property_with_sequence_value(self):
        self.fail("not implemented yet")

    def test_parse_item_property_with_no_value(self):
        self.fail("not implemented yet")

    def test_parse_item_property_no_assign(self):
        self.fail("not implemented yet")

    def test_parse_object(self):
        self.fail("not implemented yet")

    def test_parse_object_name(self):
        self.fail("not implemented yet")

    def test_parse_object_type_definition(self):
        self.fail("not implemented yet")

    def test_parse_full_object_declaration(self):
        self.fail("not implemented yet")

    def test_parse_object_content_with_simple_properties(self):
        self.fail("not implemented yet")

    def test_parse_object_content_with_sequence_properties(self):
        self.fail("not implemented yet")

    def test_parse_object_content_with_nested_objects(self):
        self.fail("not implemented yet")

    def test_parse_object_content_complete(self):
        self.fail("not implemented yet")

    def test_parse_empty_object(self):
        self.fail("not implemented yet")

    def test_parse_object_with_omitted_type_definition(self):
        self.fail("not implemented yet")

    def test_parse_empty_object_wit_omitted_type_definition(self):
        self.fail("not implemented yet")

    def test_parse_object_with_no_end(self):
        self.fail("not implemented yet")

    def test_parse_file(self):
        self.fail("not implemented yet")

    def test_parse_empty_file(self):
        self.fail("not implemented yet")

    def test_parse_item(self):
        self.fail("not implemented yet")

    def test_parse_item_with_no_end(self):
        self.fail("not implemented yet")

    def test_state_transition(self):
        self.fail("not implemented yet")