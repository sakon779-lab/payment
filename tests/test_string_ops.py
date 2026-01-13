import unittest
from src.utils.string_ops import reverse_string

class TestStringOps(unittest.TestCase):
    def test_reverse_string(self):
        self.assertEqual(reverse_string('hello'), 'olleh')
        self.assertIsNone(reverse_string(''))
        self.assertEqual(reverse_string('a'), 'a')

if __name__ == '__main__':
    unittest.main()