"""
Что тестируем
Перемещение от токена к токену
Распознавание токенов всех типов (пока без многострочек, русских букв и бинарников)
    Объект, заголовок, тип, свойство, простое значение, последовательности ((), [], <>), конец
Извлечение токенов
Ошибка при попытке обработать кривой токен (без учета контекста, это задача парсера)
Перебор всего документа от начала до конца без ошибок
"""
import unittest
from dfm.tokenizer import Tokenizer, TokenizerError
from dfm.tokens import *
from dfm.reader import Reader, ReaderError

#small_test_file = open("small_component.dfm", "rb")

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
    
    def test_detect_type_definition_token(self):
        data = b" : integer\n"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "TYPEDEF")
        self.assertEqual(token.value, "integer")

    def test_detect_identifier_token(self):
        data = b" someObject: objClass"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "IDENTIFIER")
        self.assertEqual(token.value, b"someObject")

    def test_detect_scalar_token(self):
        data = b" -123"
        t = Worker(data)
        token = t.get_next_token()
        self.assertEqual(token.id, "SCALAR")
        self.assertEqual(token.value, "-123")

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

    # Тестируем чтение документа
    @unittest.skip("wait")
    def test_scan_document(self):
        # должно получиться 69 токенов
        data = small_test_file.read()
        t = Worker(data)
        tokens = []        
        while t.has_tokens():
            token = t.get_next_token()
            tokens.append(token)
        self.assertTrue(len(tokens) == 69)
