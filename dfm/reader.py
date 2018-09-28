from .mark import Mark


class ReaderError(Exception):
    pass


class Reader(object):

    def __init__(self, input_data):
        # нуль-символ как маркер конца файла
        self.stream = input_data + b"\0"
        self.line = 0
        self.pointer = 0
        self.index = 0
        self.eof = (self.pointer >= len(input_data))

    def forward(self, length=1) -> None:
        if self.eof:
            return
        if self.pointer + length >= len(self.stream):
            raise ReaderError("Out of range")
        while length:
            self.pointer += 1
            self.index += 1
            if chr(self.stream[self.pointer]) == "\n":
                self.line += 1
                self.index = 0
            if (self.pointer + 1) == len(self.stream):
                self.eof = True
            length -= 1

    def peek(self, length=0):
        if (self.pointer + length) >= len(self.stream):
            return b"\0"
        return self.stream[self.pointer + length]

    def get_chunk(self, length=1):
        if self.pointer + length - 1 >= len(self.stream):
            raise ReaderError("Out of range")
        return self.stream[self.pointer:self.pointer + length]

    def copy_to_end_of_line(self):
        stop = False
        length = 0
        while not stop:
            if self.peek(length) not in b"\r\n\0":
                length += 1
            else:
                stop = True
        if length > 0:
            return self.get_chunk(length)
        return b""

    def get_mark(self):
        return Mark(self.index, self.line)
