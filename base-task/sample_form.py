"""
sample_form.py

Python twin of src/user/utils/sampleForm.js, which is what the live experiment
runs. Both draw one participant's 24 trials the same way with the same PRNG
(mulberry32), so a given seed yields the identical form in both languages.
Change one, change the other, then rerun the checks here.

The form (decided 2026-09-13):
  * four pools by category x error position (A/1, A/3, B/1, B/3), 60 items each
  * from each pool, one item drawn at random for each of the 6 misconceptions
    (the rule present in the trace) -> 24 trials: 12 agree / 12 disagree, 12
    at each position, every misconception present exactly 4 times (once per
    pool), every statement named exactly twice as the CORRECT statement
  * which foil a B trial names is left to the draw
  * trial order shuffled per participant
  * the 24 STUDENT_NAMES shuffled per participant, one per trial, so each name
    appears exactly once; the belief statement is rewritten to match
Every expression is unique in the pool, so no form repeats an expression.

    python3 sample_form.py            # checks over 500 seeds
    python3 sample_form.py --dump N   # [id, name] per trial for seeds 0..N-1, as JSON
"""

import json
import sys
from collections import Counter

from learner import MISCONCEPTION_FLIPS
from pool import STATEMENT_TEMPLATES, STUDENT_NAMES

IDS = list(MISCONCEPTION_FLIPS.keys())
POOLS = [('A', 1), ('A', 3), ('B', 1), ('B', 3)]
_M = 0xFFFFFFFF


class Mulberry32:
    """Bit-exact port of makeRng in sampleForm.js (32-bit unsigned arithmetic)."""

    def __init__(self, seed):
        self.s = seed & _M

    def next(self):
        self.s = (self.s + 0x6D2B79F5) & _M
        s = self.s
        t = ((s ^ (s >> 15)) * (1 | s)) & _M
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & _M)) & _M) ^ t
        return ((t ^ (t >> 14)) & _M) / 4294967296

    def choice(self, arr):
        return arr[int(self.next() * len(arr))]

    def shuffle(self, arr):
        for i in range(len(arr) - 1, 0, -1):
            j = int(self.next() * (i + 1))
            arr[i], arr[j] = arr[j], arr[i]
        return arr


def sample_form(pool, seed):
    rng = Mulberry32(seed)
    form = []
    for cat, pos in POOLS:
        for m in IDS:
            members = [it for it in pool if it['category'] == cat
                       and it['error_position'] == pos and it['misconceptions'][0] == m]
            form.append(rng.choice(members))
    rng.shuffle(form)
    names = rng.shuffle(list(STUDENT_NAMES))
    return [dict(it, student_name=names[i],
                 belief_statement=names[i] + it['belief_statement'][len(it['student_name']):])
            for i, it in enumerate(form)]


def check(pool, n_seeds=500):
    by_id = {it['id']: it for it in pool}
    want = Counter({(c, p, m): 1 for c, p in POOLS for m in IDS})
    uses = Counter()
    named_total, named_foil = Counter(), Counter()
    for seed in range(n_seeds):
        form = sample_form(pool, seed)
        assert len(form) == 24, (seed, len(form))
        assert Counter((it['category'], it['error_position'], it['misconceptions'][0])
                       for it in form) == want, seed
        assert sum(it['statement_correct'] for it in form) == 12, seed
        assert Counter(it['probed_misconception'] for it in form
                       if it['category'] == 'A') == Counter({m: 2 for m in IDS}), seed
        assert len({it['id'] for it in form}) == 24, seed
        assert len({it['expression'] for it in form}) == 24, seed
        assert sorted(it['student_name'] for it in form) == sorted(STUDENT_NAMES), seed
        for it in form:
            assert it['belief_statement'] == STATEMENT_TEMPLATES[it['probed_misconception']].format(
                name=it['student_name']), (seed, it['id'])
            src = by_id[it['id']]
            assert all(it[k] == src[k] for k in src if k not in ('student_name', 'belief_statement'))
        uses.update(it['id'] for it in form)
        tot = Counter(it['probed_misconception'] for it in form)
        foil = Counter(it['probed_misconception'] for it in form if it['category'] == 'B')
        named_total[(min(tot[m] for m in IDS), max(tot.values()))] += 1
        named_foil[max(foil.values())] += 1

    print(f"ALL CHECKS PASSED over {n_seeds} seeds")
    print("  every form: 24 trials, one per (category x position x misconception present),")
    print("  so 12 agree / 12 disagree, 12 per position, each misconception present 4 times,")
    print("  each statement named exactly twice as the correct one; 24 distinct items and")
    print("  expressions; each of the 24 names once; statements rewritten")
    exp = n_seeds * 24 / len(pool)
    print(f"  item usage: min {min(uses[i] for i in by_id)}  max {max(uses.values())}  "
          f"(expect about {exp:.0f} each; {sum(1 for i in by_id if uses[i] == 0)} items never drawn)")
    print(f"  most times one statement is named as a WRONG statement, per form: "
          f"{dict(sorted(named_foil.items()))}")
    print(f"  (fewest, most) times any statement is named in total, per form: "
          f"{dict(sorted(named_total.items()))}")


if __name__ == '__main__':
    pool = json.load(open('stimulus_pool.json', encoding='utf-8'))
    if len(sys.argv) > 2 and sys.argv[1] == '--dump':
        print(json.dumps([[[it['id'], it['student_name']] for it in sample_form(pool, s)]
                          for s in range(int(sys.argv[2]))]))
    else:
        check(pool)
