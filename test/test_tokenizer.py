"""
Что тестируем
* Перемещение к следующему токену
* Извлечение слова
Распознавание токенов всех типов (пока без многострочек, русских букв и бинарников)
* Распознавание последовательностей токенов
* [qwe,wer,ert]
* property = value
* property = [] () <> {}
* property = 123
* item p = v ... end
* object name: type
* Ошибка при попытке обработать кривой токен (без учета контекста, это уже задача парсера)
"""
import unittest
from dfm.tokenizer import Tokenizer, TokenizerError
from dfm.tokens import *
from dfm.reader import Reader, ReaderError

# Новый класс объединяет функции Reader и Tokenizer
class Worker(Reader, Tokenizer):
    
    def __init__(self, data):
        Reader.__init__(self, data)
        Tokenizer.__init__(self)

class TestTokenizer(unittest.TestCase):

# Тестируем распознавание отдельных токенов
# (используем корректные данные)
    def test_detect_object_token(self):
        data = b"\n  object someObject: objClass"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "OBJECT")
    
    @unittest.skip("Not implemented yet")
    def test_detect_type_definition_token(self):
        data = b" : integer\n"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "TYPEDEF")
        self.assertEqual(token.value, b"integer")        

    def test_detect_identifier_token(self):
        data = b" someObject: objClass"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "IDENTIFIER")
        self.assertEqual(token.value, "someObject")

    def test_detect_number_token(self):
        data = b" -123"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "NUMBER")
        self.assertEqual(token.value, b"-123")

    def test_detect_string_token(self):
        data = b"@1SomeThing"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "STRING")
        self.assertEqual(token.value, "@1SomeThing")

    def test_detect_assignment_token(self):
        data = b" = value"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "=")

    def test_detect_item_token(self):
        data = b"  item\n"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "ITEM")

    def test_detect_scalar_sequence_start_token(self):
        data = b" ("
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "(")

    def test_detect_scalar_sequence_end_token(self):
        data = b" )"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, ")")

    def test_detect_identifier_sequence_start_token(self):
        data = b" ["
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "[")

    def test_detect_identifier_sequence_end_token(self):
        data = b" ]"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "]")

    def test_detect_item_sequence_start_token(self):
        data = b" <"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "<")

    def test_detect_item_sequence_end_token(self):
        data = b" >"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, ">")

    def test_detect_binary_sequence_start_token(self):
        data = b" {"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "{")

    def test_detect_binary_sequence_end_token(self):
        data = b" }"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "}")

    def test_detect_block_end_token(self):
        data = b"\n  end"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "END_BLOCK")

    def test_detect_sequence_entry_token(self):
        data = b",value"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, ",")

    def test_detect_end_of_file_token(self):
        data = b""
        t = Worker(data)
        token = t.get_next_token()
        self.assertTrue(t.eof)
        self.assertTrue(t.done)
        self.assertEqual(token.id, "END_FILE")

    def test_detect_identifier_sequence_full(self):
        fixture = ["[","qw", ",", "er", ",", "ty1", "]", "END_FILE"]
        data = b"[qw,er, ty1]"
        t = Worker(data)
        tokens = []
        while t.has_tokens():
            token = t.get_next_token()
            tokens.append(str(token))
        self.assertEqual(fixture, tokens)

    def test_detect_full_object_header(self):
        self.fail("Not implemented yet")

    def test_detect_full_item(self):
        self.fail("Not implemented yet")

    def test_detect_simple_property(self):
        self.fail("Not implemented yet")

    def test_detect_full_scalar_sequence(self):
        self.fail("Not implemented yet")

    def test_detect_full_item_sequence(self):
        self.fail("Not implemented yet")
