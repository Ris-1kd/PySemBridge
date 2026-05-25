# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from itertools import chain

from sql import CombiningQuery, Expression, Flavor, FromItem, Select, Window

__all__ = ['Abs', 'Cbrt', 'Ceil', 'Degrees', 'Div', 'Exp', 'Floor', 'Ln',
    'Log', 'Mod', 'Pi', 'Power', 'Radians', 'Random', 'Round', 'SetSeed',
    'Sign', 'Sqrt', 'Trunc', 'WidthBucket',
    'Acos', 'Asin', 'Atan', 'Atan2', 'Cos', 'Cot', 'Sin', 'Tan',
    'BitLength', 'CharLength', 'Overlay', 'Position', 'Substring', 'Trim',
    'Upper',
    'ToChar', 'ToDate', 'ToNumber', 'ToTimestamp',
    'Age', 'ClockTimestamp', 'CurrentDate', 'CurrentTime', 'CurrentTimestamp',
    'DatePart', 'DateTrunc', 'Extract', 'Isfinite', 'JustifyDays',
    'JustifyHours', 'JustifyInterval', 'Localtime', 'Localtimestamp', 'Now',
    'StatementTimestamp', 'Timeofday', 'TransactionTimestamp',
    'AtTimeZone',
    'RowNumber', 'Rank', 'DenseRank', 'PercentRank', 'CumeDist', 'Ntile',
    'Lag', 'Lead', 'FirstValue', 'LastValue', 'NthValue']

# Mathematical


class Function(Expression, FromItem):
    __slots__ = ('args', '_columns_definitions')
    table = ''
    name = ''
    _function = ''

    def __init__(self, *args, **kwargs):
        self.args = args
        self.columns_definitions = kwargs.get('columns_definitions', [])

    @property
    def columns_definitions(self):
        return ', '.join('"%s" %s' % (c, d)
            for c, d in self._columns_definitions)

    @columns_definitions.setter
    def columns_definitions(self, value):
        assert isinstance(value, list)
        self._columns_definitions = value

    @staticmethod
    def _format(value):
        if isinstance(value, Expression):
            return str(value)
        elif isinstance(value, (Select, CombiningQuery)):
            return '(%s)' % value
        else:
            return Flavor().get().param

    def __str__(self):
        Mapping = Flavor.get().function_mapping.get(self.__class__)
        if Mapping:
            return str(Mapping(*self.args))
        return self._function + '(' + ', '.join(
            map(self._format, self.args)) + ')'

    @property
    def params(self):
        Mapping = Flavor.get().function_mapping.get(self.__class__)
        if Mapping:
            return Mapping(*self.args).params
        p = []
        for arg in self.args:
            if isinstance(arg, (Expression, Select, CombiningQuery)):
                p.extend(arg.params)
            else:
                p.append(arg)
        return tuple(p)


class FunctionKeyword(Function):
    __slots__ = ()
    _function = ''
    _keywords = ()

    def __str__(self):
        Mapping = Flavor.get().function_mapping.get(self.__class__)
        if Mapping:
            return str(Mapping(*self.args))
        return (self._function + '('
            + ' '.join(chain(*zip(
                        self._keywords,
                        map(self._format, self.args))))[1:]
            + ')')


class FunctionNotCallable(Function):
    __slots__ = ()
    _function = ''

    def __str__(self):
        Mapping = Flavor.get().function_mapping.get(self.__class__)
        if Mapping:
            return str(Mapping(*self.args))
        return self._function


class Abs(Function):
    __slots__ = ()
    _function = 'ABS'


class Cbrt(Function):
    __slots__ = ()
    _function = 'CBRT'


class Ceil(Function):
    __slots__ = ()
    _function = 'CEIL'


class Degrees(Function):
    __slots__ = ()
    _function = 'DEGREES'


class Div(Function):
    __slots__ = ()
    _function = 'DIV'


class Exp(Function):
    __slots__ = ()
    _function = 'EXP'


class Floor(Function):
    __slots__ = ()
    _function = 'FLOOR'


class Ln(Function):
    __slots__ = ()
    _function = 'LN'


class Log(Function):
    __slots__ = ()
    _function = 'LOG'


class Mod(Function):
    __slots__ = ()
    _function = 'MOD'


class Pi(Function):
    __slots__ = ()
    _function = 'PI'


