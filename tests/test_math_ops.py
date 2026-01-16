from unittest import TestCase
from src.utils.math_ops import add, subtract, multiply

class TestMathOps(TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
    
    def test_subtract(self):
        self.assertEqual(subtract(5, 3), 2)

    def test_multiply(self):
        self.assertEqual(multiply(4, 6), 24)