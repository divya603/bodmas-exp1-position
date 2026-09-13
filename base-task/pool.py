"""
pool.py

Builds the v5 stimulus pool: 240 items, each on its own expression.

v5 vs v4 (changed 2026-09-13)
-----------------------------
  * No matched pairs. v4 took the step-1 and the step-3 version of an item from
    ONE expression, so every expression appeared twice in the pool. In v5 every
    item has its own expression, and error position is manipulated BETWEEN
    expressions, held level by the cell counts below. The cost: a position
    effect can now partly reflect which expressions support step 1 vs step 3,
    which the matched design ruled out.
  * The look-alike guard (lookalike.py). A B item may not name a rule whose
    statement plainly describes the error step. Every outside_bracket_first
    error is a + or - done before an adjacent × or ÷ whose other operand is a
    bracket, which a reader would also call "addition before division" and so
    on, although the model's operator rules cannot make that step. v4 had no
    such item only by chance.

Design
------
Two categories, one misconception per trace:
  A - the statement NAMES the misconception in the trace   -> agree
  B - the statement names a FOIL                           -> disagree

Grid, 240 items on 240 distinct expressions:
  A: present(6) x position(2)            = 12 cells x 10 items = 120
  B: present(6) x named(5) x position(2) = 60 cells x  2 items = 120

So each of the four (category x position) pools the frontend samples from holds
60 items, every rule is the true misconception in 40 items (10 per category x
position), and the present x named heatmap has 20 on each diagonal cell and 4
in each of the 30 off-diagonal cells.

A foil must pass two checks on the trace it is shown with:
  * the observer check: its marginal is at most UNSUPPORTED_MAX (0.35). Above
    that the trace positively supports the rule, so "disagree" is not a
    defensible key.
  * the look-alike guard above.

student_name and belief_statement are placeholders: the frontend reassigns the
24 names per participant (src/user/utils/sampleForm.js).

N_OPS stays 6. It was forced by the matched pairs (no 5-op expression supports
both step 1 and step 3 for outside_bracket_first); without pairs it is a choice.
"""

import json
import random
from collections import Counter
from itertools import combinations

from learner import MISCONCEPTION_FLIPS
from inference import posterior_over_profiles, marginal_rule_probability
from generator_constrained import generate_expression
from find_pairs import pairs_for_expression, N_OPS, POSITIONS
from lookalike import error_step_rules

IDS        = list(MISCONCEPTION_FLIPS.keys())
HYPOTHESES = [()] + [(m,) for m in IDS] + list(combinations(IDS, 2))

A_PER_CELL = 10   # per (present, position)         -> 120 A items
B_PER_CELL = 2    # per (present, named, position)  -> 120 B items

REFUTED_MAX     = 0.15
UNSUPPORTED_MAX = 0.35

# a cell that cannot be filled stops the build after this many fruitless draws
MAX_DRY_DRAWS = 300_000

STATEMENT_TEMPLATES = {
    'add_before_mul':        "{name} believes addition should be done before multiplication.",
    'add_before_div':        "{name} believes addition should be done before division.",
    'sub_before_mul':        "{name} believes subtraction should be done before multiplication.",
    'sub_before_div':        "{name} believes subtraction should be done before division.",
    'same_priority_rtl':     "{name} believes operations of the same priority should be worked right to left.",
    'outside_bracket_first': "{name} believes you should calculate outside the brackets before what's inside them.",
}

STUDENT_NAMES = [
    'Noah', 'Maya', 'Liam', 'Ava', 'Ethan', 'Zoe',
    'Mia', 'Lucas', 'Emma', 'Owen', 'Sofia', 'Caleb',
    'Ruby', 'Jonah', 'Isla', 'Felix', 'Nora', 'Dylan',
    'Priya', 'Marcus', 'Elena', 'Theo', 'Jasmine', 'Omar',
]


def _status(marginal):
    if marginal < REFUTED_MAX:
        return 'refuted'
    if marginal <= UNSUPPORTED_MAX:
        return 'unsupported'
    return 'high'


def foil_options(trace, true_m):
    """
    ({foil_rule: (status, marginal)}, [look-alikes dropped]) for the rules
    other than true_m. A rule is an option when the trace does not support it
    (status is not 'high') and its statement does not plainly describe the
    error step (lookalike.py).
    """
    post = posterior_over_profiles(trace, profiles=HYPOTHESES)
    visible = error_step_rules(trace)
    out, dropped = {}, []
    for f in IDS:
        if f == true_m:
            continue
        marg = marginal_rule_probability(post, f)
        st = _status(marg)
        if st == 'high':
            continue
        if f in visible:
            dropped.append(f)
            continue
        out[f] = (st, marg)
    return out, dropped


