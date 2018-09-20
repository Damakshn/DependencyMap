import unittest
from dfm.reader import Reader, ReaderError

class TestReader(unittest.TestCase):

    def setUp(self):
        self.data = bytes("object TForm1: Form\r\n\t\tproperty1 = 123\r\n\t\tproperty2 = qwerty", "utf-8")
        self.r = Reader(self.data)

    def test_init(self):
        """
        Убеждаемся, что Reader инициализирован правильно
        """
        a = (self.r.line == 0)
        b = (self.r.pointer == 0)
        c = (self.r.eof == False)
        self.assertTrue(a and b and c)

    def test_forward(self):
        """
        Функция forward правильно перемещает нас от символа к символу
        """
        a = (chr(self.r.peek()) == "o")
        self.r.forward()
        b = (chr(self.r.peek()) == "b")
        self.assertTrue(a and b)
   
    def test_forward_out_of_range(self):
        """
        Функция forward не должна заходить за пределы диапазона
        """
        self.assertRaises(ReaderError, self.r.forward, len(self.data)*2)

    def test_eof_detection(self):
        self.r.forward(len(self.data))
        self.assertTrue(self.r.eof)

    def test_peek(self):
        """
        Проверка символа в текущей позиции
        """
        self.assertEqual(chr(self.r.peek()), "o")

    def test_peek_far(self):
        """
        Проверка символа подальше
        """
        self.assertEqual(chr(self.r.peek(12)), "1")    
    
    def test_peek_out_of_range(self):
        """
        Если посмотреть за пределы диапазона, то получим нуль-символ
        """        
        self.assertEqual(self.r.peek(1000), b"\0")
    
    def test_line_counting(self):
        """
        Количество строк во входных данных считается правильно
        """
        self.r.forward(len(self.data)-1)
        self.assertEqual(self.r.line, 2)

    def test_get_chunk(self):
        """
        Получение частей определённой длины
        """
        chunk = self.r.get_chunk(6)
        self.assertEqual(chunk, b"object")

    def test_get_too_big_chunk(self):
        self.assertRaises(ReaderError, self.r.get_chunk, 10000)
