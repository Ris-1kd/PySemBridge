# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import Table


class TestTable(unittest.TestCase):

    def test_name(self):
        t = Table('mytable')
        self.assertEqual(str(t), '"mytable"')

    def test_quoted_name(self):
        t = Table('my "quoted" name')
        self.assertEqual(str(t), '"my ""quoted"" name"')

    def test_schema(self):
        t = Table('mytable', schema='myschema')
        self.assertEqual(str(t), '"myschema"."mytable"')

    def test_database(self):
        t = Table('mytable', database='mydatabase', schema='myschema')
        self.assertEqual(str(t), '"mydatabase"."myschema"."mytable"')
