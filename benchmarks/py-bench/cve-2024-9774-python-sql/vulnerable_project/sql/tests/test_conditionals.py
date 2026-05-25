# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Table
from sql.conditionals import Case, Coalesce, Greatest, Least, NullIf


class TestConditionals(unittest.TestCase):
    table = Table('t')

    def test_case(self):
        case = Case((self.table.c1, 'foo'),
            (self.table.c2, 'bar'),
            else_=self.table.c3)
        self.assertEqual(str(case),
            'CASE WHEN "c1" THEN %s '
            'WHEN "c2" THEN %s '
            'ELSE "c3" END')
        self.assertEqual(case.params, ('foo', 'bar'))

    def test_case_no_expression(self):
        case = Case((True, self.table.c1), (self.table.c2, False),
            else_=False)
        self.assertEqual(str(case),
            'CASE WHEN %s THEN "c1" '
            'WHEN "c2" THEN %s '
            'ELSE %s END')
        self.assertEqual(case.params, (True, False, False))

    def test_case_sql(self):
        case = Case(
            (self.table.select(self.table.bool,
                    where=self.table.c2 == 'bar'), self.table.c1),
            else_=self.table.select(self.table.c1,
                where=self.table.c2 == 'foo'))
        self.assertEqual(str(case),
            'CASE WHEN '
            '(SELECT "a"."bool" FROM "t" AS "a" WHERE ("a"."c2" = %s)) '
            'THEN "c1" '
            'ELSE (SELECT "a"."c1" FROM "t" AS "a" WHERE ("a"."c2" = %s)) END')
        self.assertEqual(case.params, ('bar', 'foo'))

    def test_coalesce(self):
        coalesce = Coalesce(self.table.c1, self.table.c2, 'foo')
        self.assertEqual(str(coalesce), 'COALESCE("c1", "c2", %s)')
        self.assertEqual(coalesce.params, ('foo',))

    def test_coalesce_sql(self):
        coalesce = Coalesce(
            self.table.select(self.table.c1, where=self.table.c2 == 'bar'),
            self.table.c2)
        self.assertEqual(str(coalesce),
            'COALESCE('
            '(SELECT "a"."c1" FROM "t" AS "a" WHERE ("a"."c2" = %s)), "c2")')
        self.assertEqual(coalesce.params, ('bar',))

    def test_nullif(self):
        nullif = NullIf(self.table.c1, 'foo')
        self.assertEqual(str(nullif), 'NULLIF("c1", %s)')
        self.assertEqual(nullif.params, ('foo',))

    def test_greatest(self):
        greatest = Greatest(self.table.c1, self.table.c2, 'foo')
        self.assertEqual(str(greatest), 'GREATEST("c1", "c2", %s)')
        self.assertEqual(greatest.params, ('foo',))

    def test_least(self):
        least = Least(self.table.c1, self.table.c2, 'foo')
        self.assertEqual(str(least), 'LEAST("c1", "c2", %s)')
        self.assertEqual(least.params, ('foo',))
