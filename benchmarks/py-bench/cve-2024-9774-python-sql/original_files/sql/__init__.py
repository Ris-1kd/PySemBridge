# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import numbers
import string
import warnings
from collections import defaultdict
from itertools import chain
from threading import current_thread, local

__version__ = '1.5.1'
__all__ = [
    'Flavor', 'Table', 'Values', 'Literal', 'Column', 'Grouping', 'Conflict',
    'Matched', 'MatchedUpdate', 'MatchedDelete',
    'NotMatched', 'NotMatchedInsert',
    'Rollup', 'Cube', 'Excluded', 'Join', 'Asc', 'Desc', 'NullsFirst',
    'NullsLast', 'format2numeric']


def _escape_identifier(name):
    return '"%s"' % name.replace('"', '""')


def alias(i, letters=string.ascii_lowercase):
    '''
    Generate a unique alias based on integer

    >>> [alias(n) for n in range(6)]
    ['a', 'b', 'c', 'd', 'e', 'f']
    >>> [alias(n) for n in range(26, 30)]
    ['ba', 'bb', 'bc', 'bd']
    >>> [alias(26**n) for n in range(5)]
    ['b', 'ba', 'baa', 'baaa', 'baaaa']
    '''
    s = ''
    length = len(letters)
    while True:
        r = i % length
        s = letters[r] + s
        i //= length
        if i == 0:
            break
    return s


class Flavor(object):
    '''
    Contains the flavor of SQL

    Contains:
        limitstyle - state the type of pagination
        max_limit - limit to use if there is no limit but an offset
        paramstyle - state the type of parameter marker formatting
        ilike - support ilike extension
        no_as - doesn't support AS keyword for column and table
        no_boolean - doesn't support boolean type
        null_ordering - support NULL ordering
        function_mapping - dictionary with Function to replace
        filter_ - support filter on aggregate functions
        escape_empty - support empty escape
    '''

    def __init__(self, limitstyle='limit', max_limit=None, paramstyle='format',
            ilike=False, no_as=False, no_boolean=False, null_ordering=True,
            function_mapping=None, filter_=False, escape_empty=False):
        assert limitstyle in ['fetch', 'limit', 'rownum']
        self.limitstyle = limitstyle
        self.max_limit = max_limit
        self.paramstyle = paramstyle
        self.ilike = ilike
        self.no_as = no_as
        self.no_boolean = no_boolean
        self.null_ordering = null_ordering
        self.function_mapping = function_mapping or {}
        self.filter_ = filter_
        self.escape_empty = escape_empty

    @property
    def param(self):
        if self.paramstyle == 'format':
            return '%s'
        elif self.paramstyle == 'qmark':
            return '?'

    @staticmethod
    def set(flavor):
        '''Set this thread's flavor to flavor.'''
        current_thread().__sql_flavor__ = flavor

    @staticmethod
    def get():
        '''
        Return this thread's flavor.

        If this thread does not yet have a flavor, returns a new flavor and
        sets this thread's flavor.
        '''
        try:
            return current_thread().__sql_flavor__
        except AttributeError:
            flavor = Flavor()
            current_thread().__sql_flavor__ = flavor
            return flavor


class AliasManager(object):
    '''
    Context Manager for unique alias generation
    '''
    __slots__ = ()

    local = local()
    local.alias = None
    local.nested = 0
    local.exclude = None

    def __init__(self, exclude=None):
        if exclude:
            if getattr(self.local, 'exclude', None) is None:
                self.local.exclude = []
            self.local.exclude.extend(exclude)

    @classmethod
    def __enter__(cls):
        if getattr(cls.local, 'alias', None) is None:
            cls.local.alias = defaultdict(cls.alias_factory)
            cls.local.nested = 0
        if getattr(cls.local, 'exclude', None) is None:
            cls.local.exclude = []
        cls.local.nested += 1

    @classmethod
    def __exit__(cls, type, value, traceback):
        cls.local.nested -= 1
        if not cls.local.nested:
            cls.local.alias = None
            cls.local.exclude = None

    @classmethod
    def get(cls, from_):
        if getattr(cls.local, 'alias', None) is None:
            return ''
        if from_ in cls.local.exclude:
            return ''
        return cls.local.alias[id(from_)]

    @classmethod
    def contains(cls, from_):
        if getattr(cls.local, 'alias', None) is None:
            return False
        if from_ in cls.local.exclude:
            return False
        return id(from_) in cls.local.alias

    @classmethod
    def set(cls, from_, alias):
        assert cls.local.alias.get(from_) is None
        cls.local.alias[id(from_)] = alias

    @classmethod
    def alias_factory(cls):
        i = len(cls.local.alias)
        return alias(i)


def format2numeric(query, params):
    '''
    Convert format paramstyle query to numeric paramstyle

    >>> format2numeric('SELECT * FROM table WHERE col = %s', ('foo',))
    ('SELECT * FROM table WHERE col = :0', ('foo',))
    >>> format2numeric('SELECT * FROM table WHERE col1 = %s AND col2 = %s',
    ...     ('foo', 'bar'))
    ('SELECT * FROM table WHERE col1 = :0 AND col2 = :1', ('foo', 'bar'))
    '''
    return (query % tuple(':%i' % i for i, _ in enumerate(params)), params)


class Query(object):
    __slots__ = ()

    @property
    def params(self):
        return ()

    def __iter__(self):
        yield str(self)
        yield self.params

    def __or__(self, other):
        return Union(self, other)

    def __and__(self, other):
        return Intersect(self, other)

    def __sub__(self, other):
        return Except(self, other)


