import unittest
from dfm.tokenizer import Tokenizer, TokenizerError


class TestTokenizer(unittest.TestCase):

    def check_sequence(self, fixture, sequence):
        """
        Извлекает все токены из sequence, а затем сверяет их с fixture.
        """
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

    def test_detect_boolean_token(self):
        data = b"False"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "BOOLEAN")
        self.assertEqual(token.value, False)

    def test_detect_quoted_string_token(self):
        data = b"'here goes quoted string'"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "here goes quoted string")

    def test_detect_string_with_russian_letters(self):
        data = b"#1040 #1089#1084#1099#1089#1083'?'"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "А смысл?")

    def test_detect_splitted_string_with_russian_letters(self):
        data = b"#1063#1077#1084 #1073#1086#1083#1100#1096#1077 #1089#1080#1083#1072, #1090 +\r\n\
    #1077#1084 #1073#1086#1083#1100#1096#1077 #1086#1090#1074#1077#1090#1089#1090#1074#1077#1085#1085#1086#1089#1090#1100'.'"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "Чем больше сила, тем больше ответственность.")

    def test_decode_mixed_russian_letters(self):
        data = b"'Abibas - '#1101#1090#1086' '#1089#1080#1083#1072'!'"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "Abibas - это сила!")

    def test_decode_russian_letters_with_temp_tables(self):
        data = b"'select * from #person, ##student --'#1082#1086#1084#1084#1077#1085#1090#1072#1088#1080#1081"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "select * from #person, ##student --комментарий")

    def test_decode_many_sharps(self):
        data = b"####1101'###'"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "###э###")

    def test_decode_string_with_leading_tabs(self):
        data = b"#9#9'from student where id = 1234'"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "\t\tfrom student where id = 1234")

    def test_detect_single_string_tailed_with_quote(self):
        data = b"#1101#1101#1101'...')"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "эээ...")
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

    def test_detect_single_string_tailed_with_rus_letter(self):
        data = b"#1101#1101#1101)"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "эээ")
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

    def test_detect_joined_strings_first_with_quote(self):
        data = b"'aaaa' + \r\n'bbbb')"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "aaaabbbb")
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

    def test_detect_joined_strings_first_with_rus_letter(self):
        data = b"#1074#1086#1076#1086 + \r\n#1087#1072#1076)"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "водопад")
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

    def test_detect_joined_strings_followed_with_single_string_rus(self):
        data = b"#1074#1086#1076#1086 + \r\n#1087#1072#1076\r\n#1090#1072#1088#1077#1083#1082#1072)"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "водопад")
        token = t.get_next_token()
        self.assertEqual(token.value, "тарелка")
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

    def test_detect_joined_strings_followed_with_single_string_quote(self):
        data = b"'string one'+\r\n' continues here'\r\n#1082#1086#1085#1077#1094)"
        t = Tokenizer(data)
        token = t.get_next_token()
        self.assertEqual(token.value, "string one continues here")
        token = t.get_next_token()
        self.assertEqual(token.value, "конец")
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

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

    def test_detect_binary_sequenct(self):
        fixture = [int(d, 16) for d in "BD00BDBDBD00BDBDBD00D68C6B00FFDED600FFFFFF00FFFFFF00FFF7EF00FFFF"]
        self.check_sequence(["{", fixture, "}", "END_FILE"],
            b"{\r\nBD00BDBDBD00BDBDBD00D68C6B00FFDED600FFFFFF00FFFFFF00FFF7EF00FFFF}")

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
