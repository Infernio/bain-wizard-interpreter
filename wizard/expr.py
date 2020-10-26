# -*- encoding: utf-8 -*-

from abc import abstractproperty
from enum import Enum, auto
from typing import (
    Callable,
    List,
    Iterator,
    Iterable,
    Mapping,
    MutableMapping,
    Type,
    Union,
)

from wizard.antlr4.wizardParser import wizardParser

from .errors import (
    WizardTypeError,
    WizardIndexError,
    WizardNameError,
    WizardUnsupportedOperation,
)


class Void:

    """
    Simple class representing the result of a function call without a return
    value.
    """

    pass


class SubPackage(str):
    def __new__(cls, *args, **kwargs):
        return str.__new__(cls, *args, **kwargs)

    @abstractproperty
    def files(self) -> Iterable[str]:
        pass


class SubPackages(List[SubPackage]):

    """
    Class to wrap the 'SubPackages' variable.
    """

    def __init__(self, subpackages: List[SubPackage]):
        super().__init__(subpackages)


class VariableType(Enum):

    BOOL = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()

    VOID = auto()

    # Note: This is used only for SubPackages and item in SubPackages.
    LIST_SUBPACKAGES = auto()
    SUBPACKAGE = auto()

    @staticmethod
    def from_pytype(pytype: Type) -> "VariableType":
        if pytype is Void:
            return VariableType.VOID
        if issubclass(pytype, SubPackages):
            return VariableType.LIST_SUBPACKAGES
        if issubclass(pytype, SubPackage):
            return VariableType.SUBPACKAGE
        if pytype is bool:
            return VariableType.BOOL
        if pytype is int:
            return VariableType.INTEGER
        if pytype is float:
            return VariableType.FLOAT
        if pytype is str:
            return VariableType.STRING
        raise ValueError(f"Unknow type: {pytype}.")

    def __str__(self) -> str:
        if self is VariableType.LIST_SUBPACKAGES:
            return "SubPackage[]"

        if self is VariableType.SUBPACKAGE:
            return "SubPackage"

        return super().__str__().lower().split(".")[-1]


# Union of possible type for Wizard value:
WizardValueType = Union[bool, int, float, str, SubPackage, SubPackages]


