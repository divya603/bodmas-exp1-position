"""
practice.py

Builds the 3 practice items (src/user/data/practice_items.json) and checks them
against the model. Design (user, 2026-09-13), shown in this fixed order:
  P1  statement CORRECT, error at step 1
  P2  statement WRONG,   error at step 3; the work rules the statement out
      (the student had a chance to show it and did not)
  P3  statement WRONG,   error at step 1; the problem gives no chance to show
      the stated misconception at all
After each answer the practice screen highlights the error step with its note
and shows the feedback paragraph.

The traces are fixed (the user approved these exact items), so this script
checks rather than generates them:
  * no practice expression is in the pool, so a practice problem never reappears
  * each trace is generable by its true misconception, reaches a wrong answer,
    has exactly one expert-illegal step, at the declared position, and that
    step reads as the true misconception only (lookalike.py)
  * each B statement passes the pool's foil rules (observer marginal and the
    look-alike guard) with the intended status, plus the specific claim its
    feedback makes
  * practice names are distinct and not among the 24 task names

    cd base-task && python3 practice.py
"""

import json
import os

from parser import build_dag
from traces import generate_traces
from distance import correct_answer
from inference import transition_prob
from generator_constrained import error_steps, validate_trace
from lookalike import error_step_rules
from pool import STATEMENT_TEMPLATES, STUDENT_NAMES, foil_options, N_OPS

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = os.path.join(HERE, 'stimulus_pool.json')
OUT = os.path.join(HERE, '..', 'src', 'user', 'data', 'practice_items.json')

PRACTICE = [
    {
        'id': 'P1', 'student_name': 'Tara', 'position': 1,
        'misconception': 'add_before_mul', 'probed': 'add_before_mul',
        'trace': [
            '1 + 7 × 4 ÷ 2 + 4 - 2 × 3',
            '8 × 4 ÷ 2 + 4 - 2 × 3',
            '32 ÷ 2 + 4 - 2 × 3',
            '16 + 4 - 2 × 3',
            '20 - 2 × 3',
            '20 - 6',
            '14',
        ],
        'note': 'the student added 1 + 7 before multiplying 7 × 4',
        'feedback': (
            'The highlighted step shows the student adding 1 + 7 before doing 7 × 4. That is '
            'exactly the misconception the statement describes, so the statement explains the '
            'work and the right answer would be to agree.'),
    },
    {
        'id': 'P2', 'student_name': 'Sam', 'position': 3,
        'misconception': 'sub_before_div', 'probed': 'add_before_div', 'kind': 'refuted',
        'ruled_out_at': 4,
        'trace': [
            '7 × 6 - 4 ÷ 2 + 10 × 4 ÷ 2',
            '42 - 4 ÷ 2 + 10 × 4 ÷ 2',
            '42 - 4 ÷ 2 + 40 ÷ 2',
            '38 ÷ 2 + 40 ÷ 2',
            '19 + 40 ÷ 2',
            '19 + 20',
            '39',
        ],
        'note': 'the student subtracted 42 - 4 before dividing 4 ÷ 2',
        'feedback': (
            "The student's mistake is in the highlighted step: they subtracted (42 - 4) before "
            'dividing (4 ÷ 2). The statement says they add before dividing, which is a different '
            'mistake. The work even argues against it: in the next step, with 38 ÷ 2 + 40 ÷ 2, '
            'the student divided 38 ÷ 2 first, where someone who adds before dividing would have '
            'added 2 + 40. So the statement does not explain the work, and the right answer would '
            'be to disagree.'),
    },
    {
        'id': 'P3', 'student_name': 'Kai', 'position': 1,
        'misconception': 'same_priority_rtl', 'probed': 'sub_before_div', 'kind': 'unsupported',
        'absent_op': '-',
        'trace': [
            '10 × 6 ÷ 3 × 5 + 2 + 5 + 11',
            '10 × 6 ÷ 15 + 2 + 5 + 11',
            '60 ÷ 15 + 2 + 5 + 11',
            '4 + 2 + 5 + 11',
            '6 + 5 + 11',
            '11 + 11',
            '22',
        ],
        'note': 'the student worked right to left, doing 3 × 5 before 6 ÷ 3',
        'feedback': (
            "The student's mistake is in the highlighted step: they worked right to left, doing "
            '3 × 5 before 6 ÷ 3. The statement says they subtract before dividing, but there is no '
            'subtraction anywhere in this problem, so that belief cannot explain anything in the '
            'work. The right answer would be to disagree.'),
    },
]

