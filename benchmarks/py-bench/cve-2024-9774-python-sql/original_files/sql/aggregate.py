# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from sql import Expression, Flavor, Literal, Window

__all__ = ['Avg', 'BitAnd', 'BitOr', 'BoolAnd', 'BoolOr', 'Count', 'Every',
    'Max', 'Min', 'Stddev', 'Sum', 'Variance']
_sentinel = object()


class Aggregate(Expression):
    __slots__ = ('expression', '_distinct', '_order_by', '_within',
        '_filter', '_window')
    _sql = ''

    def __init__(self, expression, distinct=False, order_by=None, within=None,
            filter_=None, window=None):
        super(Aggregate, self).__init__()
        self.expression = expression
        self.distinct = distinct
        self.order_by = order_by
        self.within = within
        self.filter_ = filter_
        self.window = window

    @property
    def distinct(self):
        return self._distinct

    @distinct.setter
    def distinct(self, value):
        assert isinstance(value, bool)
        self._distinct = value

    @property
    def order_by(self):
        return self._order_by

    @order_by.setter
    def order_by(self, value):
        if value is not None:
            if isinstance(value, Expression):
                value = [value]
            assert all(isinstance(col, Expression) for col in value)
        self._order_by = value

    @property
    def within(self):
        return self._within

    @within.setter
    def within(self, value):
        if value is not None:
            if isinstance(value, Expression):
                value = [value]
            assert all(isinstance(col, Expression) for col in value)
        self._within = value

    @property
    def filter_(self):
        return self._filter

    @filter_.setter
    def filter_(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._filter = value

    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, value):
        if value:
            assert isinstance(value, Window)
        self._window = value

    @property
    def _case_expression(self):
        return self.expression

    def __str__(self):
        quantifier = 'DISTINCT ' if self.distinct else ''
        has_filter = Flavor.get().filter_
        expression = self.expression
        if self.filter_ and not has_filter:
            from sql.conditionals import Case
            expression = Case((self.filter_, self._case_expression))
        order_by = ''
        if self.order_by:
            order_by = ' ORDER BY %s' % ', '.join(map(str, self.order_by))
        aggregate = '%s(%s%s%s)' % (
            self._sql, quantifier, expression, order_by)
        within = ''
        if self.within:
            within = (' WITHIN GROUP (ORDER BY %s)'
                % ', '.join(map(str, self.within)))
        filter_ = ''
        if self.filter_ and has_filter:
            filter_ = ' FILTER (WHERE %s)' % self.filter_
        window = ''
        if self.window:
            if self.window.has_alias:
                window = ' OVER "%s"' % self.window.alias
            else:
                window = ' OVER (%s)' % self.window
        return aggregate + within + filter_ + window

    @property
    def params(self):
        has_filter = Flavor.get().filter_
        p = []
        if self.filter_ and not has_filter:
            p.extend(self.filter_.params)
            p.extend(self._case_expression.params)
        else:
            p.extend(self.expression.params)
        if self.order_by:
            for expression in self.order_by:
                p.extend(expression.params)
        if self.within:
            for expression in self.within:
                p.extend(expression.params)
        if self.filter_ and has_filter:
            p.extend(self.filter_.params)
        if self.window and not self.window.has_alias:
            p.extend(self.window.params)
        return tuple(p)


class Avg(Aggregate):
    __slots__ = ()
    _sql = 'AVG'


class BitAnd(Aggregate):
    __slots__ = ()
    _sql = 'BIT_AND'


class BitOr(Aggregate):
    __slots__ = ()
    _sql = 'BIT_OR'


class BoolAnd(Aggregate):
    __slots__ = ()
    _sql = 'BOOL_AND'


class BoolOr(Aggregate):
    __slots__ = ()
    _sql = 'BOOL_OR'


class Count(Aggregate):
    __slots__ = ()
    _sql = 'COUNT'

    def __init__(self, expression=_sentinel, **kwargs):
        if expression is _sentinel:
            expression = Literal('*')
        super().__init__(expression, **kwargs)

    @property
    def _case_expression(self):
        expression = super(Count, self)._case_expression
        if (isinstance(self.expression, Literal)
                and expression.value == '*'):
            expression = Literal(1)
        return expression


class Every(Aggregate):
    __slots__ = ()
    _sql = 'EVERY'


class Max(Aggregate):
    __slots__ = ()
    _sql = 'MAX'


class Min(Aggregate):
    __slots__ = ()
    _sql = 'MIN'


class Stddev(Aggregate):
    __slots__ = ()
    _sql = 'Stddev'


class Sum(Aggregate):
    __slots__ = ()
    _sql = 'SUM'


class Variance(Aggregate):
    __slots__ = ()
    _sql = 'VARIANCE'
