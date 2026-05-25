# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from sql import For, Table


class TestFor(unittest.TestCase):
    def test_for(self):
        for_ = For('UPDATE', Table('t1'), Table('t2'), nowait=True)
        self.assertEqual(str(for_), 'FOR UPDATE OF "t1", "t2" NOWAIT')

    def test_for_single_table(self):
        for_ = For('UPDATE')
        for_.tables = Table('t1')
        self.assertEqual(str(for_), 'FOR UPDATE OF "t1"')
