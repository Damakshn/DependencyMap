import unittest
from dfm.tokenizer import Tokenizer, TokenizerError


class TestTokenizer(unittest.TestCase):

    def check_sequence(self, fixture, sequence):
        t = Tokenizer(sequence)
        tokens = []
        while t.has_tokens():
            token = t.get_next_token()
            if token.value == "":
                tokens.append(str(token))
            else:
                tokens.append(token.value)
        self.assertEqual(fixture, tokens)

    def test_fetch_word(self):
        data = b" wordToFetch123<"
        t = Tokenizer(data)
        t.move_to_next_token()
        word = t.fetch_word()
        self.assertEqual(word, b"wordToFetch123")

# Тестируем распознавание отдельных токенов
# (используем корректные данные)
    def test_detect_object_token(self):
        data = b"\n  object someObject: objClass"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "OBJECT")

    def test_detect_type_definition_token(self):
        data = b" : integer\n"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "TYPEDEF")
        self.assertEqual(token.value, "integer")

    def test_detect_identifier_token(self):
        data = b" someObject: objClass"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "IDENTIFIER")
        self.assertEqual(token.value, "someObject")

    def test_detect_number_token(self):
        data = b" -123.8"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "NUMBER")
        self.assertEqual(token.value, -123.8)

    def test_detect_string_token(self):
        data = b"@1SomeThing"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "STRING")
        self.assertEqual(token.value, "@1SomeThing")

    def test_detect_assignment_token(self):
        data = b" = value"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "=")

    def test_detect_item_token(self):
        data = b"  item\n"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "ITEM")

    def test_detect_scalar_sequence_start_token(self):
        data = b" ("
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "(")

    def test_detect_scalar_sequence_end_token(self):
        data = b" )"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

    def test_detect_identifier_sequence_start_token(self):
        data = b" ["
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "[")

    def test_detect_identifier_sequence_end_token(self):
        data = b" ]"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "]")

    def test_detect_item_sequence_start_token(self):
        data = b" <"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "<")

    def test_detect_item_sequence_end_token(self):
        data = b" >"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, ">")

    def test_detect_binary_sequence_start_token(self):
        data = b" {"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "{")

    def test_detect_binary_sequence_end_token(self):
        data = b" }"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "}")

    def test_detect_block_end_token(self):
        data = b"\n  end"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "END_BLOCK")

    def test_detect_sequence_entry_token(self):
        data = b",value"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, ",")

    def test_detect_end_of_file_token(self):
        data = b""
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertTrue(t.reader.eof)
        self.assertTrue(t.done)
        self.assertEqual(token.id, "END_FILE")

    # тестирование распознавания последовательностей токенов
    def test_detect_identifier_sequence_full(self):
        self.check_sequence(
            ["[", "qw", ",", "er", ",", "ty1", "]", "END_FILE"],
            b"[qw,er, ty1]")

    def test_detect_full_object_header(self):
        self.check_sequence(
            ["OBJECT", "Form1", "TForm1", "END_FILE"],
            b"object Form1: TForm1")

    def test_detect_full_item(self):
        self.check_sequence(
            ["ITEM", "prop1", "=", "value1", "prop2", "=", 2, "END_BLOCK", "END_FILE"],
            b"item\r\n  prop1 = value1\r\n  prop2 = 2\r\nend")

    def test_detect_simple_property(self):
        self.check_sequence(
            ["propertyName", "=", "propertyValue", "END_FILE"],
            b"propertyName = propertyValue")

    def test_detect_full_scalar_sequence(self):
        self.check_sequence(
            ["(", 1, 2, 3, ")", "END_FILE"],
            b"(\r\n1\r\n2\r\n3)")

    def test_detect_empty_scalar_sequence(self):
        self.check_sequence(
            ["property", "=", "(", ")", "END_FILE"],
            b"property = ()")

    def test_detect_empty_identifier_sequence(self):
        self.check_sequence(
            ["property", "=", "[", "]", "END_FILE"],
            b"property = []")

    def test_detect_empty_binary_sequence(self):
        self.check_sequence(
            ["property", "=", "{", "}", "END_FILE"],
            b"property = {}")

    def test_detect_empty_item_sequence(self):
        self.check_sequence(
            ["property", "=", "<", ">", "END_FILE"],
            b"property = <>")

    def test_detect_full_item_sequence(self):
        """
        itemSeq = <
        item
          prop1 = value1
          prop2 = 2
        end
        item
          prop3 = 182
        end>
        """
        self.check_sequence(
            ["itemSeq", "=", "<", "ITEM", "prop1", "=", "value1", "prop2", "=", 2, "END_BLOCK", "ITEM", "prop3", "=", 182, "END_BLOCK", ">", "END_FILE"],
            b"itemSeq = <\r\nitem\r\n  prop1 = value1\r\n  prop2 = 2\r\nend\r\nitem\r\n  prop3 = 182\r\nend>")

    def test_detect_string_with_spaces(self):
        self.check_sequence(
            ["property", "=", "aaa bbb ccc", "END_FILE"],
            b"property = aaa bbb ccc")

    def test_detect_missing_property_value(self):
        data = b"property1 =    \r\n  property2 = 123"
        t = Tokenizer(data)
        for i in range(2):
            t.get_next_token()
        self.assertRaises(TokenizerError, t.get_next_token)
