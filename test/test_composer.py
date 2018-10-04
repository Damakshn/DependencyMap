from dfm.composer import Composer, ComposerError
import unittest


class TestComposer(unittest.TestCase):

    def test_nested_objects(self):
        data = b"object obj: tp\r\n field1 = 1\r\n object label1: TLabel\r\n  caption = 'qwerty'\r\n end\r\nend"
        fixture = {
            "name": "obj",
            "type": "tp",
            "field1": 1,
            "label1": {
                "name": "label1",
                "type": "TLabel",
                "caption": "qwerty"
            }
        }
        c = Composer(data)
        converted = c.compose_file()
        self.assertEqual(converted, fixture)

    def test_duplicate_keys_in_object(self):
        data = b"object obj: tp\r\n field1 = 1\r\n field1 = 2\r\nend"
        c = Composer(data)
        self.assertRaises(ComposerError, c.compose_file)

    def test_duplicate_keys_in_item(self):
        data = b"object obj: tp\r\n field = <\r\nitem\r\nfield1 = 1\r\nfield1 = 'qwerty'\r\nend>\r\nend"
        c = Composer(data)
        self.assertRaises(ComposerError, c.compose_file)
