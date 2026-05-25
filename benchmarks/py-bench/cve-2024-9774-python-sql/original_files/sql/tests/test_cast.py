# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Cast, Column, Table


class TestCast(unittest.TestCase):
    column = Column(Table('t'), 'c')

    def test_cast(self):
        for cast in [Cast(self.column, 'int'), self.column.cast('int')]:
            self.assertEqual(str(cast), 'CAST("c" AS int)')
            self.assertEqual(cast.params, ())

    def test_cast_no_expression(self):
        cast = Cast(1.1, 'int')
        self.assertEqual(str(cast), 'CAST(%s AS int)')
        self.assertEqual(cast.params, (1.1,))
