from .tokens import *
import re
class TokenizerError(Exception):
    pass

class Tokenizer(object):
    # регулярка для проверки идентификаторов
    # правильный идентификатор содержит английские и русские буквы любого регистра, цифры, _
    # и не может начинаться с цифры
    identifier_pattern = re.compile(b"^[a-z\xd0\xb0-\xd1\x8f_]+[a-z\xd0\xb0-\xd1\x8f\d_]*", re.IGNORECASE)
    # регулярка для валидации чисел
    # первым знаком может быть минус
    # допускаются только цифры (и точка, если это дробь)
    # запрещены ведущие нули
    number_pattern = re.compile(b"^-?[1-9]\d*$|^-?[1-9]\d*\.\d+|^0$")

    def __init__(self):
        self.done = False        
        self.current_token = None
        self.in_quotes = False

    def has_tokens(self):
        return not self.done

    def check_token(self, *choices) -> bool:
        pass

    def peek_token(self) -> Token:
        pass

    def get_next_token(self) -> Token:
        if self.has_tokens():
            self.fetch_next_token()            
            self.forward()
            return self.current_token

    def move_to_next_token(self) -> None:
        stop = False
        while not stop:            
            if self.peek() in b" \r\n":
                self.forward()
            else:
                stop = True        

    def fetch_word(self) -> str:
        # доползти до первого символа, являющегося служебным и вернуть всё от текущего символа до крайнего
        length = 1
        while not self.peek(length) in b" :=\r\n+,;-[]()<>{}\0":
            length+=1
        #self.forward()
        return self.get_chunk(length)

    def check_valid_number(self, word: bytes) -> bool:        
        return self.number_pattern.match(word) is not None

    def check_valid_identifier(self, word: bytes) -> bool:
        return self.identifier_pattern.match(word) is not None

    def fetch_next_token(self) -> None:
        self.move_to_next_token()
        ch = chr(self.peek())
        # проверяем на служебные символы
        if ch == ":" and not self.in_quotes:
            return self.fetch_data_type()

        if ch == "=" and not self.in_quotes:
            return self.fetch_assignment()

        if ch == "'" and not self.in_quotes:
            return self.fetch_quoted_string()

        if ch == "<" and not self.in_quotes:
            return self.fetch_item_sequence_start()

        if ch == ">" and not self.in_quotes:
            return self.fetch_item_sequence_end()

        if ch == "[" and not self.in_quotes:
            return self.fetch_identifier_sequence_start()

        if ch == "]" and not self.in_quotes:
            return self.fetch_identifier_sequence_end()

        if ch == "(" and not self.in_quotes:
            return self.fetch_scalar_sequence_start()

        if ch == ")" and not self.in_quotes:
            return self.fetch_scalar_sequence_end()

        if ch == "{" and not self.in_quotes:
            return self.fetch_binary_sequence_start()

        if ch == "}" and not self.in_quotes:
            return self.fetch_binary_sequence_end()

        if ch == "," and not self.in_quotes:
            return self.fetch_sequence_entry()

        if ch == "\0":
            return self.fetch_end_of_file()

        # если это не службный символ, читаем слово
        word = self.fetch_word()
        if word == b"object":
            return self.fetch_object_header()

        if word == b"item":
            return self.fetch_item()

        if word == b"end":
            return self.fetch_block_end()

        if self.check_valid_number(word):
            return self.fetch_number(word)

        if self.check_valid_identifier(word):
            return self.fetch_identifier(word)

        return self.fetch_string(word)

    def fetch_object_header(self) -> None:
        self.current_token = ObjectToken()
        self.forward(6)

    def fetch_data_type(self) -> None:
        # текущий символ - :, 
        # копируем всё от него до конца строки, обрезаем двоеточие в начале и пробелы
        # убеждаемся, что остался правильный идентификатор
        # возвращаем токен с типом данных
        line = self.copy_to_end_of_line()
        typedef = line[1:].strip()        
        if self.check_valid_identifier(typedef):
            self.current_token = TypeDefinitionToken(typedef)
            self.forward(len(line))
        else:
            raise TokenizerError("Incorrect type definition")

    def fetch_property_name(self) -> None:
        pass

    def fetch_object_property_value(self) -> None:
        pass

    def fetch_item_property_value(self) -> None:
        pass

    def fetch_string(self, word: bytes) -> None:
        self.forward(len(word)-1)
        self.current_token = StringToken(word)

    def fetch_scalar_sequence_start(self) -> None:
        self.current_token = ScalarSequenceStartToken()

    def fetch_scalar_sequence_end(self) -> None:
        self.current_token = ScalarSequenceEndToken()

    def fetch_identifier_sequence_start(self) -> None:
        self.current_token = IdentifierSequenceStartToken()

    def fetch_identifier_sequence_end(self) -> None:
        self.current_token = IdentifierSequenceEndToken()

    def fetch_item_sequence_start(self) -> None:
        self.current_token = ItemSequenceStartToken()

    def fetch_item_sequence_end(self) -> None:
        self.current_token = ItemSequenceEndToken()

    def fetch_item(self) -> None:
        self.current_token = ItemToken()
        self.forward(3)

    def fetch_identifier(self, word: bytes) -> None:
        self.forward(len(word)-1)
        self.current_token = IdentifierToken(word)

    def fetch_binary_sequence_start(self) -> None:
        self.current_token = BinarySequenceStartToken()

    def fetch_binary_sequence_end(self) -> None:
        self.current_token = BinarySequenceEndToken()

    def fetch_assignment(self) -> None:
        self.current_token = AssignmentToken()

    def fetch_block_end(self) -> None:
        self.current_token = BlockEndToken()
        self.forward(2)

    def fetch_sequence_entry(self) -> None:
        self.current_token = SequenceEntryToken()

    def fetch_number(self, word: bytes) -> None:
        self.current_token = NumberToken(word)
        self.forward(len(word))

    def fetch_end_of_file(self):
        self.current_token = EndOfFileToken()
        self.done = True