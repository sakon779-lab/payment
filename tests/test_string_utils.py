from unittest import TestCase
from src.utils.string_utils import reverse_string

class TestStringUtils(TestCase):
    def test_reverse_string(self):
        self.assertEqual(reverse_string('hello'), 'olleh')
        self.assertEqual(reverse_string('world'), 'dlrow')
        self.assertEqual(reverse_string(''), '')
        self.assertEqual(reverse_string('a'), 'a')
