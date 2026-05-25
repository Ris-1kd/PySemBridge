# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import unittest

from sql import (
    Matched, MatchedDelete, MatchedUpdate, NotMatched, NotMatchedInsert, Table,
    With)


class TestMerge(unittest.TestCase):
    target = Table('t')
    source = Table('s')

    def test_merge(self):
        query = self.target.merge(
            self.source, self.target.c1 == self.source.c2, Matched())
        self.assertEqual(
            str(query),
            'MERGE INTO "t" AS "a" USING "s" AS "b" '
            'ON ("a"."c1" = "b"."c2") '
            'WHEN MATCHED THEN DO NOTHING')
        self.assertEqual(query.params, ())

    def test_condition(self):
        query = self.target.merge(
            self.source,
            (self.target.c1 == self.source.c2) & (self.target.c3 == 42),
            Matched())
        self.assertEqual(
            str(query),
            'MERGE INTO "t" AS "a" USING "s" AS "b" '
            'ON (("a"."c1" = "b"."c2") AND ("a"."c3" = %s)) '
            'WHEN MATCHED THEN DO NOTHING')
        self.assertEqual(query.params, (42,))

    def test_matched(self):
        query = self.target.merge(
            self.source, self.target.c1 == self.source.c2,
            Matched((self.source.c3 == 42)
                & (self.target.c4 == self.source.c5)))
        self.assertEqual(
            str(query),
            'MERGE INTO "t" AS "a" USING "s" AS "b" '
            'ON ("a"."c1" = "b"."c2") '
            'WHEN MATCHED '
            'AND (("b"."c3" = %s) AND ("a"."c4" = "b"."c5")) '
            'THEN DO NOTHING')
        self.assertEqual(query.params, (42,))

    def test_matched_update(self):
        query = self.target.merge(
            self.source, self.target.c1 == self.source.c2,
            MatchedUpdate([self.target.c1], [self.target.c1 + self.source.c2]))
        self.assertEqual(
            str(query),
            'MERGE INTO "t" AS "a" USING "s" AS "b" '
            'ON ("a"."c1" = "b"."c2") '
            'WHEN MATCHED THEN '
            'UPDATE SET "c1" = ("a"."c1" + "b"."c2")')
        self.assertEqual(query.params, ())

    def test_matched_delete(self):
        query = self.target.merge(
            self.source, self.target.c1 == self.source.c2, MatchedDelete())
        self.assertEqual(
            str(query),
            'MERGE INTO "t" AS "a" USING "s" AS "b" '
            'ON ("a"."c1" = "b"."c2") '
            'WHEN MATCHED THEN DELETE')
        self.assertEqual(query.params, ())

    def test_not_matched(self):
        query = self.target.merge(
            self.source, self.target.c1 == self.source.c2, NotMatched())
        self.assertEqual(
            str(query),
            'MERGE INTO "t" AS "a" USING "s" AS "b" '
            'ON ("a"."c1" = "b"."c2") '
            'WHEN NOT MATCHED THEN DO NOTHING')
        self.assertEqual(query.params, ())

    def test_not_matched_insert(self):
        query = self.target.merge(
            self.source, self.target.c1 == self.source.c2,
            NotMatchedInsert(
                [self.target.c1, self.target.c2],
                [self.source.c3, self.source.c4]))
        self.assertEqual(
            str(query),
            'MERGE INTO "t" AS "a" USING "s" AS "b" '
            'ON ("a"."c1" = "b"."c2") '
            'WHEN NOT MATCHED THEN '
            'INSERT ("c1", "c2") VALUES ("b"."c3", "b"."c4")')
        self.assertEqual(query.params, ())

    def test_with(self):
        t1 = Table('t1')
        w = With(query=t1.select(where=t1.c2 == 42))
        source = w.select()

        query = self.target.merge(
            source, self.target.c1 == source.c2, Matched(), with_=[w])
        self.assertEqual(
            str(query),
            'WITH "a" AS (SELECT * FROM "t1" AS "d" WHERE ("d"."c2" = %s)) '
            'MERGE INTO "t" AS "b" '
            'USING (SELECT * FROM "a" AS "a") AS "c" '
            'ON ("b"."c1" = "c"."c2") '
            'WHEN MATCHED THEN DO NOTHING')
        self.assertEqual(query.params, (42,))
