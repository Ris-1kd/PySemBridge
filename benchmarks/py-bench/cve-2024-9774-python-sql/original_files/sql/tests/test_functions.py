# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import AliasManager, Flavor, Table, Window
from sql.functions import (
    Abs, AtTimeZone, CurrentTime, Div, Function, FunctionKeyword,
    FunctionNotCallable, Overlay, Rank, Trim)


class TestFunctions(unittest.TestCase):
    table = Table('t')

    def test_abs(self):
        abs_ = Abs(self.table.c1)
        self.assertEqual(str(abs_), 'ABS("c1")')
        self.assertEqual(abs_.params, ())

        abs_ = Abs(-12)
        self.assertEqual(str(abs_), 'ABS(%s)')
        self.assertEqual(abs_.params, (-12,))

    def test_mapping(self):
        class MyAbs(Function):
            _function = 'MY_ABS'
            params = ('test',)

        class MyOverlay(FunctionKeyword):
            _function = 'MY_OVERLAY'
            _keywords = ('', 'PLACING', 'FROM', 'FOR')

        class MyCurrentTime(FunctionNotCallable):
            _function = 'MY_CURRENT_TIME'

        class MyTrim(Trim):
            _function = 'MY_TRIM'

        abs_ = Abs(self.table.c1)
        overlay = Overlay(self.table.c1, 'test', 2)
        current_time = CurrentTime()
        trim = Trim(' test ')
        flavor = Flavor(function_mapping={
                Abs: MyAbs,
                Overlay: MyOverlay,
                CurrentTime: MyCurrentTime,
                Trim: MyTrim,
                })
        Flavor.set(flavor)
        try:
            self.assertEqual(str(abs_), 'MY_ABS("c1")')
            self.assertEqual(abs_.params, ('test',))

            self.assertEqual(str(overlay),
                'MY_OVERLAY("c1" PLACING %s FROM %s)')
            self.assertEqual(overlay.params, ('test', 2))

            self.assertEqual(str(current_time), 'MY_CURRENT_TIME')
            self.assertEqual(current_time.params, ())

            self.assertEqual(str(trim), 'MY_TRIM(BOTH %s FROM %s)')
            self.assertEqual(trim.params, (' ', ' test ',))
        finally:
            Flavor.set(Flavor())

    def test_sql(self):
        abs_ = Abs(self.table.select(self.table.c1,
                where=self.table.c2 == 'foo'))
        self.assertEqual(str(abs_),
            'ABS((SELECT "a"."c1" FROM "t" AS "a" WHERE ("a"."c2" = %s)))')
        self.assertEqual(abs_.params, ('foo',))

    def test_overlay(self):
        overlay = Overlay(self.table.c1, 'test', 3)
        self.assertEqual(str(overlay), 'OVERLAY("c1" PLACING %s FROM %s)')
        self.assertEqual(overlay.params, ('test', 3))
        overlay = Overlay(self.table.c1, 'test', 3, 7)
        self.assertEqual(str(overlay),
            'OVERLAY("c1" PLACING %s FROM %s FOR %s)')
        self.assertEqual(overlay.params, ('test', 3, 7))

    def test_trim(self):
        trim = Trim(' test ')
        self.assertEqual(str(trim), 'TRIM(BOTH %s FROM %s)')
        self.assertEqual(trim.params, (' ', ' test ',))

        trim = Trim(self.table.c1)
        self.assertEqual(str(trim), 'TRIM(BOTH %s FROM "c1")')
        self.assertEqual(trim.params, (' ',))

    def test_at_time_zone(self):
        time_zone = AtTimeZone(self.table.c1, 'UTC')
        self.assertEqual(str(time_zone), '"c1" AT TIME ZONE %s')
        self.assertEqual(time_zone.params, ('UTC',))

    def test_at_time_zone_expression(self):
        time_zone = AtTimeZone(self.table.c1, self.table.zone)
        self.assertEqual(str(time_zone), '"c1" AT TIME ZONE "zone"')
        self.assertEqual(time_zone.params, ())

    def test_at_time_zone_sql(self):
        time_zone = AtTimeZone(self.table.c1,
            self.table.select(self.table.tz, where=self.table.c1 == 'foo'))
        self.assertEqual(str(time_zone),
            '"c1" AT TIME ZONE '
            '(SELECT "a"."tz" FROM "t" AS "a" WHERE ("a"."c1" = %s))')
        self.assertEqual(time_zone.params, ('foo',))

    def test_at_time_zone_mapping(self):
        class MyAtTimeZone(Function):
            _function = 'MY_TIMEZONE'

        time_zone = AtTimeZone(self.table.c1, 'UTC')
        flavor = Flavor(function_mapping={
                AtTimeZone: MyAtTimeZone,
                })
        Flavor.set(flavor)
        try:
            self.assertEqual(str(time_zone), 'MY_TIMEZONE("c1", %s)')
            self.assertEqual(time_zone.params, ('UTC',))
        finally:
            Flavor.set(Flavor())

    def test_div(self):
        for div in [Div(self.table.c1, self.table.c2),
                self.table.c1 // self.table.c2]:
            self.assertEqual(str(div), 'DIV("c1", "c2")')
            self.assertEqual(div.params, ())

    def test_current_time(self):
        current_time = CurrentTime()
        self.assertEqual(str(current_time), 'CURRENT_TIME')
        self.assertEqual(current_time.params, ())


class TestWindowFunction(unittest.TestCase):

    def test_window(self):
        t = Table('t')
        function = Rank(t.c, window=Window([]))

        with AliasManager():
            self.assertEqual(str(function), 'RANK("a"."c") OVER ()')
        self.assertEqual(function.params, ())

    def test_filter(self):
        t = Table('t')
        function = Rank(t.c, filter_=t.c > 0, window=Window([]))

        with AliasManager():
            self.assertEqual(str(function),
                'RANK("a"."c") FILTER (WHERE ("a"."c" > %s)) OVER ()')
        self.assertEqual(function.params, (0,))