def build(seed=2026, verbose=True):
    rng = random.Random(seed)

    a_need = {(m, p): A_PER_CELL for m in IDS for p in POSITIONS}
    b_need = {(m, f, p): B_PER_CELL for m in IDS for f in IDS if f != m for p in POSITIONS}
    chosen = []                 # (cell key, expression, trace, foil_status, marginal)
    seen_expressions = set()
    draws = Counter()
    guard_drops = Counter()     # (present, foil): traces the look-alike guard kept out of a cell
    dry = 0

    def b_open(m, p):
        return [f for f in IDS if b_need.get((m, f, p), 0) > 0]

    while any(a_need.values()) or any(b_need.values()):
        for m in IDS:
            open_pos = tuple(p for p in POSITIONS if a_need[(m, p)] > 0 or b_open(m, p))
            if not open_pos:
                continue

            bp = 1.0 if m == 'outside_bracket_first' else 0.6
            expr = generate_expression(n_ops=N_OPS, bracket_prob=bp, rng=rng)
            draws[m] += 1
            dry += 1
            # An expression is used by exactly ONE item, so a participant can
            # never meet the same expression twice.
            if expr is None or expr in seen_expressions:
                continue

            # Every cell this expression could fill, scored by the share of
            # that cell still empty, so the scarcest cell wins (ties random).
            slots = []
            for p, trace in sorted(pairs_for_expression(expr, m, positions=open_pos).items()):
                if a_need[(m, p)] > 0:
                    slots.append((a_need[(m, p)] / A_PER_CELL, rng.random(),
                                  ('A', m, m, p), trace, None, None))
                wanted = b_open(m, p)
                if not wanted:
                    continue
                opts, dropped = foil_options(trace, m)
                for f in wanted:
                    if f in dropped:
                        guard_drops[(m, f)] += 1
                    if f in opts:
                        st, marg = opts[f]
                        slots.append((b_need[(m, f, p)] / B_PER_CELL, rng.random(),
                                      ('B', m, f, p), trace, st, marg))
            if not slots:
                continue

            _, _, key, trace, st, marg = max(slots, key=lambda s: s[:2])
            cat, _, f, p = key
            if cat == 'A':
                a_need[(m, p)] -= 1
            else:
                b_need[(m, f, p)] -= 1
            seen_expressions.add(expr)
            chosen.append((key, expr, trace, st, marg))
            dry = 0

        if verbose:
            print(f"  remaining items: A={sum(a_need.values()):3d}  "
                  f"B={sum(b_need.values()):3d}", end='\r')
        if dry > MAX_DRY_DRAWS:
            missing = {k: v for k, v in b_need.items() if v} | \
                      {k: v for k, v in a_need.items() if v}
            raise SystemExit(f"\nstalled with cells unfilled: {missing}")

    if verbose:
        print(f"  generated {len(seen_expressions)} expressions "
              f"({sum(draws.values())} draws)              ")
        print(f"  look-alike guard kept a trace out of a B cell {sum(guard_drops.values())} times: "
              f"{dict(guard_drops)}")

    # emit items: A then B, each ordered by present rule, named rule, position
    order = {m: i for i, m in enumerate(IDS)}
    chosen.sort(key=lambda c: (c[0][0], order[c[0][1]], order[c[0][2]], c[0][3]))
    items = []
    for (cat, m, probed, p), expr, trace, st, marg in chosen:
        name = STUDENT_NAMES[len(items) % len(STUDENT_NAMES)]
        it = {
            'id':                   f"{cat}{len(items):03d}",
            'category':             cat,
            'error_position':       p,
            'expression':           expr,
            'n_ops':                N_OPS,
            'misconceptions':       [m],
            'num_misconceptions':   1,
            'trace':                trace,
            'probed_misconception': probed,
            'statement_correct':    cat == 'A',
            'student_name':         name,
            'belief_statement':     STATEMENT_TEMPLATES[probed].format(name=name),
        }
        if cat == 'B':
            # recorded, NOT balanced: see the module docstring
            it['foil_status']      = st
            it['io_foil_marginal'] = round(marg, 4)
        items.append(it)
    return items


def summarise(items):
    print(f"\n{len(items)} items, {len({i['expression'] for i in items})} distinct expressions")
    print("  sampling pools (category x position), want 60 each:",
          dict(Counter((i['category'], i['error_position']) for i in items)))
    print("  trace lengths:", dict(Counter(len(i['trace']) for i in items)))

    print(f"\n  items per PRESENT rule (want 40: 10 per category x position):")
    for m in IDS:
        sub = [i for i in items if i['misconceptions'][0] == m]
        c = Counter((i['category'], i['error_position']) for i in sub)
        print(f"    {m:24s} n={len(sub):3d}  " +
              "  ".join(f"{cat}/pos{p}={c[(cat, p)]:2d}"
                        for cat in 'AB' for p in POSITIONS))

    print(f"\n  present x named heatmap occupancy (diagonal = A, want 20; "
          f"off-diagonal = B, want 4):")
    grid = Counter((i['misconceptions'][0], i['probed_misconception']) for i in items)
    empty = [(p, n) for p in IDS for n in IDS if grid[(p, n)] == 0]
    header = "".join(f"{n[:9]:>11s}" for n in IDS)
    print(f"    {'present \\ named':>24s}{header}")
    for p in IDS:
        print(f"    {p:>24s}" + "".join(f"{grid[(p, n)]:>11d}" for n in IDS))
    print(f"    EMPTY CELLS: {len(empty)}" + (f"  {empty}" if empty else "  (heatmap is full)"))

    print("\n  refutation status, RECORDED not balanced (expect uneven):")
    cs = Counter(i['foil_status'] for i in items if i['category'] == 'B')
    print(f"    {dict(cs)}")
    per = Counter((i['probed_misconception'], i['foil_status'])
                  for i in items if i['category'] == 'B')
    for f in IDS:
        print(f"    {f:24s} refuted={per[(f,'refuted')]:2d}  "
              f"unsupported={per[(f,'unsupported')]:2d}")

    look = [i['id'] for i in items if i['category'] == 'B'
            and i['probed_misconception'] in error_step_rules(i['trace'])]
    print(f"\n  B items naming a look-alike foil (want 0): {len(look)}")


if __name__ == '__main__':
    print("Building v5 pool...")
    items = build()
    summarise(items)
    with open('stimulus_pool.json', 'w', encoding='utf-8') as fh:
        json.dump(items, fh, ensure_ascii=False, indent=1)
    print("\nwrote stimulus_pool.json")