class WithQuery(Query):
    __slots__ = ('_with',)

    def __init__(self, **kwargs):
        self._with = None
        self.with_ = kwargs.pop('with_', None)
        super(Query, self).__init__(**kwargs)

    @property
    def with_(self):
        return self._with

    @with_.setter
    def with_(self, value):
        if value is not None:
            if isinstance(value, With):
                value = [value]
            assert all(isinstance(w, With) for w in value)
        self._with = value

    def _with_str(self):
        if not self.with_:
            return ''
        recursive = (' RECURSIVE' if any(w.recursive for w in self.with_)
            else '')
        with_ = ('WITH%s ' % recursive
            + ', '.join(w.statement() for w in self.with_)
            + ' ')
        return with_

    def _with_params(self):
        if not self.with_:
            return ()
        params = []
        for w in self.with_:
            params.extend(w.statement_params())
        return tuple(params)


class FromItem(object):
    __slots__ = ()

    @property
    def alias(self):
        return AliasManager.get(self)

    @property
    def has_alias(self):
        return AliasManager.contains(self)

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError
        return Column(self, name)

    def __add__(self, other):
        assert isinstance(other, FromItem)
        return From((self, other))

    def select(self, *args, **kwargs):
        return From((self,)).select(*args, **kwargs)

    def join(self, right, type_='INNER', condition=None):
        return Join(self, right, type_=type_, condition=condition)

    def left_join(self, right, condition=None):
        return self.join(right, type_='LEFT', condition=condition)

    def left_outer_join(self, right, condition=None):
        return self.join(right, type_='LEFT OUTER', condition=condition)

    def right_join(self, right, condition=None):
        return self.join(right, type_='RIGHT', condition=condition)

    def right_outer_join(self, right, condition=None):
        return self.join(right, type_='RIGHT OUTER', condition=condition)

    def full_join(self, right, condition=None):
        return self.join(right, type_='FULL', condition=condition)

    def full_outer_join(self, right, condition=None):
        return self.join(right, type_='FULL OUTER', condition=condition)

    def cross_join(self, right, condition=None):
        return self.join(right, type_='CROSS', condition=condition)

    def lateral(self):
        return Lateral(self)


class Lateral(FromItem):
    __slots__ = ('_from_item',)

    def __init__(self, from_item):
        self._from_item = from_item

    def __str__(self):
        template = '%s'
        if isinstance(self._from_item, Query):
            template = '(%s)'
        return 'LATERAL ' + template % self._from_item

    def __getattr__(self, name):
        return getattr(self._from_item, name)


class With(FromItem):
    __slots__ = ('columns', 'query', 'recursive')

    def __init__(self, *columns, **kwargs):
        self.recursive = kwargs.pop('recursive', False)
        self.columns = columns
        self.query = kwargs.pop('query', None)
        super(With, self).__init__(**kwargs)

    def statement(self):
        columns = (' (%s)' % ', '.join('"%s"' % c for c in self.columns)
            if self.columns else '')
        return '"%s"%s AS (%s)' % (self.alias, columns, self.query)

    def statement_params(self):
        return self.query.params

    def __str__(self):
        return '"%s"' % self.alias

    @property
    def params(self):
        return tuple()


class SelectQuery(WithQuery):
    __slots__ = ('_order_by', '_limit', '_offset')

    def __init__(self, *args, **kwargs):
        self._order_by = None
        self._limit = None
        self._offset = None
        self.order_by = kwargs.pop('order_by', None)
        self.limit = kwargs.pop('limit', None)
        self.offset = kwargs.pop('offset', None)
        super(SelectQuery, self).__init__(*args, **kwargs)

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
    def _order_by_str(self):
        order_by = ''
        if self.order_by:
            order_by = ' ORDER BY ' + ', '.join(map(str, self.order_by))
        return order_by

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, value):
        if value is not None:
            assert isinstance(value, numbers.Integral)
        self._limit = value

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        if value is not None:
            assert isinstance(value, numbers.Integral)
        self._offset = value

    @property
    def _limit_offset_str(self):
        param = Flavor.get().param
        if Flavor.get().limitstyle == 'limit':
            offset = ''
            if self.offset:
                offset = ' OFFSET %s' % param
            limit = ''
            if self.limit is not None:
                limit = ' LIMIT %s' % param
            elif self.offset:
                max_limit = Flavor.get().max_limit
                if max_limit:
                    limit = ' LIMIT %s' % max_limit
            return limit + offset
        else:
            offset = ''
            if self.offset:
                offset = ' OFFSET (%s) ROWS' % param
            fetch = ''
            if self.limit is not None:
                fetch = ' FETCH FIRST (%s) ROWS ONLY' % param
            return offset + fetch

    @property
    def _limit_offset_params(self):
        p = []
        if Flavor.get().limitstyle == 'limit':
            if self.limit is not None:
                p.append(self.limit)
            if self.offset:
                p.append(self.offset)
        else:
            if self.offset:
                p.append(self.offset)
            if self.limit is not None:
                p.append(self.limit)
        return tuple(p)

    def as_(self, output_name):
        return As(self, output_name)


