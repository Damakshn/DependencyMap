"""
Тест
Доходит по строке от начала до конца
Заглядывает от начала до конца
Правильно достаёт слова
Выдаёт ошибки при выходе за пределы диапазона
"""

class ReaderError(Exception):
    pass

class Reader(object):

    def __init__(self, input_data):
        # нуль-символ как маркер конца файла        
        self.stream = input_data+b"\0"
        self.line = 0
        self.pointer = 0
        self.eof = (self.pointer >= len(input_data))

    def forward(self, length=1) -> None:
        if self.eof:
            return
        if self.pointer+length >= len(self.stream):
            raise ReaderError("Out of range")
        while length:
            self.pointer+=1
            if chr(self.stream[self.pointer]) == "\n":
                self.line += 1
            # конец файла будет за 1 символ до настоящего из-за \0
            if (self.pointer+1) == len(self.stream):
                self.eof = True                
            length-=1

    def peek(self, length=0):
        if (self.pointer+length) >= len(self.stream):
            return b"\0"
        return self.stream[self.pointer+length]

    def get_chunk(self, length=1):        
        if self.pointer+length-1 >= len(self.stream):
            raise ReaderError("Out of range")
        return self.stream[self.pointer:self.pointer+length]
