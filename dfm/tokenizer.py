"""
Перемещается между токенами
Распознаёт все токены по отдельности
Кидает ошибки для кривых токенов
"""


class TokenizerError(Exception):
    pass

class Tokenizer(object):

    __init__(self):
        self.done = False
        self.tokens = []
        self.current_token = None

    def check_token(self, choices*) -> boolean:
        pass

    def peek_token(self) -> Token:
        pass

    def get_next_token(self) -> Token:
        pass

    def move_to_next_token(self) -> None:
        while self.peek() in b" \r\n\0":
            self.forward()

    def fetch_word(self) -> str:
        # доползти до первого символа, не являющегося ' :=\n+,;-' и вернуть всё от текущего символа до крайнего
        length = 1
        while self.peek(length) in b" :=\r\n+,;-[]()<>{}\0":
            length+=1            
        return self.get_chunk(length)

    def check_valid_identifier(self, word: str) -> Boolean:
        return True

    def fetch_next_token(self) -> None:
        move_to_next_token()
        ch = self.peek()
        # проверяем на служебные символы
        if ch == ":" and not self.in_quotes:
            return self.fetch_data_type()

        if ch == "=" and not self.in_quotes:
            if self.in_item:
                return self.fetch_item_property_value()
            else:
                return self.fetch_object_property_value()

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
            return self.fetch_value_sequence_start()

        if ch == ")" and not self.in_quotes:
            return self.fetch_value_sequence_end()

        if ch == "{" and not self.in_quotes:
            return self.fetch_binary_sequence_start()

        if ch == "}" and not self.in_quotes:
            return self.fetch_binary_sequence_end()

        # если это не службный символ, читаем слово
        word = self.fetch_word()
        if word == "object":
            return self.fetch_object_header()

        if word == "item":
            return self.fetch_item()

        if word == "end" and (self.in_item or self.in_object):
            return self.fetch_block_end()

        if self.check_valid_identifier(word):
            return self.fetch_identifier(word)

        raise TokenizerError("Unknown token")

    def fetch_object_header(self) -> None:
        self.tokens.append(ObjectToken())

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

    def fetch_scalar(self) -> None:
        pass

    def fetch_scalar_sequence(self) -> None:
        pass

    def fetch_identifier_sequence(self) -> None:
        pass

    def fetch_binary_sequence(self) -> None:
        pass

    def fetch_item_sequence(self) -> None:
        pass

    def fetch_item(self) -> None:
        pass

    def fetch_identifier(self, word) -> None:
        self.forward(len(word))
        self.tokens.append(IdentifierToken(word))
