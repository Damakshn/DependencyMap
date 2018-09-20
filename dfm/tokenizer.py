from .tokens import *
import re
class TokenizerError(Exception):
    pass

class Tokenizer(object):
    identifier_pattern = re.compile(b"^[a-z\xd0\xb0-\xd1\x8f]+[a-z\xd0\xb0-\xd1\x8f\d_]*")    

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
        # первым знаком может быть минус
        # допускаются только цифры
        # запрещены ведущие нули
        if word[0] == ord("-"):
            word = word[1:]
        if word[0] == ord("0"):
            return False
        for ch in word:
            if not  chr(ch) in "0123456789":
                return False
        return True

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

        if word == b"end" and self.peek(3) in b" \r\n\0":
            return self.fetch_block_end()
            # and (self.in_item or self.in_object)

        if self.check_valid_number(word):
            return self.fetch_number(word)

        if self.check_valid_identifier(word):
            return self.fetch_identifier(word)

        return self.fetch_string(word)

    def fetch_object_header(self) -> None:
        self.current_token = ObjectToken()

    def fetch_data_type(self) -> None:
        # текущий символ - :, ползём от него до пробела или конца строки
        # читаем слово, убеждаемся, что это идентификатор
        # возвращаем токен с типом данных        
        pass

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

    def fetch_sequence_entry(self) -> None:
        self.current_token = SequenceEntryToken()

    def fetch_number(self, word: bytes) -> None:
        self.forward(len(word)-1)
        self.current_token = NumberToken(word)

    def fetch_end_of_file(self):
        self.current_token = EndOfFileToken()
        self.done = True