class Select(FromItem, SelectQuery):
    __slots__ = ('_columns', '_where', '_group_by', '_having', '_for_',
        'from_', '_distinct', '_distinct_on', '_windows')

    def __init__(self, columns, from_=None, where=None, group_by=None,
            having=None, for_=None, distinct=False, distinct_on=None,
            windows=None, **kwargs):
        self._distinct = False
        self._distinct_on = []
        self._columns = None
        self._where = None
        self._group_by = None
        self._having = None
        self._for_ = None
        self._windows = []
        super(Select, self).__init__(**kwargs)
        self.distinct = distinct
        self.distinct_on = distinct_on
        self.columns = columns
        self.from_ = from_
        self.where = where
        self.group_by = group_by
        self.having = having
        self.for_ = for_
        self.windows = windows

    @property
    def distinct(self):
        return bool(self._distinct or self._distinct_on)

    @distinct.setter
    def distinct(self, value):
        self._distinct = bool(value)

    @property
    def distinct_on(self):
        return self._distinct_on

    @distinct_on.setter
    def distinct_on(self, value):
        if value is not None:
            if isinstance(value, Expression):
                value = [value]
            assert all(isinstance(col, Expression) for col in value)
        self._distinct_on = value

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        assert all(isinstance(col, (Expression, SelectQuery)) for col in value)
        self._columns = tuple(value)

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._where = value

    @property
    def group_by(self):
        return self._group_by

    @group_by.setter
    def group_by(self, value):
        if value is not None:
            if isinstance(value, Expression):
                value = [value]
            assert all(isinstance(col, Expression) for col in value)
        self._group_by = value

    @property
    def having(self):
        return self._having

    @having.setter
    def having(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._having = value

    @property
    def for_(self):
        return self._for_

    @for_.setter
    def for_(self, value):
        if value is not None:
            if isinstance(value, For):
                value = [value]
            assert all(isinstance(f, For) for f in value)
        self._for_ = value

    @property
    def windows(self):
        from sql.aggregate import Aggregate
        from sql.functions import WindowFunction
        windows = set()
        if self._windows is not None:
            for window in self._windows:
                windows.add(window)
                yield window
        for column in self.columns:
            window_function = None
            if isinstance(column, (WindowFunction, Aggregate)):
                window_function = column
            elif (isinstance(column, As)
                    and isinstance(column.expression,
                        (WindowFunction, Aggregate))):
                window_function = column.expression
            if (window_function and window_function.window
                    and window_function.window not in windows):
                windows.add(window_function.window)
                yield window_function.window

    @windows.setter
    def windows(self, value):
        if value is not None:
            assert all(isinstance(w, Window) for w in value)
        self._windows = value

    @staticmethod
    def _format_column(column):
        if isinstance(column, As):
            if isinstance(column.expression, Select):
                expression = '(%s)' % column.expression
            else:
                expression = column.expression
            if Flavor.get().no_as:
                return '%s %s' % (expression, column)
            else:
                return '%s AS %s' % (expression, column)
        else:
            if isinstance(column, Select):
                return '(%s)' % column
            else:
                return str(column)

    def _rownum(self, func):
        aliases = [c.output_name if isinstance(c, As) else None
            for c in self.columns]

        def columns(table):
            if aliases and all(aliases):
                return [Column(table, alias) for alias in aliases]
            else:
                return [Column(table, '*')]

        limitselect = self.select(*columns(self))
        if self.limit is not None:
            max_row = self.limit
            if self.offset is not None:
                max_row += self.offset
            limitselect.where = _rownum <= max_row
        if self.offset is not None:
            rnum = _rownum.as_('rnum')
            limitselect.columns += (rnum,)
            offsetselect = limitselect.select(*columns(limitselect),
                where=rnum > self.offset)
            query = offsetselect
        else:
            query = limitselect

        self.limit, limit = None, self.limit
        self.offset, offset = None, self.offset
        query.for_, self.for_ = self.for_, None

        try:
            value = func(query)
        finally:
            self.limit = limit
            self.offset = offset
            self.for_ = query.for_
        return value

    def __str__(self):
        if (Flavor.get().limitstyle == 'rownum'
                and (self.limit is not None or self.offset is not None)):
            return self._rownum(str)

        with AliasManager():
            if self.from_ is not None:
                from_ = ' FROM %s' % self.from_
            else:
                from_ = ''

            # format window before expressions to set alias
            window = ', '.join(
                '"%s" AS (%s)' % (w.alias, w) for w in self.windows)
            if window:
                window = ' WINDOW ' + window

            if self.distinct:
                distinct = 'DISTINCT '
                if self.distinct_on:
                    distinct += ('ON (%s) '
                        % ', '.join(map(str, self.distinct_on)))
            else:
                distinct = ''
            if self.columns:
                columns = ', '.join(map(self._format_column, self.columns))
            else:
                columns = '*'
            where = ''
            if self.where:
                where = ' WHERE ' + str(self.where)
            group_by = ''
            if self.group_by:
                group_by = ' GROUP BY ' + ', '.join(map(str, self.group_by))
            having = ''
            if self.having:
                having = ' HAVING ' + str(self.having)
            for_ = ''
            if self.for_ is not None:
                for_ = ' ' + ' '.join(map(str, self.for_))
            return (self._with_str()
                + 'SELECT %s%s%s' % (distinct, columns, from_)
                + where + group_by + having + window + self._order_by_str
                + self._limit_offset_str + for_)

    @property
    def params(self):
        if (Flavor.get().limitstyle == 'rownum'
                and (self.limit is not None or self.offset is not None)):
            return self._rownum(lambda q: q.params)
        p = []
        with AliasManager():
            # Set alias to window function to skip their params
            for window in self.windows:
                window.alias

            p.extend(self._with_params())
            for column in chain(self.distinct_on or (), self.columns):
                if isinstance(column, As):
                    p.extend(column.expression.params)
                p.extend(column.params)
            if self.from_ is not None:
                p.extend(self.from_.params)
            if self.where:
                p.extend(self.where.params)
            if self.group_by:
                for expression in self.group_by:
                    p.extend(expression.params)
            if self.order_by:
                for expression in self.order_by:
                    p.extend(expression.params)
            if self.having:
                p.extend(self.having.params)
            for window in self.windows:
                p.extend(window.params)
            p.extend(self._limit_offset_params)
        return tuple(p)


class Insert(WithQuery):
    __slots__ = ('_table', '_columns', '_values', '_on_conflict', '_returning')

    def __init__(
            self, table, columns=None, values=None, returning=None,
            on_conflict=None, **kwargs):
        self._table = None
        self._columns = None
        self._values = None
        self._on_conflict = None
        self._returning = None
        self.table = table
        self.columns = columns
        self.values = values
        self.on_conflict = on_conflict
        self.returning = returning
        super(Insert, self).__init__(**kwargs)

    @property
    def table(self):
        return self._table

    @table.setter
    def table(self, value):
        assert isinstance(value, Table)
        self._table = value

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        if value is not None:
            assert all(isinstance(col, Column) for col in value)
            assert all(col.table == self.table for col in value)
        self._columns = value

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        if value is not None:
            assert isinstance(value, (list, Select))
        if isinstance(value, list):
            value = Values(value)
        self._values = value

    @property
    def on_conflict(self):
        return self._on_conflict

    @on_conflict.setter
    def on_conflict(self, value):
        if value is not None:
            assert isinstance(value, Conflict)
            assert value.table == self.table
        self._on_conflict = value

    @property
    def returning(self):
        return self._returning

    @returning.setter
    def returning(self, value):
        if value is not None:
            assert isinstance(value, list)
        self._returning = value

    @staticmethod
    def _format(value, param=None):
        if param is None:
            param = Flavor.get().param
        if isinstance(value, Expression):
            return str(value)
        elif isinstance(value, Select):
            return '(%s)' % value
        else:
            return param

    def __str__(self):
        columns = ''
        if self.columns:
            assert all(col.table == self.table for col in self.columns)
            # Get columns without alias
            columns = ', '.join(c.column_name for c in self.columns)
            columns = ' (' + columns + ')'
        with AliasManager():
            if isinstance(self.values, Query):
                values = ' %s' % str(self.values)
                # TODO manage DEFAULT
            elif self.values is None:
                values = ' DEFAULT VALUES'
            on_conflict = ''
            if self.on_conflict:
                on_conflict = ' %s' % self.on_conflict
            returning = ''
            if self.returning:
                returning = ' RETURNING ' + ', '.join(
                    map(self._format, self.returning))
            if on_conflict or returning:
                table = '%s AS "%s"' % (self.table, self.table.alias)
            else:
                table = str(self.table)
            return (self._with_str()
                + 'INSERT INTO %s' % table
                + columns + values + on_conflict + returning)

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        if isinstance(self.values, Query):
            p.extend(self.values.params)
        if self.on_conflict:
            p.extend(self.on_conflict.params)
        if self.returning:
            for exp in self.returning:
                p.extend(exp.params)
        return tuple(p)


class Conflict(object):
    __slots__ = (
        '_table', '_indexed_columns', '_index_where', '_columns', '_values',
        '_where')

    def __init__(
            self, table, indexed_columns=None, index_where=None,
            columns=None, values=None, where=None):
        self._table = None
        self._indexed_columns = None
        self._index_where = None
        self._columns = None
        self._values = None
        self._where = None
        self.table = table
        self.indexed_columns = indexed_columns
        self.index_where = index_where
        self.columns = columns
        self.values = values
        self.where = where

    @property
    def table(self):
        return self._table

    @table.setter
    def table(self, value):
        assert isinstance(value, Table)
        self._table = value

    @property
    def indexed_columns(self):
        return self._indexed_columns

    @indexed_columns.setter
    def indexed_columns(self, value):
        if value is not None:
            assert all(isinstance(col, Column) for col in value)
            assert all(col.table == self.table for col in value)
        self._indexed_columns = value

    @property
    def index_where(self):
        return self._index_where

    @index_where.setter
    def index_where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._index_where = value

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        if value is not None:
            assert all(isinstance(col, Column) for col in value)
            assert all(col.table == self.table for col in value)
        self._columns = value

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        if value is not None:
            assert isinstance(value, (list, Select))
        if isinstance(value, list):
            value = Values([value])
        self._values = value

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._where = value

    def __str__(self):
        indexed_columns = ''
        if self.indexed_columns:
            assert all(c.table == self.table for c in self.indexed_columns)
            # Get columns without alias
            indexed_columns = ', '.join(
                c.column_name for c in self.indexed_columns)
            indexed_columns = ' (' + indexed_columns + ')'
            if self.index_where:
                indexed_columns += ' WHERE ' + str(self.index_where)
        else:
            assert not self.index_where
        do = ''
        if not self.columns:
            assert not self.values
            assert not self.where
            do = 'NOTHING'
        else:
            assert all(c.table == self.table for c in self.columns)
            # Get columns without alias
            do = ', '.join(c.column_name for c in self.columns)
            # TODO manage DEFAULT
            values = str(self.values)
            if values.startswith('VALUES'):
                values = values[len('VALUES'):]
            else:
                values = ' (' + values + ')'
            if len(self.columns) == 1:
                # PostgreSQL would require ROW expression
                # with single column with parenthesis
                do = 'UPDATE SET ' + do + ' =' + values
            else:
                do = 'UPDATE SET (' + do + ') =' + values
            if self.where:
                do += ' WHERE %s' % self.where
        return 'ON CONFLICT' + indexed_columns + ' DO ' + do

    @property
    def params(self):
        p = []
        if self.index_where:
            p.extend(self.index_where.params)
        if self.values:
            p.extend(self.values.params)
        if self.where:
            p.extend(self.where.params)
        return p


class Update(Insert):
    __slots__ = ('_where', '_values', 'from_')

    def __init__(self, table, columns, values, from_=None, where=None,
            returning=None, **kwargs):
        super(Update, self).__init__(table, columns=columns, values=values,
            returning=returning, **kwargs)
        self._where = None
        self.from_ = From(from_) if from_ else None
        self.where = where

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        if isinstance(value, Select):
            value = [value]
        assert isinstance(value, list)
        self._values = value

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._where = value

    def __str__(self):
        assert all(col.table == self.table for col in self.columns)
        # Get columns without alias
        columns = [c.column_name for c in self.columns]

        with AliasManager():
            from_ = ''
            if self.from_:
                from_ = ' FROM %s' % str(self.from_)
            values = ', '.join('%s = %s' % (c, self._format(v))
                for c, v in zip(columns, self.values))
            where = ''
            if self.where:
                where = ' WHERE ' + str(self.where)
            returning = ''
            if self.returning:
                returning = ' RETURNING ' + ', '.join(
                    map(self._format, self.returning))
            return (self._with_str()
                + 'UPDATE %s AS "%s" SET ' % (self.table, self.table.alias)
                + values + from_ + where + returning)

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        for value in self.values:
            if isinstance(value, (Expression, Select)):
                p.extend(value.params)
            else:
                p.append(value)
        if self.from_:
            p.extend(self.from_.params)
        if self.where:
            p.extend(self.where.params)
        if self.returning:
            for exp in self.returning:
                p.extend(exp.params)
        return tuple(p)


class Delete(WithQuery):
    __slots__ = ('_table', '_where', '_returning', 'only')

    def __init__(self, table, only=False, using=None, where=None,
            returning=None, **kwargs):
        self._table = None
        self._where = None
        self._returning = None
        self.table = table
        self.only = only
        # TODO using (not standard)
        self.where = where
        self.returning = returning
        super(Delete, self).__init__(**kwargs)

    @property
    def table(self):
        return self._table

    @table.setter
    def table(self, value):
        assert isinstance(value, Table)
        self._table = value

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._where = value

    @property
    def returning(self):
        return self._returning

    @returning.setter
    def returning(self, value):
        if value is not None:
            assert isinstance(value, list)
        self._returning = value

    @staticmethod
    def _format(value, param=None):
        if param is None:
            param = Flavor.get().param
        if isinstance(value, Expression):
            return str(value)
        elif isinstance(value, Select):
            return '(%s)' % value
        else:
            return param

    def __str__(self):
        with AliasManager(exclude=[self.table]):
            only = ' ONLY' if self.only else ''
            where = ''
            if self.where:
                where = ' WHERE ' + str(self.where)
            returning = ''
            if self.returning:
                returning = ' RETURNING ' + ', '.join(
                    map(self._format, self.returning))
            return (self._with_str()
                + 'DELETE FROM%s %s' % (only, self.table)
                + where + returning)

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        if self.where:
            p.extend(self.where.params)
        if self.returning:
            for exp in self.returning:
                p.extend(exp.params)
        return tuple(p)


class Merge(WithQuery):
    __slots__ = ('_target', '_source', '_condition', '_whens')

    def __init__(self, target, source, condition, *whens, **kwargs):
        self._target = None
        self._source = None
        self._condition = None
        self._whens = None
        self.target = target
        self.source = source
        self.condition = condition
        self.whens = whens
        super().__init__(**kwargs)

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        assert isinstance(value, Table)
        self._target = value

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        assert isinstance(value, (Table, SelectQuery, Values))
        self._source = value

    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, value):
        assert isinstance(value, Expression)
        self._condition = value

    @property
    def whens(self):
        return self._whens

    @whens.setter
    def whens(self, value):
        assert all(isinstance(w, Matched) for w in value)
        self._whens = tuple(value)

    def __str__(self):
        with AliasManager():
            if isinstance(self.source, (Select, Values)):
                source = '(%s)' % self.source
            else:
                source = self.source
            if self.condition:
                condition = 'ON %s' % self.condition
            else:
                condition = ''
            return (self._with_str()
                + 'MERGE INTO %s AS "%s" ' % (self.target, self.target.alias)
                + 'USING %s AS "%s" ' % (source, self.source.alias)
                + condition + ' ' + ' '.join(map(str, self.whens)))

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        if isinstance(self.source, (SelectQuery, Values)):
            p.extend(self.source.params)
        if self.condition:
            p.extend(self.condition.params)
        for match in self.whens:
            p.extend(match.params)
        return tuple(p)