class Value:

    """
    Represent a value of a given type, that can be a constant or the reuslt of
    a complex expression.

    Value expose operators from the BAIN Wizard specification with proper type
    checking so you can use them directly.
    """

    _value: WizardValueType

    def __init__(self, value: WizardValueType):
        self._type = VariableType.from_pytype(type(value))
        self._value = value

    @property
    def type(self) -> VariableType:
        """
        Returns:
            The type of the variable.
        """
        return self._type

    def is_void(self) -> bool:
        """
        Returns:
            True if this value represent the "void" value.
        """
        return self._type == VariableType.VOID

    @property
    def value(self) -> WizardValueType:
        """
        Returns:
            The value of this constant.
        """
        return self._value

    def __pos__(self) -> "Value":
        if not isinstance(self._value, (int, float)):
            raise WizardTypeError(
                f"Cannot use plus operator on variable of type {self._type}."
            )
        return Value(self._value)

    def __neg__(self) -> "Value":
        if not isinstance(self._value, (int, float)):
            raise WizardTypeError(
                f"Cannot use minus operator on variable of type {self._type}."
            )
        return Value(-self._value)

    def __add__(self, other: "Value") -> "Value":
        if (
            not isinstance(self._value, (int, float, str))
            or not isinstance(other._value, (int, float, str))
            or isinstance(self._value, str) != isinstance(other._value, str)
        ):
            raise WizardTypeError(
                f"Cannot add values of types {self._type}, {other._type}."
            )
        return Value(self._value + other._value)  # type: ignore

    def __sub__(self, other: "Value") -> "Value":
        if not isinstance(self._value, (int, float)) or not isinstance(
            other._value, (int, float)
        ):
            raise WizardTypeError("Cannot substract non-numeric values.")
        return Value(self._value - other._value)

    def __mul__(self, other: "Value") -> "Value":
        if not isinstance(self._value, (int, float)) or not isinstance(
            other._value, (int, float)
        ):
            raise WizardTypeError("Cannot multiply non-numeric values.")
        return Value(self._value * other._value)

    def __div__(self, other: "Value") -> "Value":
        if not isinstance(self._value, (int, float)) or not isinstance(
            other._value, (int, float)
        ):
            raise WizardTypeError("Cannot divide non-numeric values.")
        return Value(self._value / other._value)

    def __pow__(self, other: "Value") -> "Value":
        if not isinstance(self._value, (int, float)) or not isinstance(
            other._value, (int, float)
        ):
            raise WizardTypeError("Cannot raise non-numeric values.")
        return Value(self._value ** other._value)

    def __mod__(self, other: "Value") -> "Value":
        if not isinstance(self._value, (int, float)) or not isinstance(
            other._value, (int, float)
        ):
            raise WizardTypeError("Cannot modulo non-numeric values.")
        return Value(self._value % other._value)

    def logical_not(self) -> "Value":
        return Value(not self._value)

    def equals(self, other: "Value") -> "Value":
        return Value(self._value == other._value)

    def not_equals(self, other: "Value") -> "Value":
        return Value(self._value != other._value)

    def __or__(self, other: "Value") -> "Value":
        return Value(self._value or other._value)

    def __and__(self, other: "Value") -> "Value":
        return Value(self._value and other._value)

    def __gt__(self, other: "Value") -> "Value":
        if isinstance(self._value, (int, float)) and isinstance(
            other._value, (int, float)
        ):
            return Value(self._value > other._value)
        if isinstance(self._value, str) and isinstance(other._value, str):
            return Value(self._value > other._value)
        raise WizardTypeError(
            f"Cannot compare values of types {self._type}, {other._type}."
        )

    def __ge__(self, other: "Value") -> "Value":
        if isinstance(self._value, (int, float)) and isinstance(
            other._value, (int, float)
        ):
            return Value(self._value >= other._value)
        if isinstance(self._value, str) and isinstance(other._value, str):
            return Value(self._value >= other._value)
        raise WizardTypeError(
            f"Cannot compare values of types {self._type}, {other._type}."
        )

    def __lt__(self, other: "Value") -> "Value":
        if isinstance(self._value, (int, float)) and isinstance(
            other._value, (int, float)
        ):
            return Value(self._value < other._value)
        if isinstance(self._value, str) and isinstance(other._value, str):
            return Value(self._value < other._value)
        raise WizardTypeError(
            f"Cannot compare values of types {self._type}, {other._type}."
        )

    def __le__(self, other: "Value") -> "Value":
        if isinstance(self._value, (int, float)) and isinstance(
            other._value, (int, float)
        ):
            return Value(self._value <= other._value)
        if isinstance(self._value, str) and isinstance(other._value, str):
            return Value(self._value <= other._value)
        raise WizardTypeError(
            f"Cannot compare values of types {self._type}, {other._type}."
        )

    def contains(self, item: "Value", case_insensitive: bool = False) -> "Value":
        if not isinstance(self._value, (SubPackage, SubPackages)):
            raise WizardTypeError(f"Cannot iterate variable of type {self._type}.")

        if not isinstance(item._value, (str, SubPackage)):
            raise WizardTypeError(
                f"Cannot check presence of variable of type {self._type}."
            )

        if case_insensitive:
            item = Value(item._value.lower())

        it: Iterable[str]
        if isinstance(self._value, SubPackages):
            it = iter(self._value)
        else:
            it = self._value.files

        for istr in it:
            if case_insensitive:
                istr = istr.lower()
            if item._value == istr:
                return Value(True)

        return Value(False)

    def __getitem__(self, index: "Value") -> "Value":
        if not isinstance(self._value, (SubPackage, SubPackages)):
            raise WizardTypeError(f"Cannot index variable of type {self._type}.")
        if not isinstance(index._value, (int)):
            raise WizardTypeError(f"Cannot index with variable of type {index._type}.")

        try:
            return Value(self._value[index._value])
        except IndexError:
            raise WizardIndexError(index._value)

    def __iter__(self) -> Iterable["Value"]:
        if not isinstance(self._value, (SubPackage, SubPackages)):
            raise WizardTypeError(f"Cannot iterate variable of type {self._type}.")

        it: Iterable[str]
        if isinstance(self._value, SubPackages):
            it = iter(self._value)
        else:
            it = self._value.files

        return (Value(x) for x in it)

    # Those operations are not "Wizardly", i.e. they make sense in Python:

    def __eq__(self, other: object) -> bool:
        value: Value
        if not isinstance(other, Value):
            value = Value(other)  # type: ignore
        else:
            value = other

        if self.is_void() and value.is_void():
            return True

        return value._type == self._type and value._value == self._value

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __repr__(self) -> str:
        return "{}({})".format(self.type, self.value)


