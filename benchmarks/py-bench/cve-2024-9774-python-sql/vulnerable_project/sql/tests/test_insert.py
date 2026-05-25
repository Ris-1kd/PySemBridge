# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Conflict, Excluded, Table, With
from sql.functions import Abs


class TestInsert(unittest.TestCase):
    table = Table('t')

    def test_insert_default(self):
        query = self.table.insert()
        self.assertEqual(str(query), 'INSERT INTO "t" DEFAULT VALUES')
        self.assertEqual(tuple(query.params), ())

    def test_insert_values(self):
        query = self.table.insert([self.table.c1, self.table.c2],
            [['foo', 'bar']])
        self.assertEqual(str(query),
            'INSERT INTO "t" ("c1", "c2") VALUES (%s, %s)')
        self.assertEqual(tuple(query.params), ('foo', 'bar'))

    def test_insert_many_values(self):
        query = self.table.insert([self.table.c1, self.table.c2],
            [['foo', 'bar'], ['spam', 'eggs']])
        self.assertEqual(str(query),
            'INSERT INTO "t" ("c1", "c2") VALUES (%s, %s), (%s, %s)')
        self.assertEqual(tuple(query.params), ('foo', 'bar', 'spam', 'eggs'))

    def test_insert_subselect(self):
        t1 = Table('t1')
        t2 = Table('t2')
        subquery = t2.select(t2.c1, t2.c2)
        query = t1.insert([t1.c1, t1.c2], subquery)
        self.assertEqual(str(query),
            'INSERT INTO "t1" ("c1", "c2") '
            'SELECT "a"."c1", "a"."c2" FROM "t2" AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_insert_function(self):
        query = self.table.insert([self.table.c], [[Abs(-1)]])
        self.assertEqual(str(query),
            'INSERT INTO "t" ("c") VALUES (ABS(%s))')
        self.assertEqual(tuple(query.params), (-1,))

    def test_insert_returning(self):
        query = self.table.insert([self.table.c1, self.table.c2],
            [['foo', 'bar']], returning=[self.table.c1, self.table.c2])
        self.assertEqual(str(query),
            'INSERT INTO "t" AS "a" ("c1", "c2") VALUES (%s, %s) '
            'RETURNING "a"."c1", "a"."c2"')
        self.assertEqual(tuple(query.params), ('foo', 'bar'))

    def test_insert_returning_select(self):
        t1 = Table('t1')
        t2 = Table('t2')
        query = t1.insert([t1.c], [['foo']],
            returning=[
                t2.select(t2.c, where=(t2.c1 == t1.c) & (t2.c2 == 'bar'))])
        self.assertEqual(str(query),
            'INSERT INTO "t1" AS "b" ("c") VALUES (%s) '
            'RETURNING (SELECT "a"."c" FROM "t2" AS "a" '
            'WHERE (("a"."c1" = "b"."c") AND ("a"."c2" = %s)))')
        self.assertEqual(tuple(query.params), ('foo', 'bar'))

    def test_with(self):
        t1 = Table('t1')
        w = With(query=t1.select())

        query = self.table.insert(
            [self.table.c1],
            with_=[w],
            values=w.select())
        self.assertEqual(str(query),
            'WITH "a" AS (SELECT * FROM "t1" AS "b") '
            'INSERT INTO "t" ("c1") SELECT * FROM "a" AS "a"')
        self.assertEqual(tuple(query.params), ())

    def test_insert_in_with(self):
        t1 = Table('t1')

        w = With(query=self.table.insert(
                [self.table.c1],
                values=[['foo']],
                returning=[self.table.id]))
        query = t1.update(
            [t1.c],
            [w.id],
            from_=[w],
            with_=[w])
        self.assertEqual(str(query),
            'WITH "a" AS ('
                'INSERT INTO "t" AS "b" ("c1") VALUES (%s) '
                'RETURNING "b"."id") '
            'UPDATE "t1" AS "c" SET "c" = "a"."id" FROM "a" AS "a"')
        self.assertEqual(tuple(query.params), ('foo',))

    def test_schema(self):
        t1 = Table('t1', 'default')
        query = t1.insert([t1.c1], [['foo']])

        self.assertEqual(str(query),
            'INSERT INTO "default"."t1" ("c1") VALUES (%s)')
        self.assertEqual(tuple(query.params), ('foo',))

    def test_upsert_nothing(self):
        query = self.table.insert(
            [self.table.c1], [['foo']],
            on_conflict=Conflict(self.table))

        self.assertEqual(str(query),
            'INSERT INTO "t" AS "a" ("c1") VALUES (%s) '
            'ON CONFLICT DO NOTHING')
        self.assertEqual(tuple(query.params), ('foo',))

    def test_upsert_indexed_column(self):
        query = self.table.insert(
            [self.table.c1], [['foo']],
            on_conflict=Conflict(
                self.table,
                indexed_columns=[self.table.c1, self.table.c2]))

        self.assertEqual(str(query),
            'INSERT INTO "t" AS "a" ("c1") VALUES (%s) '
            'ON CONFLICT ("c1", "c2") DO NOTHING')
        self.assertEqual(tuple(query.params), ('foo',))

    def test_upsert_indexed_column_index_where(self):
        query = self.table.insert(
            [self.table.c1], [['foo']],
            on_conflict=Conflict(
                self.table,
                indexed_columns=[self.table.c1],
                index_where=self.table.c2 == 'bar'))

        self.assertEqual(str(query),
            'INSERT INTO "t" AS "a" ("c1") VALUES (%s) '
            'ON CONFLICT ("c1") WHERE ("a"."c2" = %s) DO NOTHING')
        self.assertEqual(tuple(query.params), ('foo', 'bar'))

    def test_upsert_update(self):
        query = self.table.insert(
            [self.table.c1], [['baz']],
            on_conflict=Conflict(
                self.table,
                columns=[self.table.c1, self.table.c2],
                values=['foo', 'bar']))

        self.assertEqual(str(query),
            'INSERT INTO "t" AS "a" ("c1") VALUES (%s) '
            'ON CONFLICT DO UPDATE SET ("c1", "c2") = (%s, %s)')
        self.assertEqual(tuple(query.params), ('baz', 'foo', 'bar'))

    def test_upsert_update_where(self):
        query = self.table.insert(
            [self.table.c1], [['baz']],
            on_conflict=Conflict(
                self.table,
                columns=[self.table.c1],
                values=['foo'],
                where=self.table.c2 == 'bar'))

        self.assertEqual(str(query),
            'INSERT INTO "t" AS "a" ("c1") VALUES (%s) '
            'ON CONFLICT DO UPDATE SET "c1" = (%s) '
            'WHERE ("a"."c2" = %s)')
        self.assertEqual(tuple(query.params), ('baz', 'foo', 'bar'))

    def test_upsert_update_subquery(self):
        t1 = Table('t1')
        t2 = Table('t2')
        subquery = t2.select(t2.c1, t2.c2)
        query = t1.insert(
            [t1.c1], [['baz']],
            on_conflict=Conflict(
                t1,
                columns=[t1.c1, t1.c2],
                values=subquery))

        self.assertEqual(str(query),
            'INSERT INTO "t1" AS "b" ("c1") VALUES (%s) '
            'ON CONFLICT DO UPDATE SET ("c1", "c2") = '
            '(SELECT "a"."c1", "a"."c2" FROM "t2" AS "a")')
        self.assertEqual(tuple(query.params), ('baz',))

    def test_upsert_update_excluded(self):
        query = self.table.insert(
            [self.table.c1], [[1]],
            on_conflict=Conflict(
                self.table,
                columns=[self.table.c1],
                values=[Excluded.c1 + 2]))

        self.assertEqual(str(query),
            'INSERT INTO "t" AS "a" ("c1") VALUES (%s) '
            'ON CONFLICT DO UPDATE SET "c1" = (("EXCLUDED"."c1" + %s))')
        self.assertEqual(tuple(query.params), (1, 2))
