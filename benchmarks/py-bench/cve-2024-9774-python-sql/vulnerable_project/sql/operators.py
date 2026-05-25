# This file is part of python-sql.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import warnings
from array import array

from sql import CombiningQuery, Expression, Flavor, Null, Select

__all__ = ['And', 'Or', 'Not', 'Less', 'Greater', 'LessEqual', 'GreaterEqual',
    'Equal', 'NotEqual', 'Between', 'NotBetween', 'IsDistinct',
    'IsNotDistinct', 'Is', 'IsNot', 'Add', 'Sub', 'Mul', 'Div', 'FloorDiv',
    'Mod', 'Pow', 'SquareRoot', 'CubeRoot', 'Factorial', 'Abs', 'BAnd', 'BOr',
    'BXor', 'BNot', 'LShift', 'RShift', 'Concat', 'Like', 'NotLike', 'ILike',
    'NotILike', 'In', 'NotIn', 'Exists', 'Any', 'Some', 'All']


class Operator(Expression):
    __slots__ = ()

    @property
    def table(self):
        return ''

    @property
    def name(self):
        return ''

    @property
    def _operands(self):
        return ()

    @property
    def params(self):

        def convert(operands):
            params = []
            for operand in operands:
                if isinstance(operand, (Expression, Select, CombiningQuery)):
                    params.extend(operand.params)
                elif isinstance(operand, (list, tuple)):
                    params.extend(convert(operand))
                elif isinstance(operand, array):
                    params.extend(operand)
                else:
                    params.append(operand)
            return params
        return tuple(convert(self._operands))

    def _format(self, operand, param=None):
        if param is None:
            param = Flavor.get().param
        if isinstance(operand, Expression):
            return str(operand)
        elif isinstance(operand, (Select, CombiningQuery)):
            return '(%s)' % operand
        elif isinstance(operand, (list, tuple)):
            return '(' + ', '.join(self._format(o, param)
                for o in operand) + ')'
        elif isinstance(operand, array):
            return '(' + ', '.join((param,) * len(operand)) + ')'
        else:
            return param

    def __str__(self):
        raise NotImplementedError

    def __and__(self, other):
        if isinstance(other, And):
            return And([self] + other)
        else:
            return And((self, other))

    def __or__(self, other):
        if isinstance(other, Or):
            return Or([self] + other)
        else:
            return Or((self, other))


class UnaryOperator(Operator):
    __slots__ = 'operand'
    _operator = ''

    def __init__(self, operand):
        self.operand = operand

    @property
    def _operands(self):
        return (self.operand,)

    def __str__(self):
        return '(%s %s)' % (self._operator, self._format(self.operand))


class BinaryOperator(Operator):
    __slots__ = ('left', 'right')
    _operator = ''

    def __init__(self, left, right):
        self.left = left
        self.right = right

    @property
    def _operands(self):
        return (self.left, self.right)

    def __str__(self):
        left, right = self._operands
        return '(%s %s %s)' % (self._format(left), self._operator,
            self._format(right))

    def __invert__(self):
        return _INVERT[self.__class__](self.left, self.right)


class NaryOperator(list, Operator):
    __slots__ = ()
    _operator = ''

    @property
    def _operands(self):
        return self

    def __str__(self):
        return '(' + (' %s ' % self._operator).join(map(str, self)) + ')'


class And(NaryOperator):
    __slots__ = ()
    _operator = 'AND'


class Or(NaryOperator):
    __slots__ = ()
    _operator = 'OR'


class Not(UnaryOperator):
    __slots__ = ()
    _operator = 'NOT'


class Neg(UnaryOperator):
    __slots__ = ()
    _operator = '-'


class Pos(UnaryOperator):
    __slots__ = ()
    _operator = '+'


class Less(BinaryOperator):
    __slots__ = ()
    _operator = '<'


class Greater(BinaryOperator):
    __slots__ = ()
    _operator = '>'


class LessEqual(BinaryOperator):
    __slots__ = ()
    _operator = '<='


class GreaterEqual(BinaryOperator):
    __slots__ = ()
    _operator = '>='


class Equal(BinaryOperator):
    __slots__ = ()
    _operator = '='

    @property
    def _operands(self):
        if self.left is Null:
            return (self.right,)
        elif self.right is Null:
            return (self.left,)
        return super(Equal, self)._operands

    def __str__(self):
        if self.left is Null:
            return '(%s IS NULL)' % self.right
        elif self.right is Null:
            return '(%s IS NULL)' % self.left
        return super(Equal, self).__str__()


class NotEqual(Equal):
    __slots__ = ()
    _operator = '!='

    def __str__(self):
        if self.left is Null:
            return '(%s IS NOT NULL)' % self.right
        elif self.right is Null:
            return '(%s IS NOT NULL)' % self.left
        return super(Equal, self).__str__()


class Between(Operator):
    __slots__ = ('operand', 'left', 'right', 'symmetric')
    _operator = 'BETWEEN'

    def __init__(self, operand, left, right, symmetric=False):
        self.operand = operand
        self.left = left
        self.right = right
        self.symmetric = symmetric

    @property
    def _operands(self):
        return (self.operand, self.left, self.right)

    def __str__(self):
        operator = self._operator
        if self.symmetric:
            operator += ' SYMMETRIC'
        return '(%s %s %s AND %s)' % (
            self._format(self.operand), operator,
            self._format(self.left), self._format(self.right))

    def __invert__(self):
        return _INVERT[self.__class__](
            self.operand, self.left, self.right, self.symmetric)