class WizardExpressionVisitor:

    _subpackages: SubPackages
    _variables: MutableMapping[str, Value]
    _functions: Mapping[str, Callable[[List[Value]], Value]]

    def __init__(
        self,
        variables: MutableMapping[str, Value],
        subpackages: SubPackages,
        functions: Mapping[str, Callable[[List[Value]], Value]],
    ):
        """
        Args:
            variables: List of variables. The expression visitor can modify
                the value of the variables but not add / remove variables.
            subpackages: The subpackages object.
            functions: List of functions. For method, function name should
                be "type.name" where type() is the name of the VariableType
                (e.g. string or integer).
        """
        self._variables = variables
        self._subpackages = subpackages
        self._functions = functions

    def visitTIMES_DIVIDE_MODULO(
        self, ctx: wizardParser.TIMES_DIVIDE_MODULOContext
    ) -> Value:
        op: Callable[[Value, Value], Value] = Value.__mul__
        if ctx.Divide():
            op = Value.__div__
        elif ctx.Modulo():
            op = Value.__mod__
        return op(self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)))

    def visitPLUS_MINUS(self, ctx: wizardParser.PLUS_MINUSContext) -> Value:
        op: Callable[[Value, Value], Value] = Value.__add__
        if ctx.Minus():
            op = Value.__sub__
        return op(self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)))

    def visitOR(self, ctx: wizardParser.ORContext) -> Value:
        return self.visitExpr(ctx.expr(0)) | self.visitExpr(ctx.expr(1))

    # Visit a parse tree produced by wizardParser#FUNCTION_CALL.
    def visitFUNCTION_CALL(self, ctx: wizardParser.FUNCTION_CALLContext) -> Value:

        name = ctx.Identifier().getText()
        if name not in self._functions:
            raise WizardNameError(name)

        values: List[Value] = []
        for ex in ctx.argList().expr():
            values.append(self.visitExpr(ex))
        return self._functions[name](values)

    # Visit a parse tree produced by wizardParser#METHOD_CALL.
    def visitMETHOD_CALL(self, ctx: wizardParser.METHOD_CALLContext) -> Value:
        values: List[Value] = [self.visitExpr(ctx.expr())]

        mname = "{}.{}".format(values[0].type, ctx.Identifier().getText())
        if mname not in self._functions:
            raise WizardNameError(mname)

        for ex in ctx.argList().expr():
            values.append(self.visitExpr(ex))

        return self._functions[mname](values)

    def visitLESSER(self, ctx: wizardParser.LESSERContext) -> Value:
        op = Value.__le__
        if ctx.Lesser():
            op = Value.__lt__
        return op(self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)))

    # Visit a parse tree produced by wizardParser#IN.
    def visitIN(self, ctx: wizardParser.INContext) -> Value:
        return self.visitExpr(ctx.expr(1)).contains(
            self.visitExpr(ctx.expr(0)), bool(ctx.Colon())
        )

    # Visit a parse tree produced by wizardParser#EQUAL.
    def visitEQUAL(self, ctx: wizardParser.EQUALContext) -> Value:
        op = Value.equals
        if ctx.NotEqual():
            op = Value.not_equals
        return op(self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)))

    # Visit a parse tree produced by wizardParser#GREATER.
    def visitGREATER(self, ctx: wizardParser.GREATERContext) -> Value:
        op = Value.__ge__
        if ctx.Lesser():
            op = Value.__gt__
        return op(self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)))

    # Visit a parse tree produced by wizardParser#POWER.
    def visitPOWER(self, ctx: wizardParser.POWERContext) -> Value:
        return self.visitExpr(ctx.expr(0)) ** self.visitExpr(ctx.expr(1))

    # Visit a parse tree produced by wizardParser#INDEXING.
    def visitINDEXING(self, ctx: wizardParser.INDEXINGContext) -> Value:
        return self.visitExpr(ctx.expr(0))[self.visitExpr(ctx.expr(1))]

    # Visit a parse tree produced by wizardParser#PRE_DECREMENT.
    def visitPRE_DECREMENT(self, ctx: wizardParser.PRE_DECREMENTContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._variables:
            raise WizardNameError(name)
        self._variables[ctx.Identifier().getText()] -= Value(1)
        return self._variables[ctx.Identifier().getText()]

    # Visit a parse tree produced by wizardParser#PRE_INCREMENT.
    def visitPRE_INCREMENT(self, ctx: wizardParser.PRE_INCREMENTContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._variables:
            raise WizardNameError(name)
        self._variables[ctx.Identifier().getText()] += Value(1)
        return self._variables[ctx.Identifier().getText()]

    # Visit a parse tree produced by wizardParser#POST_INCREMENT.
    def visitPOST_INCREMENT(self, ctx: wizardParser.POST_INCREMENTContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._variables:
            raise WizardNameError(name)
        self._variables[ctx.Identifier().getText()] += Value(1)
        return self._variables[ctx.Identifier().getText()]

    # Visit a parse tree produced by wizardParser#POST_DECREMENT.
    def visitPOST_DECREMENT(self, ctx: wizardParser.POST_DECREMENTContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._variables:
            raise WizardNameError(name)
        self._variables[ctx.Identifier().getText()] -= Value(1)
        return self._variables[ctx.Identifier().getText()]

    # Visit a parse tree produced by wizardParser#MINUS.
    def visitMINUS(self, ctx: wizardParser.MINUSContext) -> Value:
        return -self.visitExpr(ctx.expr())

    # Visit a parse tree produced by wizardParser#NOT.
    def visitNOT(self, ctx: wizardParser.NOTContext) -> Value:
        return self.visitExpr(ctx.expr()).logical_not()

    # Visit a parse tree produced by wizardParser#PARENS.
    def visitPARENS(self, ctx: wizardParser.PARENSContext) -> Value:
        return self.visitExpr(ctx.expr())

    # Visit a parse tree produced by wizardParser#SLICING.
    def visitSLICING(self, ctx: wizardParser.SLICINGContext) -> Value:
        raise WizardUnsupportedOperation("slicing")

    # Visit a parse tree produced by wizardParser#AND.
    def visitAND(self, ctx: wizardParser.ANDContext) -> Value:
        lhs, rhs = self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))
        return lhs & rhs

    def visitCONSTANTS(self, ctx: wizardParser.CONSTANTSContext) -> Value:
        if ctx.constant():
            return self.visitConstant(ctx.constant())
        if ctx.integer():
            return self.visitInteger(ctx.integer())
        if ctx.decimal():
            return self.visitDecimal(ctx.decimal())
        if ctx.string():
            return self.visitString(ctx.string())
        raise WizardNameError(ctx.getText())

    def visitVARIABLE(self, ctx: wizardParser.VARIABLEContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._variables:
            raise WizardNameError(name)

        return self._variables[ctx.Identifier().getText()]

    def visitConstant(self, ctx: wizardParser.ConstantContext) -> Value:
        if ctx.getText() == "False":
            return Value(False)
        elif ctx.getText() == "True":
            return Value(True)
        else:
            return Value(self._subpackages)

    def visitInteger(self, ctx: wizardParser.IntegerContext) -> Value:
        return Value(int(ctx.getText()))

    def visitDecimal(self, ctx: wizardParser.DecimalContext) -> Value:
        return Value(float(ctx.getText()))

    def visitString(self, ctx: wizardParser.StringContext) -> Value:
        return Value(ctx.getText()[1:-1])

    def visitExpr(self, ctx: wizardParser.ExprContext) -> Value:
        return getattr(self, "visit" + type(ctx).__name__[:-7])(ctx)  # type: ignore
