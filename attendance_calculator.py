"""
attendance_calculator.py
------------------------
"How many classes can I miss?" logic. Uses exact fractions (not floats) so the
answer is correct even exactly on the threshold (e.g. 75/100 at 75%).

Maths (r = required percent, P = attended, T = total conducted):
  Stay above the line after missing x more classes:   P / (T + x) >= r/100
  =>  T + x <= P * 100 / r   =>  x = floor(P * 100 / r) - T      (never below 0)

  If already below: attend y classes in a row so that (P + y)/(T + y) >= r/100
  =>  y = ceil((r*T - 100*P) / (100 - r))
"""
import math
from fractions import Fraction


def validate_inputs(attended, total, required):
    """Return a list of error messages (empty list = inputs are fine)."""
    errors = []
    if total is None or total <= 0:
        errors.append("Total classes conducted must be greater than 0.")
    if attended is None or attended < 0:
        errors.append("Classes attended cannot be negative.")
    elif total is not None and total > 0 and attended > total:
        errors.append("Classes attended cannot be more than total classes conducted.")
    if required is None or not (0 < required <= 100):
        errors.append("Required attendance must be above 0% and at most 100%.")
    return errors


def _pct(numerator, denominator):
    return float(Fraction(numerator, denominator) * 100)


def calculate(attended, total, required=75):
    """Return a dictionary with the full result. Raises ValueError for bad inputs."""
    errors = validate_inputs(attended, total, required)
    if errors:
        raise ValueError(" ".join(errors))
    attended, total = int(attended), int(total)
    r = Fraction(str(required))                       # percent as an exact fraction

    meets = Fraction(attended * 100, total) >= r      # exact comparison, no rounding
    result = {
        "attended": attended, "total": total, "required": float(required),
        "current_pct": _pct(attended, total), "meets": meets,
        "can_miss": 0, "pct_after_missing": None, "pct_if_one_more_missed": None,
        "need_to_attend": None, "pct_after_recovery": None, "recovery_possible": True,
    }
    if meets:
        can_miss = max(0, math.floor(Fraction(attended) * 100 / r) - total)
        result["can_miss"] = can_miss
        result["pct_after_missing"] = _pct(attended, total + can_miss)
        result["pct_if_one_more_missed"] = _pct(attended, total + can_miss + 1)
    elif r >= 100:
        result["recovery_possible"] = False           # can never reach 100% after missing a class
    else:
        need = math.ceil((r * total - 100 * attended) / (100 - r))
        result["need_to_attend"] = need
        result["pct_after_recovery"] = _pct(attended + need, total + need)
    return result
