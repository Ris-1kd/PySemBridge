# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import As, Column, Flavor, Table


class TestAs(unittest.TestCase):
    table = Table('t')
    column = Column(table, 'c')

    def test_as(self):
        self.assertEqual(str(As(self.column, 'foo')), '"foo"')

    def test_as_select(self):
        query = self.table.select(self.column.as_('foo'))
        self.assertEqual(str(query), 'SELECT "a"."c" AS "foo" FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_no_as(self):
        query = self.table.select(self.column.as_('foo'))
        try:
            Flavor.set(Flavor(no_as=True))
            self.assertEqual(str(query), 'SELECT "a"."c" "foo" FROM "t" "a"')
            self.assertEqual(tuple(query.params), ())
        finally:
            Flavor.set(Flavor())
