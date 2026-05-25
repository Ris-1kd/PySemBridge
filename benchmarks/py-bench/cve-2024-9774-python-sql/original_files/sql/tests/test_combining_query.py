# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Table, Union, With


class TestUnion(unittest.TestCase):
    q1 = Table('t1').select()
    q2 = Table('t2').select()
    q3 = Table('t3').select()

    def test_union2(self):
        query = Union(self.q1, self.q2)
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b"')
        self.assertEqual(tuple(query.params), ())

        query = self.q1 | self.q2
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b"')
        self.assertEqual(tuple(query.params), ())

    def test_union_with(self):
        table = Table('t')
        with_ = With()
        with_.query = table.select(table.id, where=table.id == 1)
        query = Union(self.q1, self.q2, with_=with_)

        self.assertEqual(str(query),
            'WITH "a" AS ('
            'SELECT "b"."id" FROM "t" AS "b" WHERE ("b"."id" = %s)) '
            'SELECT * FROM "t1" AS "c" UNION SELECT * FROM "t2" AS "d"')
        self.assertEqual(tuple(query.params), (1,))

    def test_union3(self):
        query = Union(self.q1, self.q2, self.q3)
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(tuple(query.params), ())

        query = Union(Union(self.q1, self.q2), self.q3)
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(tuple(query.params), ())

        query = Union(self.q1, Union(self.q2, self.q3))
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(tuple(query.params), ())

        query = self.q1 | self.q2 | self.q3
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(tuple(query.params), ())
