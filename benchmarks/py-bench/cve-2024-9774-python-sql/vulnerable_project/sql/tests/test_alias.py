# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import threading
import unittest

from sql import AliasManager, Table


class TestAliasManager(unittest.TestCase):

    def setUp(self):
        self.synchro = threading.Event()
        self.succeed1 = threading.Event()
        self.succeed2 = threading.Event()
        self.finish1 = threading.Event()
        self.finish2 = threading.Event()

        self.t1 = Table('t1')
        self.t2 = Table('t2')

    def func1(self):
        try:
            with AliasManager(exclude=[self.t2]):
                a1 = AliasManager.get(self.t1)
                a2 = AliasManager.get(self.t2)
                self.synchro.wait()
                self.assertEqual(a1, AliasManager.get(self.t1))
                self.assertEqual(a2, AliasManager.get(self.t2))
                self.succeed1.set()
            return
        except Exception:
            pass
        finally:
            self.finish1.set()

    def func2(self):
        try:
            with AliasManager(exclude=[self.t2]):
                a2 = AliasManager.get(self.t2)
                a1 = AliasManager.get(self.t1)
                self.synchro.set()
                self.assertEqual(a1, AliasManager.get(self.t1))
                self.assertEqual(a2, AliasManager.get(self.t2))
                self.succeed2.set()
            return
        except Exception:
            pass
        finally:
            self.synchro.set()
            self.finish2.set()

    def test_threading(self):

        th1 = threading.Thread(target=self.func1)
        th2 = threading.Thread(target=self.func2)

        th1.start()
        th2.start()

        self.finish1.wait()
        self.finish2.wait()
        if not self.succeed1.is_set() or not self.succeed2.is_set():
            self.fail()
