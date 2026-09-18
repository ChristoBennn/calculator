# Calculator

A simple calculator with a desktop app and a browser version that share the
same underlying logic.

**▶ Try it in your browser: https://christobennn.github.io/calculator/**

## Features

- `+`, `-`, `x`, `/`, `%`, decimals, and parentheses
- Square root and `+/-` sign toggle
- Backspace and clear
- Percent works like a normal calculator: `200 + 10%` = `220`, while
  `200 x 10%` = `20`
- Calculation history that persists between sessions
- Works by mouse/touch or keyboard

## Browser version

Open the link above, or run it locally:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

The page runs `calculator_core.py` directly in your browser using
[Pyodide](https://pyodide.org), so there is no server-side code. The Python
runtime (~10 MB) is fetched from a CDN on first load and cached afterwards,
so the first visit needs an internet connection.

## Desktop version

Requires Python 3 with tkinter (bundled with the standard installers for
Windows and macOS; on Debian/Ubuntu install it with `sudo apt install python3-tk`).

```bash
python3 calculator.py
```

History is saved next to the script in `history.json`.

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `0`–`9` `.` | digits and decimal point |
| `+` `-` `*` `/` `%` | operations (`x` also works) |
| `(` `)` | parentheses |
| `r` | square root |
| `Enter` or `=` | evaluate |
| `Backspace` | delete last character |
| `Esc` or `c` | clear |

## Running the tests

```bash
python3 -m unittest test_calculator -v
```

## Project structure

| File | Purpose |
| --- | --- |
| `calculator_core.py` | Calculator logic (`CalculatorModel` and the `press` key handler). No GUI dependencies, so it runs in normal Python and in the browser. |
| `calculator.py` | Desktop app built with tkinter. |
| `index.html` | Browser version; loads `calculator_core.py` via Pyodide and stores history in `localStorage`. |
| `test_calculator.py` | Unit tests for the logic, the key handler, and history persistence. |

Both interfaces call the same `press()` function, so they behave identically.
