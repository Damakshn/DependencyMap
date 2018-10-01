from .reader import Reader
from .tokens import *
import re


class TokenizerError(Exception):
    pass


class Tokenizer:
    # регулярка для проверки идентификаторов
    # правильный идентификатор содержит английские и
    # русские буквы любого регистра, цифры, _ и не может начинаться с цифры
    identifier_pattern = re.compile(
        b"^[a-z\xd0\xb0-\xd1\x8f_]+[a-z\xd0\xb0-\xd1\x8f\d_]*", re.IGNORECASE)
    # регулярка для валидации чисел
    # первым знаком может быть минус
    # допускаются только цифры (и точка, если это дробь)
    # запрещены ведущие нули
    number_pattern = re.compile(b"^-?[1-9]\d*$|^-?[1-9]\d*\.\d+|^0$")
    # регулярка для проверки двоичных данных
    # 32 байта шестнадцатиричных чисел
    hexcode_pattern = re.compile(b"[\dA-F]{64}")

    def __init__(self, data):
        self.done = False
        self.current_token = None
        self.assignment = False
        self.reader = Reader(data)
        self.mark = None

    def has_tokens(self) -> bool:
        return not self.done

    def check_token(self, *choices) -> bool:
        if self.current_token:
            if not choices:
                return True
            for choice in choices:
                if (isinstance(self.current_token, choice)):
                    return True
        return False

    def peek_token(self) -> Token:
        if self.current_token:
            return self.current_token
        else:
            return None

    def get_next_token(self) -> Token:
        if self.has_tokens():
            self.fetch_next_token()
            if isinstance(self.current_token, AssignmentToken):
                self.assignment = True
            else:
                self.assignment = False
            self.reader.forward()
            return self.current_token

    def move_to_next_token(self) -> None:
        stop = False
        line = self.reader.line
        while not stop:
            if self.reader.peek() in b" \r\n":
                self.reader.forward()
            else:
                stop = True
        if (self.assignment and line != self.reader.line):
            raise TokenizerError("Missing property value after assignment")
        self.mark = self.reader.get_mark()

    def fetch_word(self) -> str:
        # доползти до первого символа, являющегося служебным
        # и вернуть всё от текущего символа до крайнего
        length = 1
        while not self.reader.peek(length) in b" :=\r\n+,;-[]()<>{}\0":
            length += 1
        return self.reader.get_chunk(length)

    def check_valid_number(self, word: bytes) -> bool:
        return self.number_pattern.match(word) is not None

    def check_valid_identifier(self, word: bytes) -> bool:
        return self.identifier_pattern.match(word) is not None

    def check_valid_hexcode(self, word: bytes) -> bool:
        return self.hexcode_pattern.match(word) is not None

    def fetch_next_token(self) -> None:
        self.move_to_next_token()
        ch = chr(self.reader.peek())
        # проверяем на служебные символы
        if ch == "=":
            return self.fetch_assignment()

        if ch == ":":
            return self.fetch_data_type()

        if ch == "'":
            return self.fetch_quoted_string()

        if ch == "<":
            return self.fetch_item_sequence_start()

        if ch == ">":
            return self.fetch_item_sequence_end()

        if ch == "[":
            return self.fetch_identifier_sequence_start()

        if ch == "]":
            return self.fetch_identifier_sequence_end()

        if ch == "(":
            return self.fetch_scalar_sequence_start()

        if ch == ")":
            return self.fetch_scalar_sequence_end()

        if ch == "{":
            return self.fetch_binary_sequence_start()

        if ch == "}":
            return self.fetch_binary_sequence_end()

        if ch == ",":
            return self.fetch_sequence_entry()

        if ch == "\0":
            return self.fetch_end_of_file()

        # если это не службный символ, читаем текст куском
        # если это не первый токен после "=", читаем слово до пробела
        if not self.assignment:
            word = self.fetch_word()
        else:
            # иначе читаем до конца строки
            word = self.reader.copy_to_end_of_line().strip()

        if word == b"object":
            return self.fetch_object_header()
        if word == b"item":
            return self.fetch_item()
        if word == b"end":
            return self.fetch_block_end()
        if self.check_valid_hexcode(word):
            return self.fetch_binary_data(word)
        if self.check_valid_number(word):
            return self.fetch_number(word)
        if self.check_valid_identifier(word):
            return self.fetch_identifier(word)

        return self.fetch_string(word)

    def fetch_object_header(self) -> None:
        self.current_token = ObjectToken(self.mark)
        self.reader.forward(6)

    def fetch_data_type(self) -> None:
        # текущий символ - :,
        # копируем всё от него до конца строки, обрезаем двоеточие и пробелы
        # убеждаемся, что остался правильный идентификатор
        # возвращаем токен с типом данных
        line = self.reader.copy_to_end_of_line()
        typedef = line[1:].strip()
        if self.check_valid_identifier(typedef):
            self.current_token = TypeDefinitionToken(self.mark, typedef)
            self.reader.forward(len(line))
        else:
            raise TokenizerError("Incorrect type definition")

    def fetch_string(self, word: bytes) -> None:
        self.current_token = StringToken(self.mark, word)
        self.reader.forward(len(word) - 1)

    def fetch_quoted_string(self) -> None:
        word = self.reader.copy_to_end_of_line().strip()
        last_quot_pos = word.rfind(b"'")
        s = word[1:last_quot_pos]
        self.current_token = QuotedStringToken(self.mark, s)
        self.reader.forward(last_quot_pos)

    def fetch_scalar_sequence_start(self) -> None:
        self.current_token = ScalarSequenceStartToken(self.mark)

    def fetch_scalar_sequence_end(self) -> None:
        self.current_token = ScalarSequenceEndToken(self.mark)

    def fetch_identifier_sequence_start(self) -> None:
        self.current_token = IdentifierSequenceStartToken(self.mark)

    def fetch_identifier_sequence_end(self) -> None:
        self.current_token = IdentifierSequenceEndToken(self.mark)

    def fetch_item_sequence_start(self) -> None:
        self.current_token = ItemSequenceStartToken(self.mark)

    def fetch_item_sequence_end(self) -> None:
        self.current_token = ItemSequenceEndToken(self.mark)

    def fetch_item(self) -> None:
        self.current_token = ItemToken(self.mark)
        self.reader.forward(3)

    def fetch_identifier(self, word: bytes) -> None:
        self.current_token = IdentifierToken(self.mark, word)
        self.reader.forward(len(word) - 1)

    def fetch_binary_sequence_start(self) -> None:
        self.current_token = BinarySequenceStartToken(self.mark)

    def fetch_binary_sequence_end(self) -> None:
        self.current_token = BinarySequenceEndToken(self.mark)

    def fetch_assignment(self) -> None:
        self.current_token = AssignmentToken(self.mark)

    def fetch_block_end(self) -> None:
        self.current_token = EndOfBlockToken(self.mark)
        self.reader.forward(2)

    def fetch_sequence_entry(self) -> None:
        self.current_token = CommaToken(self.mark)

    def fetch_number(self, word: bytes) -> None:
        self.current_token = NumberToken(self.mark, word)
        self.reader.forward(len(word) - 1)

    def fetch_binary_data(self, word: bytes) -> None:
        # костыль для тестирования боевых компонентов
        # self.current_token = BinaryDataToken(self.mark, word)
        self.current_token = BinaryDataToken(self.mark, [int(d, 16) for d in word.decode("utf-8")])
        self.reader.forward(len(word) - 1)

    def fetch_end_of_file(self) -> None:
        self.current_token = EndOfFileToken(self.mark)
        self.done = True
