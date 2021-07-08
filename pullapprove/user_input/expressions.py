from typing import Any, Dict, Optional

from jinja2 import StrictUndefined
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from jinja2.sandbox import ImmutableSandboxedEnvironment


class Expression(object):
    def __init__(
        self, string: str, context: Dict[str, Any] = {}, *args, **kwargs
    ) -> None:
        assert isinstance(string, str), "Expression must be a string"
        self.string = string
        self.environment = ImmutableSandboxedEnvironment(undefined=StrictUndefined)
        self.context = context
        self.environment.globals = self.context

    def compile(self) -> Optional[Any]:
        result: Optional[Any] = False

        try:
            expr = self.environment.compile_expression(
                self.string, undefined_to_none=False
            )
            result = expr()
            if result:
                # needs to evaluate it to trigger undefined error
                pass

        except UndefinedError as e:
            raise ExpressionException(e.message)
        except TemplateSyntaxError as e:
            raise ExpressionException(e.message)
        except Exception as e:
            raise ExpressionException(str(e))
            # if str(e) == "argument of type 'StrictUndefined' is not iterable":
            #     raise ExpressionException(str(e))
            # else:
            #     raise e

        return result


class ExpressionException(Exception):
    pass
