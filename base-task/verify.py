"""
verify.py

Independent checks on stimulus_pool.json. Recomputes everything from the
model rather than trusting the builder: traces are re-derived from the
expression, error positions re-tested for expert legality, foil marginals
re-run through the 22-hypothesis observer, and the look-alike guard re-applied.

Beyond the model checks it asserts the v5 design exactly: every expression used
by exactly one item, 60 items in each of the four (category x position) pools
the frontend samples from, and the present x named heatmap full (20 on each
diagonal cell, 4 in each of the 30 off-diagonal cells, 0 empty).

For every A item it also checks the error step itself: no other single rule
could have made it, and the named rule plainly describes it. So a correct
statement always names a misconception the work visibly uses.

It deliberately does NOT check refutation balance: foil_status is recorded but
not a factor, and the per-foil counts are expected to be lopsided. What IS
checked is that the stored status matches a fresh recomputation.

Run after any pool regeneration. Exits non-zero on any failure.
"""

import json
import sys
from collections import Counter

from parser import build_dag
from traces import generate_traces, _next_dags
from misconceptions import dag_to_str
from distance import correct_answer
from learner import MISCONCEPTION_FLIPS
from inference import posterior_over_profiles, marginal_rule_probability
from generator_constrained import validate_trace, error_steps
from lookalike import error_step_rules
from pool import (HYPOTHESES, STATEMENT_TEMPLATES, POSITIONS, N_OPS,
                  UNSUPPORTED_MAX, _status, A_PER_CELL, B_PER_CELL)

IDS = list(MISCONCEPTION_FLIPS.keys())
POOL_SIZE = {'A': A_PER_CELL * len(IDS), 'B': B_PER_CELL * len(IDS) * (len(IDS) - 1)}
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


def one_step(line, rules):
    """Every line a learner holding `rules` could write next."""
    return {dag_to_str(d) for d in _next_dags(build_dag(line), list(rules))}