class Matched(object):
    __slots__ = ('_condition',)
    _when = 'MATCHED'

    def __init__(self, condition=None):
        self._condition = None
        self.condition = condition

    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, value):
        if value is not None:
            assert isinstance(value, Expression)
        self._condition = value

    def _then_str(self):
        return 'DO NOTHING'

    def __str__(self):
        if self.condition is not None:
            condition = ' AND ' + str(self.condition)
        else:
            condition = ''
        return 'WHEN ' + self._when + condition + ' THEN ' + self._then_str()

    @property
    def params(self):
        p = []
        if self.condition:
            p.extend(self.condition.params)
        return tuple(p)


class _MatchedValues(Matched):
    __slots__ = ('_columns', '_values')

    def __init__(self, columns, values, **kwargs):
        self._columns = columns
        self._values = values
        self.columns = columns
        self.values = values
        super().__init__(**kwargs)

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        assert all(isinstance(col, Column) for col in value)
        self._columns = value


class MatchedUpdate(_MatchedValues, Matched):
    __slots__ = ()

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        self._values = value

    def _then_str(self):
        columns = [c.column_name for c in self.columns]
        return 'UPDATE SET ' + ', '.join(
            '%s = %s' % (c, Update._format(v))
            for c, v in zip(columns, self.values))

    @property
    def params(self):
        p = list(super().params)
        for value in self.values:
            if isinstance(value, (Expression, Select)):
                p.extend(value.params)
            else:
                p.append(value)
        return tuple(p)


