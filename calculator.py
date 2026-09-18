"""A simple calculator app built with only the Python standard library.

Run with:  python calculator.py

Supports +, -, x, /, %, parentheses, square root, decimals, +/- sign
toggle, clear, and backspace. Works by both mouse clicks and keyboard
input. Calculation history is saved next to this file in history.json.

The same calculator logic powers the browser version in index.html, which
runs calculator_core.py client-side via Pyodide.
"""

import json
import os
import tkinter as tk
from tkinter import font

from calculator_core import SQRT, CalculatorModel, press

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
        display, record = press(self.model, label)
        if record is not None:
            self._add_history(*record)
        self._refresh(display)

    def on_key(self, event):
        """Support physical keyboard input for convenience."""
        key = event.char
        if key in "0123456789.+-*/%()":
            self.on_press(key)
        elif key in ("r", "R"):  # r = square root
            self.on_press(SQRT)
        elif key == "\r" or key == "=":
            self.on_press("=")
        elif key == "\x08":  # Backspace
            self.on_press("<")
        elif key in ("\x1b", "c", "C"):  # Escape or C clears
            self.on_press("C")

    def _refresh(self, text):
        self.display_var.set(text)


def main():
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