class Power(Function):
    __slots__ = ()
    _function = 'POWER'


class Radians(Function):
    __slots__ = ()
    _function = 'RADIANS'


class Random(Function):
    __slots__ = ()
    _function = 'RANDOM'


class Round(Function):
    __slots__ = ()
    _function = 'ROUND'


class SetSeed(Function):
    __slots__ = ()
    _function = 'SETSEED'


class Sign(Function):
    __slots__ = ()
    _function = 'SIGN'


class Sqrt(Function):
    __slots__ = ()
    _function = 'SQRT'


class Trunc(Function):
    __slots__ = ()
    _function = 'TRUNC'


class WidthBucket(Function):
    __slots__ = ()
    _function = 'WIDTH_BUCKET'

# Trigonometric


class Acos(Function):
    __slots__ = ()
    _function = 'ACOS'


class Asin(Function):
    __slots__ = ()
    _function = 'ASIN'


class Atan(Function):
    __slots__ = ()
    _function = 'ATAN'


class Atan2(Function):
    __slots__ = ()
    _function = 'ATAN2'


class Cos(Function):
    __slots__ = ()
    _function = 'Cos'


class Cot(Function):
    __slots__ = ()
    _function = 'COT'


class Sin(Function):
    __slots__ = ()
    _function = 'SIN'


class Tan(Function):
    __slots__ = ()
    _function = 'TAN'

# String


class BitLength(Function):
    __slots__ = ()
    _function = 'BIT_LENGTH'


class CharLength(Function):
    __slots__ = ()
    _function = 'CHAR_LENGTH'


class Lower(Function):
    __slots__ = ()
    _function = 'LOWER'


class OctetLength(Function):
    __slots__ = ()
    _function = 'OCTET_LENGTH'


class Overlay(FunctionKeyword):
    __slots__ = ()
    _function = 'OVERLAY'
    _keywords = ('', 'PLACING', 'FROM', 'FOR')


class Position(FunctionKeyword):
    __slots__ = ()
    _function = 'POSITION'
    _keywords = ('', 'IN')


class Substring(FunctionKeyword):
    __slots__ = ()
    _function = 'SUBSTRING'
    _keywords = ('', 'FROM', 'FOR')


class Trim(Function):
    __slots__ = ('position', 'characters', 'string')
    _function = 'TRIM'

    def __init__(self, string, position='BOTH', characters=' '):
        assert position.upper() in ('LEADING', 'TRAILING', 'BOTH')
        self.position = position.upper()
        self.characters = characters
        self.string = string

    def __str__(self):
        flavor = Flavor.get()
        Mapping = flavor.function_mapping.get(self.__class__)
        if Mapping:
            return str(Mapping(self.string, self.position, self.characters))
        param = flavor.param

        def format(arg):
            if isinstance(arg, str):
                return param
            else:
                return str(arg)
        return self._function + '(%s %s FROM %s)' % (
            self.position, format(self.characters), format(self.string))

    @property
    def params(self):
        Mapping = Flavor.get().function_mapping.get(self.__class__)
        if Mapping:
            return Mapping(self.string, self.position, self.characters).params
        p = []
        for arg in (self.characters, self.string):
            if isinstance(arg, str):
                p.append(arg)
            else:
                try:
                    p.extend(arg.params)
                except AttributeError:
                    pass
        return tuple(p)


class Upper(Function):
    __slots__ = ()
    _function = 'UPPER'


class ToChar(Function):
    __slots__ = ()
    _function = 'TO_CHAR'


class ToDate(Function):
    __slots__ = ()
    _function = 'TO_DATE'


class ToNumber(Function):
    __slots__ = ()
    _function = 'TO_NUMBER'


class ToTimestamp(Function):
    __slots__ = ()
    _function = 'TO_TIMESTAMP'


class Age(Function):
    __slots__ = ()
    _function = 'AGE'


class ClockTimestamp(Function):
    __slots__ = ()
    _function = 'CLOCK_TIMESTAMP'


class CurrentDate(FunctionNotCallable):
    __slots__ = ()
    _function = 'CURRENT_DATE'


class CurrentTime(FunctionNotCallable):
    __slots__ = ()
    _function = 'CURRENT_TIME'


class CurrentTimestamp(FunctionNotCallable):
    __slots__ = ()
    _function = 'CURRENT_TIMESTAMP'