class MatchedDelete(Matched):
    __slots__ = ()

    def _then_str(self):
        return 'DELETE'


class NotMatched(Matched):
    __slots__ = ()
    _when = 'NOT MATCHED'


class NotMatchedInsert(_MatchedValues, NotMatched):
    __slots__ = ()

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        self._values = Values([value])

    def _then_str(self):
        columns = ', '.join(c.column_name for c in self.columns)
        columns = '(' + columns + ')'
        if self.values is None:
            values = ' DEFAULT VALUES '
        else:
            values = ' ' + str(self.values)
        return 'INSERT ' + columns + values

    @property
    def params(self):
        p = list(super().params)
        p.extend(self.values.params)
        return tuple(p)


class CombiningQuery(FromItem, SelectQuery):
    __slots__ = ('queries', 'all_')
    _operator = ''

    def __init__(self, *queries, **kwargs):
        assert all(isinstance(q, Query) for q in queries)
        self.queries = queries
        self.all_ = kwargs.pop('all_', False)
        super(CombiningQuery, self).__init__(**kwargs)

    def __str__(self):
        with AliasManager():
            operator = ' %s %s' % (self._operator, 'ALL ' if self.all_ else '')
            return (
                self._with_str()
                + operator.join(map(str, self.queries)) + self._order_by_str
                + self._limit_offset_str)

    @property
    def params(self):
        p = []
        with AliasManager():
            p.extend(self._with_params())
            for q in self.queries:
                p.extend(q.params)
            if self.order_by:
                for expression in self.order_by:
                    p.extend(expression.params)
        return tuple(p)


