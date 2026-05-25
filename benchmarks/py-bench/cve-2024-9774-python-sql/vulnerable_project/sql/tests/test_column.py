# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import AliasManager, Column, Table


class TestColumn(unittest.TestCase):
    def test_column(self):
        column = Column(Table('t'), 'c')
        self.assertEqual(str(column), '"c"')
        self.assertEqual(column.name, 'c')
        self.assertEqual(column.column_name, '"c"')

        with AliasManager():
            self.assertEqual(str(column), '"a"."c"')

    def test_quote_in_column(self):
        column = Column(Table('t'), 'b "c"')
        self.assertEqual(str(column), '"b ""c"""')
        self.assertEqual(column.name, 'b "c"')
        self.assertEqual(column.column_name, '"b ""c"""')

        with AliasManager():
            self.assertEqual(str(column), '"a"."b ""c"""')
