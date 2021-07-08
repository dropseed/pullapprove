from typing import Any, Dict, Optional

from pullapprove.exceptions import UserError
from pullapprove.user_input.expressions import Expression as UserExpression
from pullapprove.user_input.expressions import ExpressionException


class Expression:
    def __init__(self, expression_str: str) -> None:
        self.expression_str = expression_str
        self.expression_result: Optional[Any] = False
        self.context: Dict[str, Any] = {}

    def load(self, ctx: Dict[str, Any]) -> None:
        self.context = ctx
        try:
            self.expression_result = UserExpression(
                self.expression_str, self.context
            ).compile()
        except ExpressionException as e:
            raise UserError(f"Expression error: {e} in {self.expression_str}")

    @property
    def is_met(self) -> bool:
        return bool(self.expression_result)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "expression": self.expression_str,
            "result": str(self.expression_result),
            "is_met": self.is_met,
        }
