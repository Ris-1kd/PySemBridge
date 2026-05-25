# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import AliasManager, Literal, Table, Values, With, WithQuery


class TestWith(unittest.TestCase):
    table = Table('t')

    def test_with(self):
        with AliasManager():
            simple = With(query=self.table.select(self.table.id,
                    where=self.table.id == 1))

            self.assertEqual(simple.statement(),
                '"a" AS ('
                'SELECT "b"."id" FROM "t" AS "b" WHERE ("b"."id" = %s)'
                ')')
            self.assertEqual(simple.statement_params(), (1,))

    def test_with_columns(self):
        with AliasManager():
            second = With('a', query=self.table.select(self.table.a))

            self.assertEqual(second.statement(),
                '"a" ("a") AS ('
                'SELECT "b"."a" FROM "t" AS "b"'
                ')')
            self.assertEqual(second.statement_params(), ())

    def test_with_query(self):
        with AliasManager():
            simple = With()
            simple.query = self.table.select(self.table.id,
                where=self.table.id == 1)
            second = With()
            second.query = simple.select()

            wq = WithQuery(with_=[simple, second])
            self.assertEqual(wq._with_str(),
                'WITH "a" AS ('
                'SELECT "b"."id" FROM "t" AS "b" WHERE ("b"."id" = %s)'
                '), "c" AS ('
                'SELECT * FROM "a" AS "a"'
                ') ')
            self.assertEqual(wq._with_params(), (1,))

    def test_recursive(self):
        upto10 = With('n', recursive=True)
        upto10.query = Values([(1,)])
        upto10.query |= upto10.select(
            upto10.n + Literal(1),
            where=upto10.n < Literal(100))
        upto10.query.all_ = True

        q = upto10.select(with_=[upto10])
        self.assertEqual(str(q),
            'WITH RECURSIVE "a" ("n") AS ('
            'VALUES (%s) '
            'UNION ALL '
            'SELECT ("a"."n" + %s) FROM "a" AS "a" WHERE ("a"."n" < %s)'
            ') SELECT * FROM "a" AS "a"')
        self.assertEqual(tuple(q.params), (1, 1, 100))
