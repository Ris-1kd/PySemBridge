# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Collate, Column, Table


class TestCollate(unittest.TestCase):
    column = Column(Table('t'), 'c')

    def test_collate(self):
        for collate in [Collate(self.column, 'C'), self.column.collate('C')]:
            self.assertEqual(str(collate), '"c" COLLATE "C"')
            self.assertEqual(collate.params, ())

    def test_collate_no_expression(self):
        collate = Collate("foo", 'C')
        self.assertEqual(str(collate), '%s COLLATE "C"')
        self.assertEqual(collate.params, ("foo",))

    def test_collate_injection(self):
        collate = Collate(self.column, 'C";')
        with self.assertRaises(ValueError):
            str(collate)