class Union(CombiningQuery):
    __slots__ = ()
    _operator = 'UNION'


class Intersect(CombiningQuery):
    __slots__ = ()
    _operator = 'INTERSECT'


class Interesect(Intersect):
    def __init__(self, *args, **kwargs):
        warnings.warn('Interesect query is deprecated, use Intersect',
            DeprecationWarning, stacklevel=2)
        super(Interesect, self).__init__(*args, **kwargs)


class Except(CombiningQuery):
    __slots__ = ()
    _operator = 'EXCEPT'


class Table(FromItem):
    __slots__ = ('_name', '_schema', '_database')

    def __init__(self, name, schema=None, database=None):
        super(Table, self).__init__()
        self._name = name
        self._schema = schema
        self._database = database

    def __str__(self):
        return '.'.join(map(_escape_identifier, filter(None,
                    (self._database, self._schema, self._name))))

    @property
    def params(self):
        return ()

    def insert(
            self, columns=None, values=None, returning=None, with_=None,
            on_conflict=None):
        return Insert(self, columns=columns, values=values,
            on_conflict=on_conflict, returning=returning, with_=with_)

    def update(self, columns, values, from_=None, where=None, returning=None,
            with_=None):
        return Update(self, columns=columns, values=values, from_=from_,
            where=where, returning=returning, with_=with_)

    def delete(self, only=False, using=None, where=None, returning=None,
            with_=None):
        return Delete(self, only=only, using=using, where=where,
            returning=returning, with_=with_)

    def merge(self, source, condition, *whens, with_=None):
        return Merge(self, source, condition, *whens, with_=with_)


class _Excluded(Table):
    def __init__(self):
        super().__init__('EXCLUDED')

    @property
    def alias(self):
        return 'EXCLUDED'

    @property
    def has_alias(self):
        return False


Excluded = _Excluded()


class Join(FromItem):
    __slots__ = ('_left', '_right', '_condition', '_type_')

    def __init__(self, left, right, type_='INNER', condition=None):
        super(Join, self).__init__()
        self._left, self._right = None, None
        self._condition = None
        self._type_ = None
        self.left = left
        self.right = right
        self.condition = condition
        self.type_ = type_

    @property
    def left(self):
        return self._left

    @left.setter
    def left(self, value):
        assert isinstance(value, FromItem)
        self._left = value

    @property
    def right(self):
        return self._right

    @right.setter
    def right(self, value):
        assert isinstance(value, FromItem)
        self._right = value

    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._condition = value

    @property
    def type_(self):
        return self._type_

    @type_.setter
    def type_(self, value):
        value = value.upper()
        assert value in ('INNER', 'LEFT', 'LEFT OUTER',
            'RIGHT', 'RIGHT OUTER', 'FULL', 'FULL OUTER', 'CROSS')
        self._type_ = value

    def __str__(self):
        join = '%s %s JOIN %s' % (From([self.left]), self.type_,
            From([self.right]))
        if self.condition:
            condition = ' ON %s' % self.condition
        else:
            condition = ''
        return join + condition

    @property
    def params(self):
        p = []
        for item in (self.left, self.right):
            try:
                p.extend(item.params)
            except AttributeError:
                pass
        try:
            p.extend(self.condition.params)
        except AttributeError:
            pass
        return tuple(p)

    @property
    def alias(self):
        raise AttributeError

    @property
    def has_alias(self):
        raise AttributeError

    def __getattr__(self, name):
        raise AttributeError

    def select(self, *args, **kwargs):
        return super(Join, self).select(*args, **kwargs)


class From(list):
    __slots__ = ()

    def select(self, *args, **kwargs):
        return Select(args, from_=self, **kwargs)

    def __str__(self):
        def format(from_):
            template = '%s'
            if isinstance(from_, Query):
                template = '(%s)'
            alias = getattr(from_, 'alias', None)
            # TODO column_alias
            columns_definitions = getattr(from_, 'columns_definitions',
                None)
            if Flavor.get().no_as:
                alias_template = ' "%s"'
            else:
                alias_template = ' AS "%s"'
            # XXX find a better test for __getattr__ which returns Column
            if (alias and columns_definitions
                    and not isinstance(columns_definitions, Column)):
                return (template + alias_template + ' (%s)') % (from_, alias,
                    columns_definitions)
            elif alias:
                return (template + alias_template) % (from_, alias)
            else:
                return template % from_
        return ', '.join(map(format, self))

    @property
    def params(self):
        p = []
        for from_ in self:
            p.extend(from_.params)
        return tuple(p)

    def __add__(self, other):
        assert isinstance(other, FromItem)
        assert not isinstance(other, CombiningQuery)
        return From(super(From, self).__add__([other]))


class Values(list, Query, FromItem):
    __slots__ = ()

    # TODO order, fetch

    def __str__(self):
        param = Flavor.get().param

        def format_(value):
            if isinstance(value, Expression):
                return str(value)
            else:
                return param
        return 'VALUES ' + ', '.join(
            '(%s)' % ', '.join(map(format_, v))
            for v in self)

    @property
    def params(self):
        p = []
        for values in self:
            for value in values:
                if isinstance(value, Expression):
                    p.extend(value.params)
                else:
                    p.append(value)
        return tuple(p)