# the order the user asked for: (statement correct, error position)
DESIGN = [(True, 1), (False, 3), (False, 1)]


def first_ruled_out(trace, rules):
    """First step a learner holding `rules` could not have made, or None."""
    for k in range(1, len(trace)):
        if transition_prob(build_dag(trace[k - 1]), trace[k], list(rules), 0.0) == 0:
            return k
    return None


def check(spec, pool_exprs):
    t, m, f, pos, tag = spec['trace'], spec['misconception'], spec['probed'], spec['position'], spec['id']
    assert t[0] not in pool_exprs, f"{tag}: expression is in the pool"
    assert len(t) == N_OPS + 1 and len(t[-1].split()) == 1, f"{tag}: not a full {N_OPS}-step trace"
    assert validate_trace(t), f"{tag}: trace fails validate_trace"
    dag = build_dag(t[0])
    assert t in generate_traces(dag, [m]), f"{tag}: trace is not generable by {m}"
    assert t[-1] != correct_answer(generate_traces(dag, [])), f"{tag}: learner answer is correct"
    assert error_steps(t) == [pos], f"{tag}: error steps {error_steps(t)}, want [{pos}]"
    assert error_step_rules(t) == {m}, f"{tag}: error step reads as {error_step_rules(t)}"
    assert spec['student_name'] not in STUDENT_NAMES, f"{tag}: name is also a task name"
    if f != m:
        opts, _ = foil_options(t, m)
        assert f in opts, f"{tag}: {f} fails the foil rules on this trace"
        assert opts[f][0] == spec['kind'], f"{tag}: {f} is {opts[f][0]}, want {spec['kind']}"
    if 'ruled_out_at' in spec:
        k = first_ruled_out(t, [m, f])
        assert k == spec['ruled_out_at'], f"{tag}: {m}+{f} ruled out at step {k}"
    if 'absent_op' in spec:
        assert spec['absent_op'] not in t[0], f"{tag}: {spec['absent_op']} appears in the problem"


def build_item(spec):
    m, f, pos, name = spec['misconception'], spec['probed'], spec['position'], spec['student_name']
    item = {
        'id':                   spec['id'],
        'category':             'practice',
        'error_position':       pos,
        'expression':           spec['trace'][0],
        'n_ops':                N_OPS,
        'trace':                spec['trace'],
        'misconceptions':       [m],
        'num_misconceptions':   1,
        'probed_misconception': f,
        'statement_correct':    f == m,
        'student_name':         name,
        'belief_statement':     STATEMENT_TEMPLATES[f].format(name=name),
        'error_steps':          [{'trace_index': pos, 'misconception': m, 'note': spec['note']}],
        'feedback':             spec['feedback'],
    }
    if f != m:
        item['foil_status'] = spec['kind']
    return item


def main():
    pool_exprs = {i['expression'] for i in json.load(open(POOL, encoding='utf-8'))}
    for spec in PRACTICE:
        check(spec, pool_exprs)
    assert [(s['probed'] == s['misconception'], s['position']) for s in PRACTICE] == DESIGN
    assert len({s['student_name'] for s in PRACTICE}) == len(PRACTICE), "practice names repeat"

    items = [build_item(s) for s in PRACTICE]
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(items, fh, ensure_ascii=False, indent=1)
    print("ALL PRACTICE CHECKS PASSED")
    for it in items:
        print(f"  {it['id']}  {'correct' if it['statement_correct'] else 'wrong  '}  "
              f"step {it['error_position']}  true {it['misconceptions'][0]:18s} "
              f"named {it['probed_misconception']:18s} {it.get('foil_status', '')}")
    print(f"wrote {os.path.relpath(OUT, HERE)}")


if __name__ == '__main__':
    main()
