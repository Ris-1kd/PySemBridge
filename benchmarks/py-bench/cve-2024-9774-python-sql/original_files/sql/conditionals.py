# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from sql import CombiningQuery, Expression, Flavor, Select

__all__ = ['Case', 'Coalesce', 'NullIf', 'Greatest', 'Least']


class Conditional(Expression):
    __slots__ = ()
    _sql = ''
    table = ''
    name = ''

    @staticmethod
    def _format(value):
        if isinstance(value, Expression):
            return str(value)
        elif isinstance(value, (Select, CombiningQuery)):
            return '(%s)' % value
        else:
            return Flavor().get().param


class Case(Conditional):
    __slots__ = ('whens', 'else_')

    def __init__(self, *whens, **kwargs):
        self.whens = whens
        self.else_ = kwargs.get('else_')

    def __str__(self):
        case = 'CASE '
        for cond, result in self.whens:
            case += 'WHEN %s THEN %s ' % (
                self._format(cond), self._format(result))
        if self.else_ is not None:
            case += 'ELSE %s ' % self._format(self.else_)
        case += 'END'
        return case

    @property
    def params(self):
        p = []
        for cond, result in self.whens:
            if isinstance(cond, (Expression, Select, CombiningQuery)):
                p.extend(cond.params)
            else:
                p.append(cond)
            if isinstance(result, (Expression, Select, CombiningQuery)):
                p.extend(result.params)
            else:
                p.append(result)
        if self.else_ is not None:
            if isinstance(self.else_, (Expression, Select, CombiningQuery)):
                p.extend(self.else_.params)
            else:
                p.append(self.else_)
        return tuple(p)


class Coalesce(Conditional):
    __slots__ = ('values')
    _conditional = 'COALESCE'

    def __init__(self, *values):
        self.values = values

    def __str__(self):
        return (self._conditional
            + '(' + ', '.join(map(self._format, self.values)) + ')')

    @property
    def params(self):
        p = []
        for value in self.values:
            if isinstance(value, (Expression, Select, CombiningQuery)):
                p.extend(value.params)
            else:
                p.append(value)
        return tuple(p)


class NullIf(Coalesce):
    __slots__ = ()
    _conditional = 'NULLIF'


class Greatest(Coalesce):
    __slots__ = ()
    _conditional = 'GREATEST'


class Least(Coalesce):
    __slots__ = ()
    _conditional = 'LEAST'