class Expression(object):
    __slots__ = ()

    def __str__(self):
        raise NotImplementedError

    @property
    def params(self):
        raise NotImplementedError

    def __and__(self, other):
        from sql.operators import And
        return And((self, other))

    def __or__(self, other):
        from sql.operators import Or
        return Or((self, other))

    def __invert__(self):
        from sql.operators import Not
        return Not(self)

    def __add__(self, other):
        from sql.operators import Add
        return Add(self, other)

    def __sub__(self, other):
        from sql.operators import Sub
        return Sub(self, other)

    def __mul__(self, other):
        from sql.operators import Mul
        return Mul(self, other)

    def __div__(self, other):
        from sql.operators import Div
        return Div(self, other)

    __truediv__ = __div__

    def __floordiv__(self, other):
        from sql.functions import Div
        return Div(self, other)

    def __mod__(self, other):
        from sql.operators import Mod
        return Mod(self, other)

    def __pow__(self, other):
        from sql.operators import Pow
        return Pow(self, other)

    def __neg__(self):
        from sql.operators import Neg
        return Neg(self)

    def __pos__(self):
        from sql.operators import Pos
        return Pos(self)

    def __abs__(self):
        from sql.operators import Abs
        return Abs(self)

    def __lshift__(self, other):
        from sql.operators import LShift
        return LShift(self, other)

    def __rshift__(self, other):
        from sql.operators import RShift
        return RShift(self, other)

    def __lt__(self, other):
        from sql.operators import Less
        return Less(self, other)

    def __le__(self, other):
        from sql.operators import LessEqual
        return LessEqual(self, other)

    def __eq__(self, other):
        from sql.operators import Equal
        return Equal(self, other)

    # When overriding __eq__, __hash__ is implicitly set to None
    __hash__ = object.__hash__

    def __ne__(self, other):
        from sql.operators import NotEqual
        return NotEqual(self, other)

    def __gt__(self, other):
        from sql.operators import Greater
        return Greater(self, other)

    def __ge__(self, other):
        from sql.operators import GreaterEqual
        return GreaterEqual(self, other)

    def in_(self, values):
        from sql.operators import In
        return In(self, values)

    def like(self, test):
        from sql.operators import Like
        return Like(self, test)

    def ilike(self, test):
        from sql.operators import ILike
        return ILike(self, test)

    def as_(self, output_name):
        return As(self, output_name)

    def cast(self, typename):
        return Cast(self, typename)

    def collate(self, collation):
        return Collate(self, collation)

    @property
    def asc(self):
        return Asc(self)

    @property
    def desc(self):
        return Desc(self)

    @property
    def nulls_first(self):
        return NullsFirst(self)

    @property
    def nulls_last(self):
        return NullsLast(self)


class Literal(Expression):
    __slots__ = ('_value')

    def __init__(self, value):
        super(Literal, self).__init__()
        self._value = value

    @property
    def value(self):
        return self._value

    def __str__(self):
        flavor = Flavor.get()
        if flavor.no_boolean:
            if self._value is True:
                return '(1 = 1)'
            elif self._value is False:
                return '(1 != 1)'
        return flavor.param

    @property
    def params(self):
        if Flavor.get().no_boolean:
            if self._value is True or self._value is False:
                return ()
        return (self._value,)


Null = None


class _Rownum(Expression):

    def __str__(self):
        return 'ROWNUM'

    @property
    def params(self):
        return ()


_rownum = _Rownum()


class Column(Expression):
    __slots__ = ('_from', '_name')

    def __init__(self, from_, name):
        super(Column, self).__init__()
        self._from = from_
        self._name = name

    @property
    def table(self):
        return self._from

    @property
    def name(self):
        return self._name

    @property
    def column_name(self):
        return (
            self._name if self._name == '*'
            else _escape_identifier(self._name))

    def __str__(self):
        alias = self._from.alias
        if alias:
            return '%s.%s' % (_escape_identifier(alias), self.column_name)
        else:
            return self.column_name

    @property
    def params(self):
        return ()


class As(Expression):
    __slots__ = ('expression', 'output_name')

    def __init__(self, expression, output_name):
        super(As, self).__init__()
        self.expression = expression
        self.output_name = output_name

    def __str__(self):
        return '%s' % _escape_identifier(self.output_name)

    @property
    def params(self):
        return ()


class Cast(Expression):
    __slots__ = ('expression', 'typename')

    def __init__(self, expression, typename):
        super(Cast, self).__init__()
        self.expression = expression
        self.typename = typename

    def __str__(self):
        if isinstance(self.expression, Expression):
            value = self.expression
        else:
            value = Flavor.get().param
        return 'CAST(%s AS %s)' % (value, self.typename)

    @property
    def params(self):
        if isinstance(self.expression, Expression):
            return self.expression.params
        else:
            return (self.expression,)


class Collate(Expression):
    __slots__ = ('expression', 'collation')

    def __init__(self, expression, collation):
        super(Collate, self).__init__()
        self.expression = expression
        self.collation = collation

    def __str__(self):
        if isinstance(self.expression, Expression):
            value = self.expression
        else:
            value = Flavor.get().param
        if '"' in self.collation:
            raise ValueError("Wrong collation %s" % self.collation)
        return '%s COLLATE "%s"' % (value, self.collation)

    @property
    def params(self):
        if isinstance(self.expression, Expression):
            return self.expression.params
        else:
            return (self.expression,)


class Grouping(Expression):
    __slots__ = ('_sets',)

    def __init__(self, *sets):
        super().__init__()
        self.sets = sets

    @property
    def sets(self):
        return self._sets

    @sets.setter
    def sets(self, value):
        assert all(
            isinstance(col, Expression) for cols in value for col in cols)
        self._sets = tuple(tuple(cols) for cols in value)

    def __str__(self):
        return 'GROUPING SETS (%s)' % (
            ', '.join(
                '(%s)' % ', '.join(str(col) for col in cols)
                for cols in self.sets))

    @property
    def params(self):
        return sum((col.params for cols in self.sets for col in cols), ())


