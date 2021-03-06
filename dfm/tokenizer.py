from .reader import Reader
from .tokens import *
import re


class TokenizerError(Exception):
    pass


class Tokenizer:
    """
    Распознаёт токены из файла.
    Использует класс Reader, чтобы двигаться по файлу вперёд, читать отдельные символы
    и куски текста.
    """
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
    hexcode_pattern = re.compile(b"[\dA-F]")
    # регулярка для логических значений
    boolean_pattern = re.compile(b"true|false", re.IGNORECASE)
    # регулярка для поиска последней закодированной русской буквы
    rus_end_of_line_pattern = re.compile(b".*(#[0-9]+)[^0-9]*$")
    # регулярка для проверки наличия закодированных русских букв
    has_rus_letters_pattern = re.compile(b".*#\d+")
    # регулярка для вытаскивания закодированных русских букв из строки
    rus_letter_pattern = re.compile("#\d+")

    def __init__(self, data):
        self.done = False
        self.current_token = None
        self.assignment = False
        self.reader = Reader(data)
        self.mark = None
        self.reading_binary_data = False
        # буфер для склеивания строк, записанных через '+'
        self.concat_strings_buffer = []
        # флаг для склейки токена из нескольких строк
        self.in_concat_mode = False

    def has_tokens(self) -> bool:
        """
        Возвращает True, если не достигнут конец файла.
        """
        return not self.done

    def check_token(self, *choices) -> bool:
        """
        Проверяет, соответствует ли токен одному из предложенных классов.
        """
        if self.current_token:
            if not choices:
                return True
            for choice in choices:
                if (isinstance(self.current_token, choice)):
                    return True
        return False

    def peek_token(self) -> Token:
        """
        Возвращает текущий токен.
        """
        if self.current_token:
            return self.current_token
        else:
            return None

    def get_next_token(self) -> Token:
        """
        Получает следующий токен и возвращает его.
        """
        if self.has_tokens():
            self.fetch_next_token()
            if isinstance(self.current_token, AssignmentToken):
                self.assignment = True
            else:
                self.assignment = False
            self.reader.forward()
            return self.current_token

    def move_to_next_token(self) -> None:
        """
        Посимвольно движется вперёд по файлу, пока не встретит непробельный символ,
        то есть новый токен. Считает строки и отмечает местоположение токена с помощью
        атрибута self.mark.
        """
        stop = False
        line = self.reader.line
        while not stop:
            if self.reader.peek() in b" \r\n":
                self.reader.forward()
            else:
                stop = True
        # если идёт сборка токена из нескольких строк, то метка не меняется,
        # пока сборка не будет завершена
        if not self.in_concat_mode:
            self.mark = self.reader.get_mark()

    def fetch_word(self) -> str:
        """
        Доходит до первого символа, являющегося служебным и
        возвращает всё от текущего символа до того, на котором остановился.
        """
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

    def check_is_boolean(self, word: bytes) -> bool:
        return self.boolean_pattern.match(word) is not None

    def check_encoded_russian_letters(self, word: bytes) -> bool:
        return self.has_rus_letters_pattern.match(word) is not None

    def fetch_next_token(self) -> None:
        """
        Смотрит, с какого символа начинается токен, пытается его распознать и
        вызывает соответствующий метод, чтобы прочитать токен целиком.
        Не возвращает значение, новый токен будет в итоге записан в self.current_token.
        Если токен распознать не удаётся, упаковывает его в строку.
        """
        self.move_to_next_token()
        ch = chr(self.reader.peek())
        # проверяем на служебные символы
        if ch == "=":
            return self.fetch_assignment()

        if ch == ":":
            return self.fetch_data_type()

        if ch == "'" or ch == "#":
            return self.fetch_line()

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
        if self.check_valid_hexcode(word) and self.reading_binary_data:
            return self.fetch_binary_data(word)
        if self.check_valid_number(word):
            return self.fetch_number(word)
        if self.check_is_boolean(word):
            return self.fetch_boolean(word)
        if self.check_valid_identifier(word):
            return self.fetch_identifier(word)

        return self.fetch_string(word)

    def fetch_object_header(self) -> None:
        self.current_token = ObjectToken(self.mark)
        self.reader.forward(6)

    def fetch_data_type(self) -> None:
        # текущий символ - ':',
        # копируем всё от него до конца строки, обрезаем двоеточие и пробелы
        # убеждаемся, что остался правильный идентификатор
        # возвращаем токен с типом данных
        line = self.reader.copy_to_end_of_line()
        typedef = line[1:].strip()
        if self.check_valid_identifier(typedef):
            self.current_token = TypeDefinitionToken(self.mark, typedef.decode("utf-8"))
            self.reader.forward(len(line))
        else:
            raise TokenizerError("Incorrect type definition")

    def fetch_string(self, word: bytes) -> None:
        self.current_token = StringToken(self.mark, word.decode("utf-8"))
        self.reader.forward(len(word) - 1)
    
    def decode_russian_letters_regex(self, text: bytes) -> str:
        """
        Декодирует строку с русскими буквами с помощью регулярного выражения.
        """
        res = []
        sample = text.decode("utf-8")
        mark = 0
        last_match = None
        # обрабатываем результат работы регулярки, все закодированные буквы преобразуем
        # если между двумя найденными буквами есть разрыв, то копируем весь текст между ними.
        # из вставляемого без обработки текста удаляем кавычки
        for match in self.rus_letter_pattern.finditer(sample):
            if match.start() != mark:
                res.append(sample[mark:match.start()].replace("'", ""))
            res.append(chr(int(match.group()[1:])))
            mark = match.end()
            last_match = match
        # если в строке остался необработанный хвост
        if last_match.end() < len(sample):
            res.append(sample[last_match.end():len(sample)].replace("'", ""))
        return "".join(res)

    def fetch_line(self) -> None:
        """
        Достаёт строку из многострочного текста.
        Такие строки могут быть разрезаны в произвольном месте и соединены знаком '+'.
        Русские буквы и некоторые другие символы закодированы в виде #код_символа_в_utf-8.
        При обнаружении '+' в конце строки токенайзер переводится в режим сборки токена из
        нескольких строк.
        """
        word = self.reader.copy_to_end_of_line().strip()
        draft = word
        self.in_concat_mode = word.endswith(b"+")
        match = self.rus_end_of_line_pattern.match(draft)
        if match is not None:
            last_rus_letter = match.end(1)
        else:
            last_rus_letter = -1
        plus = draft.rfind(b"+")
        quote = draft.rfind(b"'")
        # позиция последнего читаемого символа
        end_of_line = max((last_rus_letter, plus, quote))
        # расстояние, на которое надо переместить указатель
        distance = max(plus + 1, last_rus_letter - 1, quote)
        # выделяем разбираемый кусок текста из прочитанной строки
        # чтобы избежать попадания в неё скобок
        # удаляем плюс в конце, если он есть
        draft = draft[:end_of_line].strip()
        # перекодируем буферную строку, bytes => utf-8
        # если есть закодированные символы, обрабатываем их
        # иначе просто переводим байтовую строку в юникод
        # print(draft)
        if self.check_encoded_russian_letters(draft):
            # draft = self.decode_russian_letters(draft)
            draft = self.decode_russian_letters_regex(draft)
        else:
            # удаляем из строки лишние кавычки перед преобразованием в юникод
            draft = draft.replace(b"'", b"").decode("utf-8")
        # добавляем строку в буфер для сборки токена
        self.concat_strings_buffer.append(draft)
        # если в конце стоял '+', ищем следующий токен
        # иначе склеиваем новый токен из строк в буфере
        if self.in_concat_mode:
            self.assignment = False
            self.reader.forward(distance)
            self.fetch_next_token()
        else:
            self.current_token = QuotedStringToken(self.mark, "".join(self.concat_strings_buffer))
            self.concat_strings_buffer = []
            self.reader.forward(distance)

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
        self.current_token = IdentifierToken(self.mark, word.decode("utf-8"))
        self.reader.forward(len(word) - 1)

    def fetch_boolean(self, word: bytes) -> None:
        self.current_token = BooleanToken(self.mark, word.decode("utf-8").title() == "True")
        self.reader.forward(len(word) - 1)

    def fetch_binary_sequence_start(self) -> None:
        self.reading_binary_data = True
        self.current_token = BinarySequenceStartToken(self.mark)

    def fetch_binary_sequence_end(self) -> None:
        self.reading_binary_data = False
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
        # раскомментируйте эту строку и закомментируйте следующую, чтобы
        # данные из {} извлекались как 'A00F4' а не как [10, 0, 0, 15, 4]
        # при сохранении в json строки выглядят читабельнее массивов
        self.current_token = BinaryDataToken(self.mark, word.decode("utf-8"))
        # self.current_token = BinaryDataToken(self.mark, [int(d, 16) for d in word.decode("utf-8")])
        self.reader.forward(len(word) - 1)

    def fetch_end_of_file(self) -> None:
        self.current_token = EndOfFileToken(self.mark)
        self.done = True