def main(path='stimulus_pool.json'):
    items = json.load(open(path, encoding='utf-8'))
    print(f"verifying {len(items)} items from {path}\n")

    check(len({i['id'] for i in items}) == len(items), "duplicate item ids")

    for it in items:
        tag = it['id']
        trace, expr = it['trace'], it['expression']
        true_m = it['misconceptions'][0]

        # structure
        check(it['num_misconceptions'] == 1 and len(it['misconceptions']) == 1,
              f"{tag}: not exactly one misconception")
        check(len(trace) == N_OPS + 1, f"{tag}: trace has {len(trace)} lines, want {N_OPS+1}")
        check(trace[0] == expr, f"{tag}: trace does not start at the expression")
        check(len(trace[-1].split()) == 1, f"{tag}: trace does not reduce to a number")

        # displayable arithmetic
        check(validate_trace(trace), f"{tag}: trace fails validate_trace ({trace})")

        # the trace is really generable by a learner holding exactly true_m
        legal = generate_traces(build_dag(expr), [true_m])
        check(trace in legal, f"{tag}: trace is not generable by {true_m}")

        # exactly one expert-illegal move, at the declared position
        errs = error_steps(trace)
        check(errs == [it['error_position']],
              f"{tag}: error steps {errs}, declared position {it['error_position']}")

        # the misconception actually changes the answer
        expert = generate_traces(build_dag(expr), [])
        check(trace[-1] != correct_answer(expert),
              f"{tag}: learner answer equals the expert answer")

        # statement wiring
        probed = it['probed_misconception']
        check(it['belief_statement'] ==
              STATEMENT_TEMPLATES[probed].format(name=it['student_name']),
              f"{tag}: belief statement does not match probed rule / name")

        post = posterior_over_profiles(trace, profiles=HYPOTHESES)
        visible = error_step_rules(trace)
        if it['category'] == 'A':
            check(probed == true_m and it['statement_correct'] is True,
                  f"{tag}: A item probed {probed} but trace holds {true_m}")
            check(marginal_rule_probability(post, probed) > 0.99,
                  f"{tag}: A item true-rule marginal too low")
            check('foil_status' not in it, f"{tag}: A item carries a foil_status")
            # the error step is the named misconception and nothing else
            for k in errs:
                others = [r for r in IDS
                          if r != true_m and trace[k] in one_step(trace[k - 1], [r])]
                check(not others, f"{tag}: error step {k} could also be made by {others}")
            check(probed in visible,
                  f"{tag}: error step does not visibly show {probed} (reads as {sorted(visible)})")
        else:
            check(probed != true_m and it['statement_correct'] is False,
                  f"{tag}: B item probes its own true rule")
            marg = marginal_rule_probability(post, probed)
            check(abs(marg - it['io_foil_marginal']) < 1e-3,
                  f"{tag}: stored marginal {it['io_foil_marginal']} != recomputed {marg:.4f}")
            check(marg <= UNSUPPORTED_MAX,
                  f"{tag}: foil marginal {marg:.3f} above {UNSUPPORTED_MAX}, not a clean foil")
            # status is recorded, not balanced, but it must still be correct
            check(_status(marg) == it['foil_status'],
                  f"{tag}: foil_status {it['foil_status']} but marginal {marg:.3f} says {_status(marg)}")
            # look-alike guard: the foil must not plainly describe the error step
            check(probed not in visible,
                  f"{tag}: foil {probed} plainly describes the error step (look-alike)")

    # every expression is used by exactly one item, so no one can meet it twice
    per_expr = Counter(i['expression'] for i in items)
    check(all(v == 1 for v in per_expr.values()),
          f"expressions used more than once: {[e for e, v in per_expr.items() if v > 1][:3]}")

    # the four pools the frontend samples from
    pools = Counter((i['category'], i['error_position']) for i in items)
    want = Counter({(c, p): POOL_SIZE[c] for c in 'AB' for p in POSITIONS})
    check(pools == want, f"sampling pools {dict(pools)}, want {dict(want)}")

    ca = Counter((i['misconceptions'][0], i['error_position'])
                 for i in items if i['category'] == 'A')
    check(len(ca) == 12 and set(ca.values()) == {A_PER_CELL},
          f"A cells (present x position) not all {A_PER_CELL}: {sorted(set(ca.values()))}")

    cb = Counter((i['misconceptions'][0], i['probed_misconception'], i['error_position'])
                 for i in items if i['category'] == 'B')
    check(len(cb) == 60 and set(cb.values()) == {B_PER_CELL},
          f"B cells (present x named x position) not all {B_PER_CELL}: "
          f"{len(cb)} cells, sizes {sorted(set(cb.values()))}")

    # per present rule: 40 items, 10 per category x position
    for m in IDS:
        sub = [i for i in items if i['misconceptions'][0] == m]
        check(len(sub) == 40, f"{m}: {len(sub)} items, want 40")
        c = Counter((i['category'], i['error_position']) for i in sub)
        check(set(c.values()) == {10} and len(c) == 4,
              f"{m}: category x position split is {dict(c)}, want 10 each")

    # the heatmap has no empty boxes
    grid = Counter((i['misconceptions'][0], i['probed_misconception']) for i in items)
    empty = [(p, n) for p in IDS for n in IDS if grid[(p, n)] == 0]
    check(not empty, f"heatmap has {len(empty)} empty cells: {empty[:5]}")
    diag = {grid[(m, m)] for m in IDS}
    off = {grid[(p, n)] for p in IDS for n in IDS if p != n}
    check(diag == {20}, f"diagonal cells not all 20: {sorted(diag)}")
    check(off == {4}, f"off-diagonal cells not all 4: {sorted(off)}")

    if fails:
        print(f"FAILED - {len(fails)} problem(s):")
        for f in fails[:25]:
            print("  -", f)
        if len(fails) > 25:
            print(f"  ... and {len(fails)-25} more")
        sys.exit(1)

    nums = [int(n) for i in items for line in i['trace']
            for n in line.replace('(', ' ').replace(')', ' ').split()
            if n.lstrip('-').isdigit()]
    marg = [i['io_foil_marginal'] for i in items if i['category'] == 'B']
    print("ALL CHECKS PASSED")
    print(f"  {len(items)} items / {len(per_expr)} expressions, each used once")
    print(f"  sampling pools: {POOL_SIZE['A']} per A position, {POOL_SIZE['B']} per B position")
    print(f"  every trace: {N_OPS} steps, exactly 1 expert-illegal move, at step "
          f"{POSITIONS[0]} or {POSITIONS[1]}")
    print(f"  A error steps: only the named rule could make them, and it visibly shows")
    print(f"  B foils: none plainly describes the error step (look-alike guard)")
    print(f"  present x named heatmap: 0 empty cells, diagonal 20, off-diagonal 4")
    print(f"  foil marginals: min {min(marg):.3f}  max {max(marg):.3f}  "
          f"mean {sum(marg)/len(marg):.3f}  (status recorded, NOT balanced)")
    print(f"  numbers shown: min {min(nums)}  max {max(nums)}  "
          f"(no negatives, no decimals, no zero)")


if __name__ == '__main__':
    main()