class Rollup(Expression):
    __slots__ = ('_expressions',)

    def __init__(self, *expressions):
        super().__init__()
        self.expressions = expressions

    @property
    def expressions(self):
        return self._expressions

    @expressions.setter
    def expressions(self, value):
        assert all(
            isinstance(col, Expression)
            or all(isinstance(c, Expression) for c in col)
            for col in value)
        self._expressions = tuple(value)

    def __str__(self):
        def format(col):
            if isinstance(col, Expression):
                return str(col)
            else:
                return '(%s)' % ', '.join(str(c) for c in col)
        return '%s (%s)' % (
            self.__class__.__name__.upper(),
            ', '.join(format(col) for col in self.expressions))

    @property
    def params(self):
        p = []
        for col in self.expressions:
            if isinstance(col, Expression):
                p.extend(col.params)
            else:
                for c in col:
                    p.extend(c.params)
        return tuple(p)


class Cube(Rollup):
    pass


class Window(object):
    __slots__ = (
        '_partition', '_order_by', '_frame', '_start', '_end', '_exclude')

    def __init__(self, partition, order_by=None,
            frame=None, start=None, end=0, exclude=None):
        super(Window, self).__init__()
        self._partition = None
        self._order_by = None
        self._frame = None
        self._start = None
        self._end = None
        self.partition = partition
        self.order_by = order_by
        self.frame = frame
        self.start = start
        self.end = end
        self.exclude = exclude

    @property
    def partition(self):
        return self._partition

    @partition.setter
    def partition(self, value):
        assert all(isinstance(e, Expression) for e in value)
        self._partition = value

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
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if value:
            assert value in ['RANGE', 'ROWS', 'GROUPS']
        self._frame = value

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        if value:
            assert isinstance(value, numbers.Integral)
        self._start = value

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        if value:
            assert isinstance(value, numbers.Integral)
        self._end = value

    @property
    def exclude(self):
        return self._exclude

    @exclude.setter
    def exclude(self, value):
        if value:
            assert value in ['CURRENT ROW', 'GROUP', 'TIES']
        self._exclude = value

    @property
    def alias(self):
        return AliasManager.get(self)

    @property
    def has_alias(self):
        return AliasManager.contains(self)

    def __str__(self):
        param = Flavor.get().param
        partition = ''
        if self.partition:
            partition = 'PARTITION BY ' + ', '.join(map(str, self.partition))
        order_by = ''
        if self.order_by:
            order_by = ' ORDER BY ' + ', '.join(map(str, self.order_by))

        def format(frame, direction):
            if frame is None:
                return 'UNBOUNDED %s' % direction
            elif not frame:
                return 'CURRENT ROW'
            elif frame < 0:
                return '%s PRECEDING' % param
            elif frame > 0:
                return '%s FOLLOWING' % param

        frame = ''
        if self.frame:
            start = format(self.start, 'PRECEDING')
            end = format(self.end, 'FOLLOWING')
            frame = ' %s BETWEEN %s AND %s' % (self.frame, start, end)
        exclude = ''
        if self.exclude:
            exclude = ' EXCLUDE %s' % self.exclude
        return partition + order_by + frame + exclude

    @property
    def params(self):
        p = []
        if self.partition:
            for expression in self.partition:
                p.extend(expression.params)
        if self.order_by:
            for expression in self.order_by:
                p.extend(expression.params)
        if self.frame:
            if self.start:
                p.append(abs(self.start))
            if self.end:
                p.append(abs(self.end))
        return tuple(p)


class Order(Expression):
    __slots__ = ('_expression')
    _sql = ''

    def __init__(self, expression):
        super(Order, self).__init__()
        self._expression = None
        self.expression = expression
        # TODO USING

    @property
    def expression(self):
        return self._expression

    @expression.setter
    def expression(self, value):
        assert isinstance(value, (Expression, SelectQuery))
        self._expression = value

    def __str__(self):
        if isinstance(self.expression, SelectQuery):
            return '(%s) %s' % (self.expression, self._sql)
        return '%s %s' % (self.expression, self._sql)

    @property
    def params(self):
        return self.expression.params


class Asc(Order):
    __slots__ = ()
    _sql = 'ASC'


class Desc(Order):
    __slots__ = ()
    _sql = 'DESC'


class NullOrder(Expression):
    __slots__ = ('expression')
    _sql = ''

    def __init__(self, expression):
        super(NullOrder, self).__init__()
        self.expression = expression

    def __str__(self):
        if not Flavor.get().null_ordering:
            return '%s, %s' % (self._case, self.expression)
        return '%s NULLS %s' % (self.expression, self._sql)

    @property
    def params(self):
        p = []
        if not Flavor.get().null_ordering:
            p.extend(self.expression.params)
            p.extend(self._case_values())
        p.extend(self.expression.params)
        return tuple(p)

    @property
    def _case(self):
        from .conditionals import Case
        values = self._case_values()
        if isinstance(self.expression, Order):
            expression = self.expression.expression
        else:
            expression = self.expression
        return Asc(Case((expression == Null, values[0]), else_=values[1]))

    def _case_values(self):
        raise NotImplementedError


class NullsFirst(NullOrder):
    __slots__ = ()
    _sql = 'FIRST'

    def _case_values(self):
        return (0, 1)


class NullsLast(NullOrder):
    __slots__ = ()
    _sql = 'LAST'

    def _case_values(self):
        return (1, 0)


class For(object):
    __slots__ = ('_tables', '_type_', 'nowait')

    def __init__(self, type_, *tables, **kwargs):
        self._tables = None
        self._type_ = None
        self.tables = list(tables)
        self.type_ = type_
        self.nowait = kwargs.get('nowait')

    @property
    def tables(self):
        return self._tables

    @tables.setter
    def tables(self, value):
        if not isinstance(value, list):
            value = [value]
        all(isinstance(table, Table) for table in value)
        self._tables = value

    @property
    def type_(self):
        return self._type_

    @type_.setter
    def type_(self, value):
        value = value.upper()
        assert value in ('UPDATE', 'SHARE')
        self._type_ = value

    def __str__(self):
        tables = ''
        if self.tables:
            tables = ' OF ' + ', '.join(map(str, self.tables))
        nowait = ''
        if self.nowait:
            nowait = ' NOWAIT'
        return ('FOR %s' % self.type_) + tables + nowait
