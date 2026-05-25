# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import From, Lateral, Table
from sql.functions import Function


class TestLateral(unittest.TestCase):

    def test_lateral_select(self):
        t1 = Table('t1')
        t2 = Table('t2')
        lateral = Lateral(t2.select(where=t2.id == t1.t2))
        query = From([t1, lateral]).select()

        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a", LATERAL '
            '(SELECT * FROM "t2" AS "c" WHERE ("c"."id" = "a"."t2")) AS "b"')
        self.assertEqual(tuple(query.params), ())

    def test_lateral_function(self):

        class Func(Function):
            _function = 'FUNC'

        t = Table('t')
        lateral = Lateral(Func(t.a))
        query = From([t, lateral]).select()

        self.assertEqual(str(query),
            'SELECT * FROM "t" AS "a", LATERAL FUNC("a"."a") AS "b"')
        self.assertEqual(tuple(query.params), ())
