"""
lookalike.py

Which misconception statements plainly describe a trace's error step, judged
from the surface of the two lines (which operation was done and what sits next
to it), not from the model.

Why this exists: the model's operator rules (add_before_mul etc.) only fire when
all three operands are plain numbers, and outside_bracket_first covers the same
move when the neighbouring operand is a bracket. So on

    4 + 8 ÷ (4 - 1)   ->   12 ÷ (4 - 1)

the model says add_before_div cannot have made the step, yet a reader would call
it "addition before division". A category-B item naming such a rule would have a
key that a reasonable participant rejects, so pool.py never names one as a foil
and verify.py asserts it.

Surface description of an error step that fires operator X:
  add/sub_before_mul/div   X is + or -, and an adjacent operator is × or ÷
  same_priority_rtl        the operator to X's left has X's priority
  outside_bracket_first    X is + or -, and an adjacent × or ÷ has a bracket
                           as its other operand
"""

import re

from generator_constrained import error_steps

_TOKEN = re.compile(r'\d+|[-+×÷()]')
_PRIO = {'+': 1, '-': 1, '×': 2, '÷': 2}
_OP_RULE = {('+', '×'): 'add_before_mul', ('+', '÷'): 'add_before_div',
            ('-', '×'): 'sub_before_mul', ('-', '÷'): 'sub_before_div'}


def _apply(a, op, b):
    a, b = int(a), int(b)
    if op == '+':
        return a + b
    if op == '-':
        return a - b
    if op == '×':
        return a * b
    q, r = divmod(a, b)
    return q if r == 0 else None


def _fired(p, n):
    """Indices into token list p of every operator whose firing turns p into n."""
    hits = []
    for i in range(1, len(p) - 1):
        if p[i] not in _PRIO or not (p[i - 1].isdigit() and p[i + 1].isdigit()):
            continue
        v = _apply(p[i - 1], p[i], p[i + 1])
        if v is None:
            continue
        out = p[:i - 1] + [str(v)] + p[i + 2:]
        j = i - 1
        # a bracket reduced to one number loses its parentheses in the same step
        if 0 < j < len(out) - 1 and out[j - 1] == '(' and out[j + 1] == ')':
            out = out[:j - 1] + [out[j]] + out[j + 2:]
        if out == n:
            hits.append(i)
    return hits


def visible_rules(prev, nxt):
    """Rules whose statement plainly describes the move prev -> nxt."""
    p, n = _TOKEN.findall(prev), _TOKEN.findall(nxt)
    out = set()
    for i in _fired(p, n):
        x = p[i]
        left = p[i - 2] if i >= 2 and p[i - 2] in _PRIO else None
        right = p[i + 2] if i + 2 < len(p) and p[i + 2] in _PRIO else None
        if x in ('+', '-'):
            if left in ('×', '÷'):
                out.add(_OP_RULE[(x, left)])
                if i >= 3 and p[i - 3] == ')':
                    out.add('outside_bracket_first')
            if right in ('×', '÷'):
                out.add(_OP_RULE[(x, right)])
                if i + 3 < len(p) and p[i + 3] == '(':
                    out.add('outside_bracket_first')
        if left is not None and _PRIO[left] == _PRIO[x]:
            out.add('same_priority_rtl')
    return out


def error_step_rules(trace):
    """Union of visible_rules over the trace's expert-illegal steps."""
    out = set()
    for k in error_steps(trace):
        out |= visible_rules(trace[k - 1], trace[k])
    return out
