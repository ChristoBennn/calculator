"""A simple calculator app built with only the Python standard library.

Run with:  python calculator.py

Supports +, -, x, /, %, parentheses, square root, decimals, +/- sign
toggle, clear, and backspace. Works by both mouse clicks and keyboard
input. Calculation history is saved next to this file in history.json.
"""

import json
import math
import os
import tkinter as tk
from tkinter import font

# Where the calculation history is stored between runs.
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")


def load_history(path=HISTORY_FILE):
    """Return the saved history as a list of (expression, result) tuples."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        # Missing or unreadable file just means there is no history yet.
        return []
    entries = []
    for item in data:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            entries.append((str(item[0]), str(item[1])))
    return entries


def save_history(history, path=HISTORY_FILE):
    """Write the history to disk, ignoring write failures."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(list(history), handle, indent=2)
    except OSError:
        pass  # History is a convenience; never crash over a write failure.


# ---------------------------------------------------------------------------
# Calculator logic (kept separate from the GUI so it is easy to read/test)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class CalculatorApp:
    # Layout of the buttons as (label, row, column, columnspan).
    BUTTONS = [
        ("C", 0, 0, 1), ("(", 0, 1, 1), (")", 0, 2, 1), ("\u221a", 0, 3, 1),
        ("7", 1, 0, 1), ("8", 1, 1, 1), ("9", 1, 2, 1), ("/", 1, 3, 1),
        ("4", 2, 0, 1), ("5", 2, 1, 1), ("6", 2, 2, 1), ("x", 2, 3, 1),
        ("1", 3, 0, 1), ("2", 3, 1, 1), ("3", 3, 2, 1), ("-", 3, 3, 1),
        ("0", 4, 0, 1), (".", 4, 1, 1), ("+/-", 4, 2, 1), ("+", 4, 3, 1),
        ("%", 5, 0, 1), ("<", 5, 1, 1), ("=", 5, 2, 2),
    ]

    def __init__(self, root):
        self.root = root
        self.model = CalculatorModel()
        self.display_var = tk.StringVar(value="0")
        self.history_path = HISTORY_FILE
        self.history = load_history(self.history_path)  # (expression, result) tuples

        root.title("Calculator")
        root.resizable(False, False)

        self._build_display()
        self._build_buttons()
        self._build_history()
        self._bind_keys()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_display(self):
        display_font = font.Font(family="Helvetica", size=24, weight="bold")
        entry = tk.Entry(
            self.root,
            textvariable=self.display_var,
            font=display_font,
            justify="right",
            bd=10,
            state="readonly",
            readonlybackground="white",
        )
        entry.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=6, pady=(6, 2))
        self.display = entry

    def _build_buttons(self):
        button_font = font.Font(family="Helvetica", size=16)
        for label, row, col, span in self.BUTTONS:
            tk.Button(
                self.root,
                text=label,
                font=button_font,
                width=5,
                height=2,
                command=lambda l=label: self.on_press(l),
            ).grid(row=row + 1, column=col, columnspan=span, padx=3, pady=3, sticky="nsew")

    def _build_history(self):
        panel = tk.Frame(self.root, bd=2, relief="groove")
        panel.grid(row=0, column=4, rowspan=7, sticky="nsew", padx=(2, 6), pady=6)

        header = font.Font(family="Helvetica", size=12, weight="bold")
        tk.Label(panel, text="History", font=header).pack(pady=(4, 2))

        list_frame = tk.Frame(panel)
        list_frame.pack(fill="both", expand=True, padx=4)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.history_list = tk.Listbox(
            list_frame, width=22, yscrollcommand=scrollbar.set, activestyle="none"
        )
        self.history_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.history_list.yview)
        # Double-click an entry to reuse its result as the new starting value.
        self.history_list.bind("<Double-Button-1>", self._recall_from_history)

        # Show anything restored from the previous run.
        for expression, result in self.history:
            self.history_list.insert(tk.END, f"{expression} = {result}")

        tk.Button(panel, text="Clear History", command=self._clear_history).pack(
            fill="x", padx=4, pady=4
        )

    def _add_history(self, expression, result):
        self.history.append((expression, result))
        self.history_list.insert(tk.END, f"{expression} = {result}")
        self.history_list.see(tk.END)
        self._save_history()

    def _clear_history(self):
        self.history.clear()
        self.history_list.delete(0, tk.END)
        self._save_history()

    def _save_history(self):
        save_history(self.history, self.history_path)

    def _on_close(self):
        self._save_history()
        self.root.destroy()

    def _recall_from_history(self, _event):
        selection = self.history_list.curselection()
        if not selection:
            return
        result = self.history[selection[0]][1]
        self.model.clear()
        self.model.append(result)
        self._refresh(result)

    def _bind_keys(self):
        self.root.bind("<Key>", self.on_key)

    # -- input handling ----------------------------------------------------
    def on_press(self, label):
        if label == "C":
            self.model.clear()
            self._refresh("0")
        elif label == "<":
            self.model.backspace()
            self._refresh(self.model.expression or "0")
        elif label == "=":
            self._calculate()
        elif label == "%":
            self.model.apply_percent()
            self._refresh(self.model.expression or "0")
        elif label == "\u221a":
            try:
                self.model.apply_sqrt()
            except Exception:
                self._refresh("Error")
                self.model.clear()
                return
            self._refresh(self.model.expression or "0")
        elif label in "()":
            self.model.append(label)
            self._refresh(self.model.expression)
        elif label == "+/-":
            self.model.toggle_sign()
            self._refresh(self.model.expression or "0")
        else:
            self.model.append(label)
            self._refresh(self.model.expression)

    def on_key(self, event):
        """Support physical keyboard input for convenience."""
        key = event.char
        if key in "0123456789.+-*/%()":
            self.on_press(key)
        elif key in ("r", "R"):  # r = square root
            self.on_press("\u221a")
        elif key == "\r" or key == "=":
            self.on_press("=")
        elif key == "\x08":  # Backspace
            self.on_press("<")
        elif key in ("\x1b", "c", "C"):  # Escape or C clears
            self.on_press("C")

    def _calculate(self):
        original = self.model.expression.strip()
        if not original:
            return
        try:
            result = self.model.evaluate()
        except ZeroDivisionError:
            self._refresh("Error: divide by zero")
            self.model.clear()
            return
        except Exception:
            self._refresh("Error")
            self.model.clear()
            return
        self._add_history(original, result)
        self.model.expression = result
        self._refresh(result)

    def _refresh(self, text):
        self.display_var.set(text)


def main():
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
