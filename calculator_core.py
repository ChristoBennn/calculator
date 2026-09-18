"""Calculator logic shared by the desktop app and the web page.

This module deliberately imports nothing but the standard library and has no
GUI dependencies, so it runs both under normal Python and inside the browser
via Pyodide. The desktop window lives in calculator.py.
"""

import math

# The key that means "square root". Kept as a constant so both user
# interfaces agree on the label.
SQRT = "\u221a"


class CalculatorModel:
    """Holds the current expression and evaluates it safely."""

    def __init__(self):
        self.expression = ""
        # True right after "=", so the next key can start a fresh calculation.
        self.just_evaluated = False

    def clear(self):
        self.expression = ""
        self.just_evaluated = False

    def backspace(self):
        self.expression = self.expression[:-1]
        self.just_evaluated = False

    def toggle_sign(self):
        """Flip the sign of the number currently being typed."""
        if not self.expression:
            return
        self.just_evaluated = False
        # Find the start of the last number in the expression.
        i = len(self.expression)
        while i > 0 and (self.expression[i - 1].isdigit() or self.expression[i - 1] == "."):
            i -= 1
        start = i
        # Skip a leading minus that belongs to this number.
        if i > 0 and self.expression[i - 1] == "-":
            start = i - 1
        else:
            start = i
        number = self.expression[start:]
        if not number:
            return
        if number.startswith("-"):
            self.expression = self.expression[:start] + number[1:]
        else:
            self.expression = self.expression[:start] + "-" + number

    def append(self, text):
        """Add a digit, operator, or decimal point to the expression."""
        # After "=", a digit or "(" starts a new calculation, while an
        # operator continues from the result that is already on screen.
        if self.just_evaluated:
            if text.isdigit() or text in ".(":
                self.expression = ""
            self.just_evaluated = False
        if text == ".":
            # Do not allow two dots in the same number.
            last_number = self._last_number()
            if "." in last_number:
                return
        self.expression += text

    def _last_number_start(self):
        i = len(self.expression)
        while i > 0 and (self.expression[i - 1].isdigit() or self.expression[i - 1] == "."):
            i -= 1
        return i

    def _last_number(self):
        return self.expression[self._last_number_start():]

    def apply_percent(self):
        """Turn the last number into a percentage, like a normal calculator.

        With + or -, the percentage is relative to the value before the
        operator (200 + 10% -> 200 + 20). With x or /, the number is just
        divided by 100 (200 x 10% -> 200 x 0.1). A bare number becomes
        itself over 100 (50% -> 0.5).
        """
        start = self._last_number_start()
        number_text = self.expression[start:]
        if not number_text:
            return
        prefix = self.expression[:start]
        value = float(number_text)

        operator = prefix[-1] if prefix and prefix[-1] in "+-x*/" else None
        if operator is not None and operator in "+-":
            # Relative to the running total before this operator.
            try:
                left = self._eval_expr(prefix[:-1])
            except Exception:
                left = None
            value = left * value / 100 if left is not None else value / 100
        else:
            value = value / 100

        self.expression = prefix + self._format_number(value)
        self.just_evaluated = False

    def apply_sqrt(self):
        """Replace the last number with its square root (9 -> 3)."""
        start = self._last_number_start()
        number_text = self.expression[start:]
        if not number_text:
            raise ValueError("No number to take the square root of")
        value = float(number_text)
        if value < 0:
            raise ValueError("Cannot take the square root of a negative number")
        self.expression = self.expression[:start] + self._format_number(math.sqrt(value))
        self.just_evaluated = False

    @staticmethod
    def _format_number(value):
        """Render a float without trailing zeros or scientific notation."""
        if float(value).is_integer():
            return str(int(value))
        text = f"{value:.10g}"
        if "e" in text or "E" in text:
            text = f"{value:.10f}".rstrip("0").rstrip(".")
        return text

    @staticmethod
    def _eval_expr(expr):
        """Safely evaluate a plain arithmetic expression."""
        expr = expr.replace("x", "*").strip()
        # Only allow characters that are safe for our simple evaluator.
        allowed = set("0123456789.+-*/() ")
        if not set(expr) <= allowed:
            raise ValueError("Invalid characters in expression")
        return eval(expr, {"__builtins__": {}}, {})

    def evaluate(self):
        """Evaluate the expression and return the result as a string."""
        if not self.expression.strip():
            return ""
        result = self._eval_expr(self.expression)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        # Remember that the screen now shows a finished result.
        self.just_evaluated = True
        return str(result)


def press(model, label):
    """Apply one key press to ``model``.

    Returns ``(display, record)`` where ``display`` is the text to show and
    ``record`` is an ``(expression, result)`` tuple when a calculation was
    completed, otherwise ``None``. Sharing this between the desktop and web
    interfaces keeps their behaviour identical.
    """
    if label == "C":
        model.clear()
        return "0", None
    if label == "<":
        model.backspace()
        return model.expression or "0", None
    if label == "%":
        model.apply_percent()
        return model.expression or "0", None
    if label == SQRT:
        try:
            model.apply_sqrt()
        except Exception:
            model.clear()
            return "Error", None
        return model.expression or "0", None
    if label == "+/-":
        model.toggle_sign()
        return model.expression or "0", None
    if label == "=":
        return _equals(model)

    model.append(label)
    return model.expression, None


def _equals(model):
    """Handle the "=" key, returning (display, record)."""
    original = model.expression.strip()
    if not original:
        return model.expression or "0", None
    try:
        result = model.evaluate()
    except ZeroDivisionError:
        model.clear()
        return "Error: divide by zero", None
    except Exception:
        model.clear()
        return "Error", None
    model.expression = result
    return result, (original, result)
