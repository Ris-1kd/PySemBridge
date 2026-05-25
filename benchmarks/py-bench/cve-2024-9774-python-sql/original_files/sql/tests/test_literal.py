# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Flavor, Literal


class TestLiteral(unittest.TestCase):
    def test_literal(self):
        literal = Literal(1)
        self.assertEqual(str(literal), '%s')
        self.assertEqual(literal.params, (1,))
        self.assertEqual(literal.value, 1)

    def test_no_boolean(self):
        true = Literal(True)
        false = Literal(False)
        self.assertEqual(str(true), '%s')
        self.assertEqual(true.params, (True,))
        self.assertEqual(str(false), '%s')
        self.assertEqual(false.params, (False,))
        try:
            Flavor.set(Flavor(no_boolean=True))
            self.assertEqual(str(true), '(1 = 1)')
            self.assertEqual(str(false), '(1 != 1)')
            self.assertEqual(true.params, ())
            self.assertEqual(false.params, ())
        finally:
            Flavor.set(Flavor())
