# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import doctest
import os

import sql

here = os.path.dirname(__file__)
readme = os.path.normpath(os.path.join(here, '..', '..', 'README'))


def load_tests(loader, tests, pattern):
    tests.addTests(loader.discover(start_dir=here, pattern=pattern))
    for mod in (sql,):
        tests.addTest(doctest.DocTestSuite(mod))
    if os.path.isfile(readme):
        tests.addTest(doctest.DocFileSuite(
                readme, module_relative=False,
                tearDown=lambda t: sql.Flavor.set(sql.Flavor())))
    return tests
