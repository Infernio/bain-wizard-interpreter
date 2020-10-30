# -*- encoding: utf-8 -*-

import codecs
import re

from typing import overload, Callable, List, Optional, Type

from .antlr4.wizardParser import wizardParser
from .errors import WizardTypeError, WizardIndexError, WizardNameError
from .abstract_interpreter import AbstractWizardInterpreter
from .severity import Issue
from .value import (  # noqa: F401
    SubPackage,
    SubPackages,
    Value,
    ValueType,
    VariableType,
    Void,
)


class WizardExpressionVisitor:

    """
    Visitor for Wizard expression. This visitor can be used to interpret Wizard
    expression and return `Value` object. The main entry point is `visitExpr()`
    which takes an expression context and returns a `Value`.
    """

    BAD_ESCAPE_SEQUENCE = re.compile(r"(^|(?<=[^\\]))\\(?=[^abfnrtuUx0-7\\])")

    _intp: AbstractWizardInterpreter

    def __init__(
        self, interpreter: AbstractWizardInterpreter,
    ):
        """
        Args:
            interpreter: The interpreter to use with this expression visitor.
        """
        self._intp = interpreter

    def visitTimesDivideModulo(
        self, ctx: wizardParser.TimesDivideModuloContext
    ) -> Value:
        op: Callable[[Value, Value], Value] = Value.__mul__
        if ctx.Divide():
            op = Value.__div__
        elif ctx.Modulo():
            op = Value.__mod__
        return op(self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)))

    def visitPlusMinus(self, ctx: wizardParser.PlusMinusContext) -> Value:
        op: Callable[[Value, Value], Value] = Value.__add__
        if ctx.Minus():
            op = Value.__sub__
        return op(self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)))

    def visitOr(self, ctx: wizardParser.OrContext) -> Value:
        return self.visitExpr(ctx.expr(0)) | self.visitExpr(ctx.expr(1))

    def visitFunctionCall(self, ctx: wizardParser.FunctionCallContext) -> Value:

        name = ctx.Identifier().getText()
        if name not in self._intp.functions:
            raise WizardNameError(ctx.Identifier(), name)

        values: List[Value] = []
        for ex in ctx.argList().expr():
            values.append(self.visitExpr(ex))

        return self._intp.functions[name](values)

    def visitDotFunctionCall(self, ctx: wizardParser.DotFunctionCallContext) -> Value:
        values: List[Value] = [self.visitExpr(ctx.expr())]

        mname = "{}.{}".format(values[0].type, ctx.Identifier().getText())
        if mname not in self._intp.functions:
            raise WizardNameError(ctx.Identifier(), mname)

        for ex in ctx.argList().expr():
            values.append(self.visitExpr(ex))

        return self._intp.functions[mname](values)

    def visitIn(self, ctx: wizardParser.InContext) -> Value:
        return self.visitExpr(ctx.expr(1)).contains(
            self.visitExpr(ctx.expr(0)), bool(ctx.Colon())
        )

    def doCmp(
        self,
        op: Callable[[Value, Value], Value],
        lhs: Value,
        rhs: Value,
        case_insensitive: bool = True,
    ) -> Value:
        if case_insensitive:
            if not isinstance(lhs.value, str) or not isinstance(rhs.value, str):
                raise WizardTypeError(
                    "Cannot use case-insensitive comparison with values of type"
                    f" {lhs.type}, {rhs.type}."
                )
            lhs = Value(lhs.value.lower())
            rhs = Value(rhs.value.lower())
        return op(lhs, rhs)

    def visitEqual(self, ctx: wizardParser.EqualContext) -> Value:
        op = Value.equals
        if ctx.NotEqual():
            op = Value.not_equals
        return self.doCmp(
            op,
            self.visitExpr(ctx.expr(0)),
            self.visitExpr(ctx.expr(1)),
            bool(ctx.Colon()),
        )

    def visitLesser(self, ctx: wizardParser.LesserContext) -> Value:
        op = Value.__le__
        if ctx.Lesser():
            op = Value.__lt__
        return self.doCmp(
            op,
            self.visitExpr(ctx.expr(0)),
            self.visitExpr(ctx.expr(1)),
            bool(ctx.Colon()),
        )

    def visitGreater(self, ctx: wizardParser.GreaterContext) -> Value:
        op = Value.__ge__
        if ctx.Greater():
            op = Value.__gt__
        return self.doCmp(
            op,
            self.visitExpr(ctx.expr(0)),
            self.visitExpr(ctx.expr(1)),
            bool(ctx.Colon()),
        )

    def visitExponentiation(self, ctx: wizardParser.ExponentiationContext) -> Value:
        return self.visitExpr(ctx.expr(0)) ** self.visitExpr(ctx.expr(1))

    def visitIndex(self, ctx: wizardParser.IndexContext) -> Value:
        return self.visitExpr(ctx.expr(0))[self.visitExpr(ctx.expr(1))]

    def visitPreDecrement(self, ctx: wizardParser.PreDecrementContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._intp.variables:
            raise WizardNameError(ctx.Identifier(), name)
        self._intp.variables[ctx.Identifier().getText()] -= Value(1)
        return self._intp.variables[ctx.Identifier().getText()]

    def visitPreIncrement(self, ctx: wizardParser.PreIncrementContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._intp.variables:
            raise WizardNameError(ctx.Identifier(), name)
        self._intp.variables[ctx.Identifier().getText()] += Value(1)
        return self._intp.variables[ctx.Identifier().getText()]

    def visitPostIncrement(self, ctx: wizardParser.PostIncrementContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._intp.variables:
            raise WizardNameError(ctx.Identifier(), name)
        self._intp.variables[ctx.Identifier().getText()] += Value(1)
        return self._intp.variables[ctx.Identifier().getText()]

    def visitPostDecrement(self, ctx: wizardParser.PostDecrementContext) -> Value:
        name = ctx.Identifier().getText()
        if name not in self._intp.variables:
            raise WizardNameError(ctx.Identifier(), name)
        self._intp.variables[ctx.Identifier().getText()] -= Value(1)
        return self._intp.variables[ctx.Identifier().getText()]

    def visitNegative(self, ctx: wizardParser.NegativeContext) -> Value:
        return -self.visitExpr(ctx.expr())

    def visitNot(self, ctx: wizardParser.NotContext) -> Value:
        return self.visitExpr(ctx.expr()).logical_not()

    def visitParenExpr(self, ctx: wizardParser.ParenExprContext) -> Value:
        return self.visitExpr(ctx.expr())

    def visitSlice(self, ctx: wizardParser.SliceContext) -> Value:
        # expr LeftBracket expr? Colon expr? (Colon expr?)? RightBracket
        lhs = self.visitExpr(ctx.expr(0))

        start: Optional[Value] = None
        end: Optional[Value] = None
        step: Optional[Value] = None

        # Index of end expression in ctx.children (without start by
        # default):
        cidx: int = 3

        # Is there a start?
        if isinstance(ctx.children[2], wizardParser.ExprContext):
            start = self.visitExpr(ctx.expr(1))
            cidx = 4

        # Is there and end?
        if isinstance(ctx.children[cidx], wizardParser.ExprContext):
            end = self.visitExpr(ctx.children[cidx])

        # Is there a step?
        if ctx.Colon(1) and isinstance(ctx.children[-2], wizardParser.ExprContext):
            step = self.visitExpr(ctx.children[-2])

        # We keep None and let python built-in slice() do the job for us.
        return lhs.slice(start, end, step)

    def visitAnd(self, ctx: wizardParser.AndContext) -> Value:
        lhs, rhs = self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))
        return lhs & rhs

    def visitValue(self, ctx: wizardParser.ValueContext) -> Value:
        if ctx.constant():
            return self.visitConstant(ctx.constant())
        if ctx.integer():
            return self.visitInteger(ctx.integer())
        if ctx.decimal():
            return self.visitDecimal(ctx.decimal())
        if ctx.string():
            return self.visitString(ctx.string())
        if ctx.Identifier():
            name = ctx.Identifier().getText()
            if name not in self._intp.variables:
                # Severity check:
                self._intp.severity.raise_or_warn(
                    Issue.USAGE_OF_NOTSET_VARIABLES,
                    WizardNameError(ctx.Identifier(), name),
                    f"Variable {name} used before being set, default to 0.",
                )
                return Value(0)
            else:
                return self._intp.variables[ctx.Identifier().getText()]

        raise WizardNameError(ctx, ctx.getText())

    def visitConstant(self, ctx: wizardParser.ConstantContext) -> Value:
        if ctx.getText() == "False":
            return Value(False)
        elif ctx.getText() == "True":
            return Value(True)
        else:
            return Value(self._intp.subpackages)

    def visitInteger(self, ctx: wizardParser.IntegerContext) -> Value:
        return Value(int(ctx.getText()))

    def visitDecimal(self, ctx: wizardParser.DecimalContext) -> Value:
        return Value(float(ctx.getText()))

    def visitString(self, ctx: wizardParser.StringContext) -> Value:
        # Remove the quotation marks:
        txt = ctx.getText()[1:-1]

        # Remove bad escape sequences:
        txt = self.BAD_ESCAPE_SEQUENCE.sub("", txt)

        # Replace escape sequences by Python escape sequences:
        txt = codecs.decode(txt, "unicode_escape")

        return Value(txt)

    @overload
    def visitExpr(self, ctx: wizardParser.ExprContext) -> Value:
        ...

    @overload
    def visitExpr(
        self, ctx: wizardParser.ExprContext, typ: Type[ValueType]
    ) -> Value[ValueType]:
        ...

    def visitExpr(
        self, ctx: wizardParser.ExprContext, typ: Optional[Type[ValueType]] = None
    ):
        try:
            value = getattr(self, "visit" + type(ctx).__name__[:-7])(ctx)
        except TypeError as te:
            raise WizardTypeError(ctx, *te.args)
        except IndexError as ie:
            raise WizardIndexError(ctx, *ie.args)

        if typ is not None and not isinstance(value.value, typ):
            raise WizardTypeError(
                ctx,
                f"Expected value of type {VariableType.from_pytype(typ)} but got value"
                f" of type {value.type}.",
            )

        return value  # type: ignore
