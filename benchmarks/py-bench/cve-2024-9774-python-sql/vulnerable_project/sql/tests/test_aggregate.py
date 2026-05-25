# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import AliasManager, Flavor, Literal, Table, Window
from sql.aggregate import Avg, Count


class TestAggregate(unittest.TestCase):
    table = Table('t')

    def test_avg(self):
        avg = Avg(self.table.c)
        self.assertEqual(str(avg), 'AVG("c")')

        avg = Avg(self.table.a + self.table.b)
        self.assertEqual(str(avg), 'AVG(("a" + "b"))')

    def test_count_without_expression(self):
        count = Count()
        self.assertEqual(str(count), 'COUNT(%s)')
        self.assertEqual(count.params, ('*',))

    def test_order_by_one_column(self):
        avg = Avg(self.table.a, order_by=self.table.b)
        self.assertEqual(str(avg), 'AVG("a" ORDER BY "b")')
        self.assertEqual(avg.params, ())

    def test_order_by_multiple_columns(self):
        avg = Avg(
            self.table.a, order_by=[self.table.b.asc, self.table.c.desc])
        self.assertEqual(str(avg), 'AVG("a" ORDER BY "b" ASC, "c" DESC)')
        self.assertEqual(avg.params, ())

    def test_within(self):
        avg = Avg(self.table.a, within=self.table.b)
        self.assertEqual(str(avg), 'AVG("a") WITHIN GROUP (ORDER BY "b")')
        self.assertEqual(avg.params, ())

    def test_filter(self):
        flavor = Flavor(filter_=True)
        Flavor.set(flavor)
        try:
            avg = Avg(self.table.a + 1, filter_=self.table.a > 0)
            self.assertEqual(
                str(avg), 'AVG(("a" + %s)) FILTER (WHERE ("a" > %s))')
            self.assertEqual(avg.params, (1, 0))
        finally:
            Flavor.set(Flavor())

    def test_filter_case(self):
        avg = Avg(self.table.a + 1, filter_=self.table.a > 0)
        self.assertEqual(
            str(avg), 'AVG(CASE WHEN ("a" > %s) THEN ("a" + %s) END)')
        self.assertEqual(avg.params, (0, 1))

    def test_filter_case_count_star(self):
        count = Count(Literal('*'), filter_=self.table.a > 0)
        self.assertEqual(
            str(count), 'COUNT(CASE WHEN ("a" > %s) THEN %s END)')
        self.assertEqual(count.params, (0, 1))

    def test_window(self):
        avg = Avg(self.table.c, window=Window([]))
        with AliasManager():
            self.assertEqual(str(avg), 'AVG("a"."c") OVER ()')
        self.assertEqual(avg.params, ())

    def test_distinct(self):
        avg = Avg(self.table.c, distinct=True)
        self.assertEqual(str(avg), 'AVG(DISTINCT "c")')
        self.assertEqual(avg.params, ())
