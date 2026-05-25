# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Values


class TestValues(unittest.TestCase):
    def test_single_values(self):
        values = Values([[1]])
        self.assertEqual(str(values), 'VALUES (%s)')
        self.assertEqual(values.params, (1,))

    def test_many_values(self):
        values = Values([[1, 2], [3, 4]])
        self.assertEqual(str(values), 'VALUES (%s, %s), (%s, %s)')
        self.assertEqual(values.params, (1, 2, 3, 4))

    def test_select(self):
        values = Values([[1], [2], [3]])
        query = values.select()
        self.assertEqual(str(query),
            'SELECT * FROM (VALUES (%s), (%s), (%s)) AS "a"')
        self.assertEqual(tuple(query.params), (1, 2, 3))

    def test_union(self):
        values = Values([[1]])
        values |= Values([[2]])
        self.assertEqual(str(values), 'VALUES (%s) UNION VALUES (%s)')
        self.assertEqual(values.params, (1, 2))
