"""Unit tests for calculator.py.

Run with:  python -m unittest test_calculator -v
Only uses the standard library (unittest).
"""

import os
import tempfile
import unittest

from calculator import CalculatorModel, load_history, save_history


def run(keys):
    """Feed a sequence of button labels to a fresh model and return it."""
    model = CalculatorModel()
    for key in keys:
        if key == "%":
            model.apply_percent()
        elif key == "\u221a":
            model.apply_sqrt()
        else:
            model.append(key)
    return model


class TestArithmetic(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(run(["1", "+", "2"]).evaluate(), "3")

    def test_multiplication_precedence(self):
        self.assertEqual(run(["1", "+", "2", "x", "3"]).evaluate(), "7")

    def test_multiply_button(self):
        # The button labelled "x" must behave as multiplication.
        self.assertEqual(run(["3", "x", "4"]).evaluate(), "12")

    def test_division(self):
        self.assertEqual(run(["8", "/", "2"]).evaluate(), "4")

    def test_subtraction_negative_result(self):
        self.assertEqual(run(["2", "-", "5"]).evaluate(), "-3")

    def test_decimals(self):
        self.assertEqual(run(["3", ".", "5", "+", "1", ".", "2", "5"]).evaluate(), "4.75")

    def test_integer_float_is_rendered_without_point(self):
        self.assertEqual(run(["10", "/", "4"]).evaluate(), "2.5")

    def test_divide_by_zero_raises(self):
        with self.assertRaises(ZeroDivisionError):
            run(["5", "/", "0"]).evaluate()

    def test_empty_expression_evaluates_to_empty(self):
        self.assertEqual(CalculatorModel().evaluate(), "")

    def test_invalid_characters_rejected(self):
        model = CalculatorModel()
        model.append("1")
        model.expression = "1 import os"
        with self.assertRaises(ValueError):
            model.evaluate()


class TestParentheses(unittest.TestCase):
    def test_parentheses(self):
        self.assertEqual(run(["(", "2", "+", "3", ")", "x", "4"]).evaluate(), "20")

    def test_nested_parentheses(self):
        self.assertEqual(run(["(", "(", "1", "+", "1", ")", "x", "3", ")"]).evaluate(), "6")

    def test_unbalanced_parentheses_raise(self):
        with self.assertRaises(Exception):
            run(["(", "2", "+", "3"]).evaluate()


class TestSqrt(unittest.TestCase):
    def test_perfect_square(self):
        self.assertEqual(run(["9", "\u221a"]).evaluate(), "3")

    def test_non_perfect_square(self):
        self.assertEqual(run(["2", "\u221a"]).evaluate(), "1.414213562")

    def test_sqrt_of_expression_tail(self):
        self.assertEqual(run(["1", "6", "\u221a"]).evaluate(), "4")

    def test_leading_minus_is_treated_as_an_operator(self):
        model = CalculatorModel()
        model.append("9")
        model.toggle_sign()  # expression is now "-9"
        model.apply_sqrt()
        # Only the trailing number (9) is rooted, leaving the minus in place.
        self.assertEqual(model.expression, "-3")

    def test_no_number_raises(self):
        with self.assertRaises(ValueError):
            CalculatorModel().apply_sqrt()


class TestPercent(unittest.TestCase):
    def test_standalone(self):
        self.assertEqual(run(["5", "0", "%"]).evaluate(), "0.5")

    def test_add_percent_of_left_operand(self):
        self.assertEqual(run(["2", "0", "0", "+", "1", "0", "%"]).evaluate(), "220")

    def test_subtract_percent_of_left_operand(self):
        self.assertEqual(run(["2", "0", "0", "-", "1", "0", "%"]).evaluate(), "180")

    def test_multiply_percent_divides_by_100(self):
        self.assertEqual(run(["2", "0", "0", "x", "1", "0", "%"]).evaluate(), "20")

    def test_divide_percent_divides_by_100(self):
        self.assertEqual(run(["2", "0", "0", "/", "1", "0", "%"]).evaluate(), "2000")


class TestEditing(unittest.TestCase):
    def test_backspace(self):
        model = run(["1", "2", "3"])
        model.backspace()
        self.assertEqual(model.expression, "12")

    def test_clear(self):
        model = run(["1", "2", "3"])
        model.clear()
        self.assertEqual(model.expression, "")

    def test_toggle_sign_adds_and_removes(self):
        model = run(["7"])
        model.toggle_sign()
        self.assertEqual(model.expression, "-7")
        model.toggle_sign()
        self.assertEqual(model.expression, "7")

    def test_double_decimal_point_ignored(self):
        model = run(["1", ".", ".", "5"])
        self.assertEqual(model.expression, "1.5")


class TestPostEquals(unittest.TestCase):
    """After "=", a new digit starts fresh but operators keep chaining."""

    @staticmethod
    def _finished(keys):
        model = run(keys)
        result = model.evaluate()  # sets just_evaluated, like pressing "="
        model.expression = result  # the app leaves the result on the display
        return model

    def test_digit_starts_a_new_calculation(self):
        model = self._finished(["1", "+", "2"])
        self.assertEqual(model.expression, "3")
        model.append("5")
        self.assertEqual(model.expression, "5")

    def test_decimal_starts_a_new_calculation(self):
        model = self._finished(["1", "+", "2"])
        model.append(".")
        self.assertEqual(model.expression, ".")

    def test_open_paren_starts_a_new_calculation(self):
        model = self._finished(["1", "+", "2"])
        model.append("(")
        self.assertEqual(model.expression, "(")

    def test_operator_continues_from_the_result(self):
        model = self._finished(["1", "+", "2"])
        model.append("+")
        model.append("4")
        self.assertEqual(model.expression, "3+4")
        self.assertEqual(model.evaluate(), "7")

    def test_clear_resets_the_finished_state(self):
        model = self._finished(["1", "+", "2"])
        model.clear()
        model.append("7")
        self.assertEqual(model.expression, "7")


class TestHistoryPersistence(unittest.TestCase):
    def test_save_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.json")
            entries = [("1+2", "3"), ("5x3", "15")]
            save_history(entries, path)
            self.assertEqual(load_history(path), entries)

    def test_load_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_history(os.path.join(tmp, "nope.json")), [])

    def test_load_corrupt_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not valid json")
            self.assertEqual(load_history(path), [])

    def test_load_skips_malformed_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.json")
            save_history([["1+1", "2"], ["bad"], "junk"], path)
            self.assertEqual(load_history(path), [("1+1", "2")])


if __name__ == "__main__":
    unittest.main()
