import click
from pprint import pformat
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.completion.base import Completer
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.python import Python3Lexer
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name
from prompt_toolkit.completion import Completion
import cls_client

from .utils import pull_request_url_command
from pullapprove.exceptions import UserError
from pullapprove.models.expressions import Expression
from pullapprove.logger import logger
from pullapprove.context.base import ContextObject


class ContextCompleterValidator(Completer, Validator):
    def __init__(self, expression_context, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expression_context = expression_context

        # Store the most recent one, so the completer and validator can share the result without recomputing
        self.last_expression_str = ""
        self.last_expression = None
        self.last_expression_exception = None

        # So we can complete attrs of the last valid obj
        self.last_valid_expression = None

    def eval_expression(self, expression_str):
        # Return the last result if the expression is the same
        if expression_str == self.last_expression_str:
            if self.last_expression_exception:
                raise self.last_expression_exception
            else:
                return self.last_expression

        self.last_expression_str = expression_str
        self.last_expression = Expression(expression_str)

        try:
            self.last_expression.load(self.expression_context)
            self.last_expression_exception = None
            self.last_valid_expression = self.last_expression
        except UserError as e:
            self.last_expression_exception = e
            # completer/validator needs to handle the UserError
            raise

        return self.last_expression

    def complete_context_vars(self, d, prefix=""):
        if prefix:
            start_position = -len(prefix)
        else:
            start_position = 0

        for k, v in d.items():
            if k.startswith(prefix) and not k.startswith("_"):
                yield Completion(
                    k, display_meta=type(v).__name__, start_position=start_position
                )

    def get_completions(self, document, complete_event):
        if not document.text:
            for c in self.complete_context_vars(self.expression_context):
                yield c
            return

        if (
            len(document.text_before_cursor) > 0
            and document.text_before_cursor[-1] == " "
        ):
            for c in self.complete_context_vars(self.expression_context):
                yield c
            return

        expression_text_last_chunk = document.text_before_cursor.split()[-1]
        completion_prefix = (
            ""  # optionally filter completions by a prefix (ex. beginning of word)
        )

        # If it ended with a dot, we want to complete the attributes
        if expression_text_last_chunk.endswith("."):
            try:
                expression = self.eval_expression(expression_text_last_chunk[:-1])
            except UserError:
                return

            expression_result = expression.expression_result
        elif expression_text_last_chunk.endswith("["):
            # complete dict keys?
            return
        elif expression_text_last_chunk.endswith("("):
            # complete function arguments?
            return
        else:
            try:
                expression = self.eval_expression(expression_text_last_chunk)
                return  # valid expression, not sure what's next
            except UserError:
                # middle of word, maybe
                if "." in expression_text_last_chunk and self.last_valid_expression:
                    expression_result = self.last_valid_expression.expression_result
                    completion_prefix = expression_text_last_chunk.split(".")[-1]
                else:
                    for c in self.complete_context_vars(
                        self.expression_context, prefix=expression_text_last_chunk
                    ):
                        yield c
                    return

        if isinstance(expression_result, dict):
            for c in self.complete_context_vars(
                expression_result, prefix=completion_prefix
            ):
                yield c
        elif isinstance(expression_result, ContextObject):
            context_vars = {
                name: getattr(expression_result, name)
                for name in dir(expression_result)
            }
            for c in self.complete_context_vars(context_vars, prefix=completion_prefix):
                yield c

    def validate(self, document):
        text = document.text

        if not text:
            return

        if text in ("help", "exit", "exit()"):
            return

        try:
            self.eval_expression(text)
        except UserError as e:
            raise ValidationError(message=str(e))


class REPL:
    def __init__(self, expression_context):
        self.expression_context = expression_context
        completer_validator = ContextCompleterValidator(
            expression_context=self.expression_context
        )
        self.session = PromptSession(
            completer=completer_validator,
            validator=completer_validator,
            lexer=PygmentsLexer(Python3Lexer),
            style=style_from_pygments_cls(get_style_by_name("bw")),
            include_default_pygments_style=False,
            validate_while_typing=True,
            complete_in_thread=True,
        )

    def run(self):
        click.echo(
            'Type "help" to see the available variables.\n\nHit Ctrl+C or type "exit" to quit.\n'
        )

        while True:
            expression_str = self.session.prompt(
                HTML("<b>>>></b> "),
            )
            if expression_str in ("exit", "exit()"):
                break
            if expression_str == "help":
                click.secho(
                    f"Available context:\n{pformat(self.expression_context)}",
                    fg="yellow",
                )
            else:
                try:
                    expression = Expression(expression_str)
                    expression.load(self.expression_context)
                    click.secho("Passed: ", nl=False, bold=True)
                    click.secho(
                        expression.is_met, fg="green" if expression.is_met else "red"
                    )
                    click.secho("Output: ", nl=False, bold=True)
                    click.secho(pformat(expression.expression_result))
                    if hasattr(expression.expression_result, "_data"):
                        click.secho(pformat(expression.expression_result._data))
                except UserError as e:
                    click.secho(str(e), fg="red", err=True)
                click.echo()


@click.command()
@pull_request_url_command
@cls_client.track_command()
def repl(pull_request):
    """Interactive expression testing"""
    logger.disabled = True

    ctx = pull_request.as_context()

    repl = REPL(ctx)
    repl.run()
