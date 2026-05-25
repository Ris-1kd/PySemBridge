# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import warnings
from copy import deepcopy

from sql import (
    Cube, Flavor, For, Grouping, Join, Literal, Rollup, Select, Table, Union,
    Window, With)
from sql.aggregate import Max, Min
from sql.functions import DatePart, Function, Now, Rank


class TestSelect(unittest.TestCase):
    table = Table('t')

    def test_select1(self):
        query = self.table.select()
        self.assertEqual(str(query), 'SELECT * FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_select2(self):
        query = self.table.select(self.table.c)
        self.assertEqual(str(query), 'SELECT "a"."c" FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), ())

        query.columns += (self.table.c2,)
        self.assertEqual(str(query),
            'SELECT "a"."c", "a"."c2" FROM "t" AS "a"')

    def test_select3(self):
        query = self.table.select(where=(self.table.c == 'foo'))
        self.assertEqual(str(query),
            'SELECT * FROM "t" AS "a" WHERE ("a"."c" = %s)')
        self.assertEqual(tuple(query.params), ('foo',))

    def test_select_without_from(self):
        query = Select([Literal(1)])
        self.assertEqual(str(query), 'SELECT %s')
        self.assertEqual(tuple(query.params), (1,))

    def test_select_select(self):
        query = Select([Select([Literal(1)])])
        self.assertEqual(str(query), 'SELECT (SELECT %s)')
        self.assertEqual(tuple(query.params), (1,))

    def test_select_select_as(self):
        query = Select([Select([Literal(1)]).as_('foo')])
        self.assertEqual(str(query), 'SELECT (SELECT %s) AS "foo"')
        self.assertEqual(tuple(query.params), (1,))

    def test_select_distinct(self):
        query = self.table.select(self.table.c, distinct=True)
        self.assertEqual(
            str(query), 'SELECT DISTINCT "a"."c" FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_select_distinct_on(self):
        query = self.table.select(self.table.c, distinct_on=self.table.c)
        self.assertEqual(
            str(query), 'SELECT DISTINCT ON ("a"."c") "a"."c" FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), ())

        query = self.table.select(
            self.table.c, distinct_on=[self.table.a, self.table.b])
        self.assertEqual(
            str(query),
            'SELECT DISTINCT ON ("a"."a", "a"."b") "a"."c" FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_select_from_list(self):
        t2 = Table('t2')
        t3 = Table('t3')
        query = (self.table + t2 + t3).select(self.table.c, getattr(t2, '*'))
        self.assertEqual(str(query),
            'SELECT "a"."c", "b".* FROM "t" AS "a", "t2" AS "b", "t3" AS "c"')
        self.assertEqual(tuple(query.params), ())

    def test_select_union(self):
        query1 = self.table.select()
        query2 = Table('t2').select()
        union = query1 | query2
        self.assertEqual(str(union),
            'SELECT * FROM "t" AS "a" UNION SELECT * FROM "t2" AS "b"')
        union.all_ = True
        self.assertEqual(str(union),
            'SELECT * FROM "t" AS "a" UNION ALL '
            'SELECT * FROM "t2" AS "b"')
        self.assertEqual(str(union.select()),
            'SELECT * FROM ('
            'SELECT * FROM "t" AS "b" UNION ALL '
            'SELECT * FROM "t2" AS "c") AS "a"')
        query1.where = self.table.c == 'foo'
        self.assertEqual(str(union),
            'SELECT * FROM "t" AS "a" WHERE ("a"."c" = %s) UNION ALL '
            'SELECT * FROM "t2" AS "b"')
        self.assertEqual(tuple(union.params), ('foo',))

        union = Union(query1)
        self.assertEqual(str(union), str(query1))
        self.assertEqual(tuple(union.params), tuple(query1.params))

    def test_select_union_order(self):
        query1 = self.table.select()
        query2 = Table('t2').select()
        union = query1 | query2
        union.order_by = Literal(1)
        self.assertEqual(str(union),
            'SELECT * FROM "t" AS "a" UNION '
            'SELECT * FROM "t2" AS "b" '
            'ORDER BY %s')
        self.assertEqual(tuple(union.params), (1,))

    def test_select_intersect(self):
        query1 = self.table.select()
        query2 = Table('t2').select()
        intersect = query1 & query2
        self.assertEqual(str(intersect),
            'SELECT * FROM "t" AS "a" INTERSECT SELECT * FROM "t2" AS "b"')

        from sql import Interesect, Intersect
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            interesect = Interesect(query1, query2)
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[-1].category, DeprecationWarning))
            if hasattr(self, 'assertIn'):
                self.assertIn('Interesect query is deprecated, use Intersect',
                    str(w[-1].message))
        self.assertTrue(isinstance(interesect, Intersect))

    def test_select_except(self):
        query1 = self.table.select()
        query2 = Table('t2').select()
        except_ = query1 - query2
        self.assertEqual(str(except_),
            'SELECT * FROM "t" AS "a" EXCEPT SELECT * FROM "t2" AS "b"')

    def test_select_join(self):
        t1 = Table('t1')
        t2 = Table('t2')
        join = Join(t1, t2)

        self.assertEqual(str(join.select()),
            'SELECT * FROM "t1" AS "a" INNER JOIN "t2" AS "b"')
        self.assertEqual(str(join.select(getattr(t1, '*'))),
            'SELECT "a".* FROM "t1" AS "a" INNER JOIN "t2" AS "b"')

    def test_select_subselect(self):
        t1 = Table('t1')
        select = t1.select()
        self.assertEqual(str(select.select()),
            'SELECT * FROM (SELECT * FROM "t1" AS "b") AS "a"')
        self.assertEqual(tuple(select.params), ())

    def test_select_function(self):
        query = Now().select()
        self.assertEqual(str(query), 'SELECT * FROM NOW() AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_select_function_columns_definitions(self):
        class Crosstab(Function):
            _function = 'CROSSTAB'

        query = Crosstab('query1', 'query2',
            columns_definitions=[
                ('c1', 'INT'), ('c2', 'CHAR'), ('c3', 'BOOL')]).select()
        self.assertEqual(str(query), 'SELECT * FROM CROSSTAB(%s, %s) '
            'AS "a" ("c1" INT, "c2" CHAR, "c3" BOOL)')
        self.assertEqual(tuple(query.params), ('query1', 'query2'))

    def test_select_group_by(self):
        column = self.table.c
        query = self.table.select(column, group_by=column)
        self.assertEqual(str(query),
            'SELECT "a"."c" FROM "t" AS "a" GROUP BY "a"."c"')
        self.assertEqual(tuple(query.params), ())

        output = column.as_('c1')
        query = self.table.select(output, group_by=output)
        self.assertEqual(str(query),
            'SELECT "a"."c" AS "c1" FROM "t" AS "a" GROUP BY "c1"')
        self.assertEqual(tuple(query.params), ())

        query = self.table.select(Literal('foo'), group_by=Literal('foo'))
        self.assertEqual(str(query),
            'SELECT %s FROM "t" AS "a" GROUP BY %s')
        self.assertEqual(tuple(query.params), ('foo', 'foo'))

    def test_select_group_by_grouping_sets(self):
        query = self.table.select(
            Literal('*'),
            group_by=Grouping((self.table.a, self.table.b), (Literal('foo'),)))
        self.assertEqual(str(query),
            'SELECT %s FROM "t" AS "a" '
            'GROUP BY GROUPING SETS (("a"."a", "a"."b"), (%s))')
        self.assertEqual(tuple(query.params), ('*', 'foo',))

        query = self.table.select(
            Literal('*'),
            group_by=[
                self.table.a, Grouping((self.table.b,), (self.table.c,))])
        self.assertEqual(str(query),
            'SELECT %s FROM "t" AS "a" '
            'GROUP BY "a"."a", GROUPING SETS (("a"."b"), ("a"."c"))')
        self.assertEqual(tuple(query.params), ('*',))

    def test_select_group_by_rollup(self):
        query = self.table.select(
            Literal('*'),
            group_by=Rollup(self.table.a, self.table.b, Literal('foo')))
        self.assertEqual(str(query),
            'SELECT %s FROM "t" AS "a" '
            'GROUP BY ROLLUP ("a"."a", "a"."b", %s)')
        self.assertEqual(tuple(query.params), ('*', 'foo'))

        query = self.table.select(
            Literal('*'),
            group_by=Rollup((self.table.a, self.table.b), self.table.c))
        self.assertEqual(str(query),
            'SELECT %s FROM "t" AS "a" '
            'GROUP BY ROLLUP (("a"."a", "a"."b"), "a"."c")')
        self.assertEqual(tuple(query.params), ('*',))

    def test_select_group_by_cube(self):
        query = self.table.select(
            Literal('*'),
            group_by=Cube(self.table.a, self.table.b))
        self.assertEqual(str(query),
            'SELECT %s FROM "t" AS "a" '
            'GROUP BY CUBE ("a"."a", "a"."b")')
        self.assertEqual(tuple(query.params), ('*',))

    def test_select_having(self):
        col1 = self.table.col1
        col2 = self.table.col2
        query = self.table.select(col1, Min(col2),
            having=(Min(col2) > 3))
        self.assertEqual(str(query),
            'SELECT "a"."col1", MIN("a"."col2") FROM "t" AS "a" '
            'HAVING (MIN("a"."col2") > %s)')
        self.assertEqual(tuple(query.params), (3,))

    def test_select_order(self):
        c = self.table.c
        query = self.table.select(c, order_by=Literal(1))
        self.assertEqual(str(query),
            'SELECT "a"."c" FROM "t" AS "a" ORDER BY %s')
        self.assertEqual(tuple(query.params), (1,))

    def test_select_limit_offset(self):
        try:
            Flavor.set(Flavor(limitstyle='limit'))
            query = self.table.select(limit=50, offset=10)
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a" LIMIT %s OFFSET %s')
            self.assertEqual(tuple(query.params), (50, 10))

            query.limit = None
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a" OFFSET %s')
            self.assertEqual(tuple(query.params), (10,))

            query.offset = 0
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a"')
            self.assertEqual(tuple(query.params), ())

            Flavor.set(Flavor(limitstyle='limit', max_limit=-1))

            query.offset = None
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a"')
            self.assertEqual(tuple(query.params), ())

            query.offset = 0
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a"')
            self.assertEqual(tuple(query.params), ())

            query.offset = 10
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a" LIMIT -1 OFFSET %s')
            self.assertEqual(tuple(query.params), (10,))
        finally:
            Flavor.set(Flavor())

    def test_select_offset_fetch(self):
        try:
            Flavor.set(Flavor(limitstyle='fetch'))
            query = self.table.select(limit=50, offset=10)
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a" '
                'OFFSET (%s) ROWS FETCH FIRST (%s) ROWS ONLY')
            self.assertEqual(tuple(query.params), (10, 50))

            query.limit = None
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a" OFFSET (%s) ROWS')
            self.assertEqual(tuple(query.params), (10,))

            query.offset = 0
            self.assertEqual(str(query),
                'SELECT * FROM "t" AS "a"')
            self.assertEqual(tuple(query.params), ())
        finally:
            Flavor.set(Flavor())

    def test_select_rownum(self):
        try:
            Flavor.set(Flavor(limitstyle='rownum'))
            query = self.table.select(limit=50, offset=10)
            self.assertEqual(str(query),
                'SELECT "a".* FROM ('
                    'SELECT "b".*, ROWNUM AS "rnum" FROM ('
                        'SELECT * FROM "t" AS "c") AS "b" '
                    'WHERE (ROWNUM <= %s)) AS "a" '
                'WHERE ("rnum" > %s)')
            self.assertEqual(tuple(query.params), (60, 10))

            query = self.table.select(
                self.table.c1.as_('col1'), self.table.c2.as_('col2'),
                limit=50, offset=10)
            self.assertEqual(str(query),
                'SELECT "a"."col1", "a"."col2" FROM ('
                    'SELECT "b"."col1", "b"."col2", ROWNUM AS "rnum" FROM ('
                        'SELECT "c"."c1" AS "col1", "c"."c2" AS "col2" '
                        'FROM "t" AS "c") AS "b" '
                    'WHERE (ROWNUM <= %s)) AS "a" '
                'WHERE ("rnum" > %s)')
            self.assertEqual(tuple(query.params), (60, 10))

            subquery = query.select(query.col1, query.col2)
            self.assertEqual(str(subquery),
                'SELECT "a"."col1", "a"."col2" FROM ('
                    'SELECT "b"."col1", "b"."col2" FROM ('
                        'SELECT "a"."col1", "a"."col2", ROWNUM AS "rnum" '
                        'FROM ('
                            'SELECT "c"."c1" AS "col1", "c"."c2" AS "col2" '
                            'FROM "t" AS "c") AS "a" '
                        'WHERE (ROWNUM <= %s)) AS "b" '
                    'WHERE ("rnum" > %s)) AS "a"')
            # XXX alias of query is reused but not a problem
            # as it is hidden in subquery
            self.assertEqual(tuple(query.params), (60, 10))

            query = self.table.select(limit=50, offset=10,
                order_by=[self.table.c])
            self.assertEqual(str(query),
                'SELECT "a".* FROM ('
                    'SELECT "b".*, ROWNUM AS "rnum" FROM ('
                        'SELECT * FROM "t" AS "c" ORDER BY "c"."c") AS "b" '
                    'WHERE (ROWNUM <= %s)) AS "a" '
                'WHERE ("rnum" > %s)')
            self.assertEqual(tuple(query.params), (60, 10))

            query = self.table.select(limit=50)
            self.assertEqual(str(query),
                'SELECT "a".* FROM ('
                    'SELECT * FROM "t" AS "b") AS "a" '
                'WHERE (ROWNUM <= %s)')
            self.assertEqual(tuple(query.params), (50,))

            query = self.table.select(offset=10)
            self.assertEqual(str(query),
                'SELECT "a".* FROM ('
                    'SELECT "b".*, ROWNUM AS "rnum" FROM ('
                        'SELECT * FROM "t" AS "c") AS "b") AS "a" '
                'WHERE ("rnum" > %s)')
            self.assertEqual(tuple(query.params), (10,))

            query = self.table.select(self.table.c.as_('col'),
                where=self.table.c >= 20,
                limit=50, offset=10)
            self.assertEqual(str(query),
                'SELECT "a"."col" FROM ('
                    'SELECT "b"."col", ROWNUM AS "rnum" FROM ('
                        'SELECT "c"."c" AS "col" FROM "t" AS "c" '
                        'WHERE ("c"."c" >= %s)) AS "b" '
                    'WHERE (ROWNUM <= %s)) AS "a" '
                'WHERE ("rnum" > %s)')
            self.assertEqual(tuple(query.params), (20, 60, 10))
        finally:
            Flavor.set(Flavor())

    def test_select_for(self):
        c = self.table.c
        query = self.table.select(c, for_=For('UPDATE'))
        self.assertEqual(str(query),
            'SELECT "a"."c" FROM "t" AS "a" FOR UPDATE')
        self.assertEqual(tuple(query.params), ())

    def test_copy(self):
        query = self.table.select()
        copy_query = deepcopy(query)
        self.assertNotEqual(query, copy_query)
        self.assertEqual(str(copy_query), 'SELECT * FROM "t" AS "a"')
        self.assertEqual(tuple(copy_query.params), ())

    def test_with(self):
        w = With(query=self.table.select(self.table.c1))

        query = w.select(with_=[w])
        self.assertEqual(str(query),
            'WITH "a" AS (SELECT "b"."c1" FROM "t" AS "b") '
            'SELECT * FROM "a" AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_window(self):
        query = self.table.select(Min(self.table.c1,
                window=Window([self.table.c2])))

        self.assertEqual(str(query),
            'SELECT MIN("a"."c1") OVER "b" FROM "t" AS "a" '
            'WINDOW "b" AS (PARTITION BY "a"."c2")')
        self.assertEqual(tuple(query.params), ())

        query = self.table.select(Rank(window=Window([])))
        self.assertEqual(str(query),
            'SELECT RANK() OVER "b" FROM "t" AS "a" '
            'WINDOW "b" AS ()')
        self.assertEqual(tuple(query.params), ())

        window = Window([self.table.c1])
        query = self.table.select(
            Rank(filter_=self.table.c1 > 0, window=window),
            Min(self.table.c1, window=window))
        self.assertEqual(str(query),
            'SELECT RANK() FILTER (WHERE ("a"."c1" > %s)) OVER "b", '
            'MIN("a"."c1") OVER "b" FROM "t" AS "a" '
            'WINDOW "b" AS (PARTITION BY "a"."c1")')
        self.assertEqual(tuple(query.params), (0,))

        window = Window([DatePart('year', self.table.date_col)])
        query = self.table.select(
            Min(self.table.c1, window=window))
        self.assertEqual(str(query),
            'SELECT MIN("a"."c1") OVER "b" FROM "t" AS "a" '
            'WINDOW "b" AS (PARTITION BY DATE_PART(%s, "a"."date_col"))')
        self.assertEqual(tuple(query.params), ('year',))

        window = Window([self.table.c2])
        query = self.table.select(
            Max(self.table.c1, window=window)
            / Min(self.table.c1, window=window))
        self.assertEqual(str(query),
            'SELECT (MAX("a"."c1") OVER (PARTITION BY "a"."c2") '
            '/ MIN("a"."c1") OVER (PARTITION BY "a"."c2")) '
            'FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), ())

        window = Window([Literal(1)])
        query = self.table.select(
            Max(self.table.c1, window=window)
            / Min(self.table.c1, window=window))
        self.assertEqual(str(query),
            'SELECT (MAX("a"."c1") OVER (PARTITION BY %s) '
            '/ MIN("a"."c1") OVER (PARTITION BY %s)) '
            'FROM "t" AS "a"')
        self.assertEqual(tuple(query.params), (1, 1))

        window1 = Window([self.table.c2])
        window2 = Window([Literal(1)])
        query = self.table.select(
            Max(self.table.c1, window=window1)
            / Min(self.table.c1, window=window2),
            windows=[window1])
        self.assertEqual(str(query),
            'SELECT (MAX("a"."c1") OVER "b" '
            '/ MIN("a"."c1") OVER (PARTITION BY %s)) '
            'FROM "t" AS "a" '
            'WINDOW "b" AS (PARTITION BY "a"."c2")')
        self.assertEqual(tuple(query.params), (1,))

    def test_order_params(self):
        with_ = With(query=self.table.select(self.table.c,
                where=(self.table.c > 1)))
        w = Window([Literal(8)])
        query = Select([Literal(2), Min(self.table.c, window=w)],
            from_=self.table.select(where=self.table.c > 3),
            with_=with_,
            where=self.table.c > 4,
            group_by=[Literal(5)],
            order_by=[Literal(6)],
            having=Literal(7))
        self.assertEqual(tuple(query.params), (1, 2, 3, 4, 5, 6, 7, 8))

    def test_no_as(self):
        query = self.table.select(self.table.c)
        try:
            Flavor.set(Flavor(no_as=True))
            self.assertEqual(str(query), 'SELECT "a"."c" FROM "t" "a"')
            self.assertEqual(tuple(query.params), ())
        finally:
            Flavor.set(Flavor())