class NotBetween(Between):
    __slots__ = ()
    _operator = 'NOT BETWEEN'


class IsDistinct(BinaryOperator):
    __slots__ = ()
    _operator = 'IS DISTINCT FROM'


class IsNotDistinct(IsDistinct):
    __slots__ = ()
    _operator = 'IS NOT DISTINCT FROM'


class Is(BinaryOperator):
    __slots__ = ()
    _operator = 'IS'

    def __init__(self, left, right):
        assert right in [None, True, False]
        super(Is, self).__init__(left, right)

    @property
    def _operands(self):
        return (self.left,)

    def __str__(self):
        if self.right is None:
            return '(%s %s UNKNOWN)' % (
                self._format(self.left), self._operator)
        elif self.right is True:
            return '(%s %s TRUE)' % (self._format(self.left), self._operator)
        elif self.right is False:
            return '(%s %s FALSE)' % (self._format(self.left), self._operator)


class IsNot(Is):
    __slots__ = ()
    _operator = 'IS NOT'


class Add(BinaryOperator):
    __slots__ = ()
    _operator = '+'


class Sub(BinaryOperator):
    __slots__ = ()
    _operator = '-'


class Mul(BinaryOperator):
    __slots__ = ()
    _operator = '*'


class Div(BinaryOperator):
    __slots__ = ()
    _operator = '/'


# For backward compatibility
class FloorDiv(BinaryOperator):
    __slots__ = ()
    _operator = '/'

    def __init__(self, left, right):
        warnings.warn('FloorDiv operator is deprecated, use Div function',
            DeprecationWarning, stacklevel=2)
        super(FloorDiv, self).__init__(left, right)


class Mod(BinaryOperator):
    __slots__ = ()

    @property
    def _operator(self):
        # '%' must be escaped with format paramstyle
        if Flavor.get().paramstyle == 'format':
            return '%%'
        else:
            return '%'


class Pow(BinaryOperator):
    __slots__ = ()
    _operator = '^'


class SquareRoot(UnaryOperator):
    __slots__ = ()
    _operator = '|/'


class CubeRoot(UnaryOperator):
    __slots__ = ()
    _operator = '||/'


class Factorial(UnaryOperator):
    __slots__ = ()
    _operator = '!!'


class Abs(UnaryOperator):
    __slots__ = ()
    _operator = '@'


class BAnd(BinaryOperator):
    __slots__ = ()
    _operator = '&'


class BOr(BinaryOperator):
    __slots__ = ()
    _operator = '|'


class BXor(BinaryOperator):
    __slots__ = ()
    _operator = '#'


class BNot(UnaryOperator):
    __slots__ = ()
    _operator = '~'


class LShift(BinaryOperator):
    __slots__ = ()
    _operator = '<<'


class RShift(BinaryOperator):
    __slots__ = ()
    _operator = '>>'


class Concat(BinaryOperator):
    __slots__ = ()
    _operator = '||'


class Like(BinaryOperator):
    __slots__ = 'escape'
    _operator = 'LIKE'

    def __init__(self, left, right, escape=None):
        super().__init__(left, right)
        assert not escape or len(escape) == 1
        self.escape = escape

    @property
    def params(self):
        params = super().params
        if self.escape or Flavor().get().escape_empty:
            params += (self.escape or '',)
        return params

    def __str__(self):
        left, right = self._operands
        if self.escape or Flavor().get().escape_empty:
            return '(%s %s %s ESCAPE %s)' % (
                self._format(left), self._operator, self._format(right),
                self._format(self.escape or ''))
        else:
            return '(%s %s %s)' % (
                self._format(left), self._operator, self._format(right))

    def __invert__(self):
        return _INVERT[self.__class__](self.left, self.right, self.escape)


class NotLike(Like):
    __slots__ = ()
    _operator = 'NOT LIKE'


class ILike(Like):
    __slots__ = ()

    @property
    def _operator(self):
        if Flavor.get().ilike:
            return 'ILIKE'
        else:
            return 'LIKE'

    @property
    def _operands(self):
        operands = super(ILike, self)._operands
        if not Flavor.get().ilike:
            from .functions import Upper
            operands = tuple(Upper(o) for o in operands)
        return operands


class NotILike(ILike):
    __slots__ = ()

    @property
    def _operator(self):
        if Flavor.get().ilike:
            return 'NOT ILIKE'
        else:
            return 'NOT LIKE'

# TODO SIMILAR


class In(BinaryOperator):
    __slots__ = ()
    _operator = 'IN'


class NotIn(BinaryOperator):
    __slots__ = ()
    _operator = 'NOT IN'


class Exists(UnaryOperator):
    __slots__ = ()
    _operator = 'EXISTS'


class Any(UnaryOperator):
    __slots__ = ()
    _operator = 'ANY'


Some = Any


class All(UnaryOperator):
    __slots__ = ()
    _operator = 'ALL'


_INVERT = {
    Less: GreaterEqual,
    Greater: LessEqual,
    LessEqual: Greater,
    GreaterEqual: Less,
    Equal: NotEqual,
    NotEqual: Equal,
    Between: NotBetween,
    NotBetween: Between,
    IsDistinct: IsNotDistinct,
    IsNotDistinct: IsDistinct,
    Is: IsNot,
    IsNot: Is,
    Like: NotLike,
    NotLike: Like,
    ILike: NotILike,
    NotILike: ILike,
    In: NotIn,
    NotIn: In,
    }
