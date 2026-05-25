# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import warnings
from array import array

from sql import Flavor, Literal, Null, Table
from sql.operators import (
    Abs, And, Between, Div, Equal, Exists, FloorDiv, Greater, GreaterEqual,
    ILike, In, Is, IsDistinct, IsNot, IsNotDistinct, Less, LessEqual, Like,
    LShift, Mod, Mul, Neg, Not, NotBetween, NotEqual, NotILike, NotIn, NotLike,
    Or, Pos, Pow, RShift, Sub)


class TestOperators(unittest.TestCase):
    table = Table('t')

    def test_and(self):
        for and_ in [And((self.table.c1, self.table.c2)),
                self.table.c1 & self.table.c2]:
            self.assertEqual(str(and_), '("c1" AND "c2")')
            self.assertEqual(and_.params, ())

        and_ = And((Literal(True), self.table.c2))
        self.assertEqual(str(and_), '(%s AND "c2")')
        self.assertEqual(and_.params, (True,))

    def test_operator_operators(self):
        and_ = And((Literal(True), self.table.c1))
        and2 = and_ & And((Literal(True), self.table.c2))
        self.assertEqual(str(and2), '((%s AND "c1") AND %s AND "c2")')
        self.assertEqual(and2.params, (True, True))

        and3 = and_ & Literal(True)
        self.assertEqual(str(and3), '((%s AND "c1") AND %s)')
        self.assertEqual(and3.params, (True, True))

        or_ = Or((Literal(True), self.table.c1))
        or2 = or_ | Or((Literal(True), self.table.c2))
        self.assertEqual(str(or2), '((%s OR "c1") OR %s OR "c2")')
        self.assertEqual(or2.params, (True, True))

        or3 = or_ | Literal(True)
        self.assertEqual(str(or3), '((%s OR "c1") OR %s)')
        self.assertEqual(or3.params, (True, True))

    def test_operator_compat_column(self):
        and_ = And((self.table.c1, self.table.c2))
        self.assertEqual(and_.table, '')
        self.assertEqual(and_.name, '')

    def test_or(self):
        for or_ in [Or((self.table.c1, self.table.c2)),
                self.table.c1 | self.table.c2]:
            self.assertEqual(str(or_), '("c1" OR "c2")')
            self.assertEqual(or_.params, ())

    def test_not(self):
        for not_ in [Not(self.table.c), ~self.table.c]:
            self.assertEqual(str(not_), '(NOT "c")')
            self.assertEqual(not_.params, ())

        not_ = Not(Literal(False))
        self.assertEqual(str(not_), '(NOT %s)')
        self.assertEqual(not_.params, (False,))

    def test_neg(self):
        for neg in [Neg(self.table.c1), -self.table.c1]:
            self.assertEqual(str(neg), '(- "c1")')
            self.assertEqual(neg.params, ())

    def test_pos(self):
        for pos in [Pos(self.table.c1), +self.table.c1]:
            self.assertEqual(str(pos), '(+ "c1")')
            self.assertEqual(pos.params, ())

    def test_less(self):
        for less in [Less(self.table.c1, self.table.c2),
                self.table.c1 < self.table.c2,
                ~GreaterEqual(self.table.c1, self.table.c2)]:
            self.assertEqual(str(less), '("c1" < "c2")')
            self.assertEqual(less.params, ())

        less = Less(Literal(0), self.table.c2)
        self.assertEqual(str(less), '(%s < "c2")')
        self.assertEqual(less.params, (0,))

    def test_greater(self):
        for greater in [Greater(self.table.c1, self.table.c2),
                self.table.c1 > self.table.c2,
                ~LessEqual(self.table.c1, self.table.c2)]:
            self.assertEqual(str(greater), '("c1" > "c2")')
            self.assertEqual(greater.params, ())

    def test_less_equal(self):
        for less in [LessEqual(self.table.c1, self.table.c2),
                self.table.c1 <= self.table.c2,
                ~Greater(self.table.c1, self.table.c2)]:
            self.assertEqual(str(less), '("c1" <= "c2")')
            self.assertEqual(less.params, ())

    def test_greater_equal(self):
        for greater in [GreaterEqual(self.table.c1, self.table.c2),
                self.table.c1 >= self.table.c2,
                ~Less(self.table.c1, self.table.c2)]:
            self.assertEqual(str(greater), '("c1" >= "c2")')
            self.assertEqual(greater.params, ())

    def test_equal(self):
        for equal in [Equal(self.table.c1, self.table.c2),
                self.table.c1 == self.table.c2,
                ~NotEqual(self.table.c1, self.table.c2)]:
            self.assertEqual(str(equal), '("c1" = "c2")')
            self.assertEqual(equal.params, ())

        equal = Equal(Literal('foo'), Literal('bar'))
        self.assertEqual(str(equal), '(%s = %s)')
        self.assertEqual(equal.params, ('foo', 'bar'))

        equal = Equal(self.table.c1, Null)
        self.assertEqual(str(equal), '("c1" IS NULL)')
        self.assertEqual(equal.params, ())

        equal = Equal(Literal('test'), Null)
        self.assertEqual(str(equal), '(%s IS NULL)')
        self.assertEqual(equal.params, ('test',))

        equal = Equal(Null, self.table.c1)
        self.assertEqual(str(equal), '("c1" IS NULL)')
        self.assertEqual(equal.params, ())

        equal = Equal(Null, Literal('test'))
        self.assertEqual(str(equal), '(%s IS NULL)')
        self.assertEqual(equal.params, ('test',))

    def test_not_equal(self):
        for equal in [NotEqual(self.table.c1, self.table.c2),
                self.table.c1 != self.table.c2,
                ~Equal(self.table.c1, self.table.c2)]:
            self.assertEqual(str(equal), '("c1" != "c2")')
            self.assertEqual(equal.params, ())

        equal = NotEqual(self.table.c1, Null)
        self.assertEqual(str(equal), '("c1" IS NOT NULL)')
        self.assertEqual(equal.params, ())

        equal = NotEqual(Null, self.table.c1)
        self.assertEqual(str(equal), '("c1" IS NOT NULL)')
        self.assertEqual(equal.params, ())

    def test_between(self):
        for between in [Between(self.table.c1, 1, 2),
                ~NotBetween(self.table.c1, 1, 2)]:
            self.assertEqual(str(between), '("c1" BETWEEN %s AND %s)')
            self.assertEqual(between.params, (1, 2))

        between = Between(
            self.table.c1, self.table.c2, self.table.c3, symmetric=True)
        self.assertEqual(
            str(between), '("c1" BETWEEN SYMMETRIC "c2" AND "c3")')
        self.assertEqual(between.params, ())

    def test_not_between(self):
        for between in [NotBetween(self.table.c1, 1, 2),
                ~Between(self.table.c1, 1, 2)]:
            self.assertEqual(str(between), '("c1" NOT BETWEEN %s AND %s)')
            self.assertEqual(between.params, (1, 2))

        between = NotBetween(
            self.table.c1, self.table.c2, self.table.c3, symmetric=True)
        self.assertEqual(
            str(between), '("c1" NOT BETWEEN SYMMETRIC "c2" AND "c3")')
        self.assertEqual(between.params, ())

    def test_is_distinct(self):
        for distinct in [IsDistinct(self.table.c1, self.table.c2),
                ~IsNotDistinct(self.table.c1, self.table.c2)]:
            self.assertEqual(str(distinct), '("c1" IS DISTINCT FROM "c2")')
            self.assertEqual(distinct.params, ())

    def test_is_not_distinct(self):
        for distinct in [IsNotDistinct(self.table.c1, self.table.c2),
                ~IsDistinct(self.table.c1, self.table.c2)]:
            self.assertEqual(str(distinct), '("c1" IS NOT DISTINCT FROM "c2")')
            self.assertEqual(distinct.params, ())

    def test_is(self):
        for is_ in [Is(self.table.c1, None),
                ~IsNot(self.table.c1, None)]:
            self.assertEqual(str(is_), '("c1" IS UNKNOWN)')
            self.assertEqual(is_.params, ())

        for is_ in [Is(self.table.c1, True),
                ~IsNot(self.table.c1, True)]:
            self.assertEqual(str(is_), '("c1" IS TRUE)')
            self.assertEqual(is_.params, ())

        for is_ in [Is(self.table.c1, False),
                ~IsNot(self.table.c1, False)]:
            self.assertEqual(str(is_), '("c1" IS FALSE)')
            self.assertEqual(is_.params, ())

    def test_is_not(self):
        for is_ in [IsNot(self.table.c1, None),
                ~Is(self.table.c1, None)]:
            self.assertEqual(str(is_), '("c1" IS NOT UNKNOWN)')
            self.assertEqual(is_.params, ())

        for is_ in [IsNot(self.table.c1, True),
                ~Is(self.table.c1, True)]:
            self.assertEqual(str(is_), '("c1" IS NOT TRUE)')
            self.assertEqual(is_.params, ())

        for is_ in [IsNot(self.table.c1, False),
                ~Is(self.table.c1, False)]:
            self.assertEqual(str(is_), '("c1" IS NOT FALSE)')
            self.assertEqual(is_.params, ())

    def test_sub(self):
        for sub in [Sub(self.table.c1, self.table.c2),
                self.table.c1 - self.table.c2]:
            self.assertEqual(str(sub), '("c1" - "c2")')
            self.assertEqual(sub.params, ())

    def test_mul(self):
        for mul in [Mul(self.table.c1, self.table.c2),
                self.table.c1 * self.table.c2]:
            self.assertEqual(str(mul), '("c1" * "c2")')
            self.assertEqual(mul.params, ())

    def test_div(self):
        for div in [Div(self.table.c1, self.table.c2),
                self.table.c1 / self.table.c2]:
            self.assertEqual(str(div), '("c1" / "c2")')
            self.assertEqual(div.params, ())

    def test_mod(self):
        for mod in [Mod(self.table.c1, self.table.c2),
                self.table.c1 % self.table.c2]:
            self.assertEqual(str(mod), '("c1" %% "c2")')
            self.assertEqual(mod.params, ())

    def test_mod_paramstyle(self):
        flavor = Flavor(paramstyle='format')
        Flavor.set(flavor)
        try:
            mod = Mod(self.table.c1, self.table.c2)
            self.assertEqual(str(mod), '("c1" %% "c2")')
            self.assertEqual(mod.params, ())
        finally:
            Flavor.set(Flavor())

        flavor = Flavor(paramstyle='qmark')
        Flavor.set(flavor)
        try:
            mod = Mod(self.table.c1, self.table.c2)
            self.assertEqual(str(mod), '("c1" % "c2")')
            self.assertEqual(mod.params, ())
        finally:
            Flavor.set(Flavor())

    def test_pow(self):
        for pow_ in [Pow(self.table.c1, self.table.c2),
                self.table.c1 ** self.table.c2]:
            self.assertEqual(str(pow_), '("c1" ^ "c2")')
            self.assertEqual(pow_.params, ())

    def test_abs(self):
        for abs_ in [Abs(self.table.c1), abs(self.table.c1)]:
            self.assertEqual(str(abs_), '(@ "c1")')
            self.assertEqual(abs_.params, ())

    def test_lshift(self):
        for lshift in [LShift(self.table.c1, 2),
                self.table.c1 << 2]:
            self.assertEqual(str(lshift), '("c1" << %s)')
            self.assertEqual(lshift.params, (2,))

    def test_rshift(self):
        for rshift in [RShift(self.table.c1, 2),
                self.table.c1 >> 2]:
            self.assertEqual(str(rshift), '("c1" >> %s)')
            self.assertEqual(rshift.params, (2,))

    def test_like(self):
        for like in [Like(self.table.c1, 'foo'),
                self.table.c1.like('foo'),
                ~NotLike(self.table.c1, 'foo'),
                ~~Like(self.table.c1, 'foo')]:
            self.assertEqual(str(like), '("c1" LIKE %s)')
            self.assertEqual(like.params, ('foo',))

    def test_like_escape(self):
        like = Like(self.table.c1, 'foo', escape='$')
        self.assertEqual(str(like), '("c1" LIKE %s ESCAPE %s)')
        self.assertEqual(like.params, ('foo', '$'))

    def test_like_escape_empty_false(self):
        flavor = Flavor(escape_empty=False)
        Flavor.set(flavor)
        try:
            like = Like(self.table.c1, 'foo')
            self.assertEqual(str(like), '("c1" LIKE %s)')
            self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

    def test_like_escape_empty_true(self):
        flavor = Flavor(escape_empty=True)
        Flavor.set(flavor)
        try:
            like = Like(self.table.c1, 'foo')
            self.assertEqual(str(like), '("c1" LIKE %s ESCAPE %s)')
            self.assertEqual(like.params, ('foo', ''))
        finally:
            Flavor.set(Flavor())

    def test_ilike(self):
        flavor = Flavor(ilike=True)
        Flavor.set(flavor)
        try:
            for like in [ILike(self.table.c1, 'foo'),
                    self.table.c1.ilike('foo'),
                    ~NotILike(self.table.c1, 'foo')]:
                self.assertEqual(str(like), '("c1" ILIKE %s)')
                self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

        flavor = Flavor(ilike=False)
        Flavor.set(flavor)
        try:
            like = ILike(self.table.c1, 'foo')
            self.assertEqual(
                str(like), '(UPPER("c1") LIKE UPPER(%s))')
            self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

    def test_not_ilike(self):
        flavor = Flavor(ilike=True)
        Flavor.set(flavor)
        try:
            for like in [NotILike(self.table.c1, 'foo'),
                    ~self.table.c1.ilike('foo')]:
                self.assertEqual(str(like), '("c1" NOT ILIKE %s)')
                self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

        flavor = Flavor(ilike=False)
        Flavor.set(flavor)
        try:
            like = NotILike(self.table.c1, 'foo')
            self.assertEqual(
                str(like), '(UPPER("c1") NOT LIKE UPPER(%s))')
            self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

    def test_in(self):
        for in_ in [In(self.table.c1, [self.table.c2, 1, Null]),
                ~NotIn(self.table.c1, [self.table.c2, 1, Null]),
                ~~In(self.table.c1, [self.table.c2, 1, Null])]:
            self.assertEqual(str(in_), '("c1" IN ("c2", %s, %s))')
            self.assertEqual(in_.params, (1, None))

        t2 = Table('t2')
        in_ = In(self.table.c1, t2.select(t2.c2))
        self.assertEqual(str(in_),
            '("c1" IN (SELECT "a"."c2" FROM "t2" AS "a"))')
        self.assertEqual(in_.params, ())

        in_ = In(self.table.c1, t2.select(t2.c2) | t2.select(t2.c3))
        self.assertEqual(str(in_),
            '("c1" IN (SELECT "a"."c2" FROM "t2" AS "a" '
            'UNION SELECT "a"."c3" FROM "t2" AS "a"))')
        self.assertEqual(in_.params, ())

        in_ = In(self.table.c1, array('l', list(range(10))))
        self.assertEqual(str(in_),
            '("c1" IN (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s))')
        self.assertEqual(in_.params, tuple(range(10)))

    def test_exists(self):
        exists = Exists(self.table.select(self.table.c1,
                where=self.table.c1 == 1))
        self.assertEqual(str(exists),
            '(EXISTS (SELECT "a"."c1" FROM "t" AS "a" '
            'WHERE ("a"."c1" = %s)))')
        self.assertEqual(exists.params, (1,))

    def test_floordiv(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            FloorDiv(4, 2)
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[-1].category, DeprecationWarning))
            if hasattr(self, 'assertIn'):
                self.assertIn(
                    'FloorDiv operator is deprecated, use Div function',
                    str(w[-1].message))