class DatePart(Function):
    __slots__ = ()
    _function = 'DATE_PART'


class DateTrunc(Function):
    __slots__ = ()
    _function = 'DATE_TRUNC'


class Extract(FunctionKeyword):
    __slots__ = ()
    _function = 'EXTRACT'
    _keywords = ('', 'FROM')


class Isfinite(Function):
    __slots__ = ()
    _function = 'ISFINITE'


class JustifyDays(Function):
    __slots__ = ()
    _function = 'JUSTIFY_DAYS'


class JustifyHours(Function):
    __slots__ = ()
    _function = 'JUSTIFY_HOURS'


class JustifyInterval(Function):
    __slots__ = ()
    _function = 'JUSTIFY_INTERVAL'


class Localtime(FunctionNotCallable):
    __slots__ = ()
    _function = 'LOCALTIME'


class Localtimestamp(FunctionNotCallable):
    __slots__ = ()
    _function = 'LOCALTIMESTAMP'


class Now(Function):
    __slots__ = ()
    _function = 'NOW'


class StatementTimestamp(Function):
    __slots__ = ()
    _function = 'STATEMENT_TIMESTAMP'


class Timeofday(Function):
    __slots__ = ()
    _function = 'TIMEOFDAY'


class TransactionTimestamp(Function):
    __slots__ = ()
    _function = 'TRANSACTION_TIMESTAMP'


class AtTimeZone(Function):
    __slots__ = ('field', 'zone')

    def __init__(self, field, zone):
        self.field = field
        self.zone = zone

    def __str__(self):
        flavor = Flavor.get()
        Mapping = flavor.function_mapping.get(self.__class__)
        if Mapping:
            return str(Mapping(self.field, self.zone))
        if isinstance(self.zone, Expression):
            zone = str(self.zone)
        elif isinstance(self.zone, (Select, CombiningQuery)):
            zone = '(%s)' % self.zone
        else:
            zone = flavor.param
        return '%s AT TIME ZONE %s' % (str(self.field), zone)

    @property
    def params(self):
        Mapping = Flavor.get().function_mapping.get(self.__class__)
        if Mapping:
            return Mapping(self.field, self.zone).params
        if isinstance(self.zone, (Expression, Select, CombiningQuery)):
            return self.field.params + self.zone.params
        else:
            return self.field.params + (self.zone,)


class WindowFunction(Function):
    __slots__ = ('_filter', '_window')

    def __init__(self, *args, **kwargs):
        self.filter_ = kwargs.pop('filter_', None)
        self.window = kwargs['window']
        super(WindowFunction, self).__init__(*args, **kwargs)

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

    def __str__(self):
        function = super(WindowFunction, self).__str__()
        filter_ = ''
        if self.filter_:
            filter_ = ' FILTER (WHERE %s)' % self.filter_
        if self.window.has_alias:
            over = ' OVER "%s"' % self.window.alias
        else:
            over = ' OVER (%s)' % self.window
        return function + filter_ + over

    @property
    def params(self):
        p = list(super(WindowFunction, self).params)
        if self.filter_:
            p.extend(self.filter_.params)
        if not self.window.has_alias:
            p.extend(self.window.params)
        return tuple(p)


class RowNumber(WindowFunction):
    __slots__ = ()
    _function = 'ROW_NUMBER'


class Rank(WindowFunction):
    __slots__ = ()
    _function = 'RANK'


class DenseRank(WindowFunction):
    __slots__ = ()
    _function = 'DENSE_RANK'


class PercentRank(WindowFunction):
    __slots__ = ()
    _function = 'PERCENT_RANK'


class CumeDist(WindowFunction):
    __slots__ = ()
    _function = 'CUME_DIST'


class Ntile(WindowFunction):
    __slots__ = ()
    _function = 'NTILE'


class Lag(WindowFunction):
    __slots__ = ()
    _function = 'LAG'


class Lead(WindowFunction):
    __slots__ = ()
    _function = 'LEAD'


class FirstValue(WindowFunction):
    __slots__ = ()
    _function = 'FIRST_VALUE'


class LastValue(WindowFunction):
    __slots__ = ()
    _function = 'LAST_VALUE'


class NthValue(WindowFunction):
    __slots__ = ()
    _function = 'NTH_VALUE'
