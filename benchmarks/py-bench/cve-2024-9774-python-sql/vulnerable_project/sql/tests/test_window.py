# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Table, Window


class TestWindow(unittest.TestCase):

    def test_window(self):
        t = Table('t')
        window = Window([t.c1, t.c2])

        self.assertEqual(str(window), 'PARTITION BY "c1", "c2"')
        self.assertEqual(window.params, ())

    def test_window_order(self):
        t = Table('t')
        window = Window([t.c], order_by=t.c)

        self.assertEqual(str(window), 'PARTITION BY "c" ORDER BY "c"')
        self.assertEqual(window.params, ())

    def test_window_range(self):
        t = Table('t')
        window = Window([t.c], frame='RANGE')

        self.assertEqual(str(window),
            'PARTITION BY "c" RANGE '
            'BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW')
        self.assertEqual(window.params, ())

        window.start = -1
        self.assertEqual(str(window),
            'PARTITION BY "c" RANGE '
            'BETWEEN %s PRECEDING AND CURRENT ROW')
        self.assertEqual(window.params, (1,))

        window.start = 0
        window.end = 1
        self.assertEqual(str(window),
            'PARTITION BY "c" RANGE '
            'BETWEEN CURRENT ROW AND %s FOLLOWING')
        self.assertEqual(window.params, (1,))

        window.start = 1
        window.end = None
        self.assertEqual(str(window),
            'PARTITION BY "c" RANGE '
            'BETWEEN %s FOLLOWING AND UNBOUNDED FOLLOWING')
        self.assertEqual(window.params, (1,))

    def test_window_exclude(self):
        t = Table('t')
        window = Window([t.c], exclude='TIES')

        self.assertEqual(str(window),
            'PARTITION BY "c" EXCLUDE TIES')
        self.assertEqual(window.params, ())

    def test_window_rows(self):
        t = Table('t')
        window = Window([t.c], frame='ROWS')

        self.assertEqual(str(window),
            'PARTITION BY "c" ROWS '
            'BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW')
        self.assertEqual(window.params, ())

    def test_window_groups(self):
        t = Table('t')
        window = Window([t.c], frame='GROUPS')

        self.assertEqual(str(window),
            'PARTITION BY "c" GROUPS '
            'BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW')
        self.assertEqual(window.params, ())
