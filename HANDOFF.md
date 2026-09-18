# BODMAS Experiment 1 (error position): Handoff

A complete, from-scratch orientation for a model picking this up cold. Read this instead of any
conversation history.

> **⚠️ STANDING INSTRUCTION TO EVERY AGENT: keep this file current.** As you complete work (new
> scripts, figures, findings, decisions, payments, deploys), update the relevant sections either as
> you go or at the latest before your session ends. This file is the single source of truth; the
> next session must be able to pick up cold from it alone.

---

## 0. What this repo is

**Repo:** `divya603/bodmas-exp1-position` (GitHub). **Experiment 1 of 3.** It asks whether people
can tell which order-of-operations misconception a student holds from the student's written work,
and whether it matters **where in the work the error happens (step 1 vs step 3)**.

The repo holds one stimulus pool, the model that generates it, a Bayesian ideal observer run over
it, three observer figures, and the Smile/Vue web experiment. **No human data and no LLM data exist
yet for this experiment.**

Provenance, in one line: split out on 2026-09-13 from `divya603/bodmas-model`, which archives an
earlier, now-dropped study (a different 480-item pool with 2-misconception trials). Nothing from that
study is needed here and none of its results apply to this pool. Experiment 2 (hidden steps) lives in
its own repo.

### The task (one trial)
A participant sees a **math expression**, a **student's step-by-step work** containing exactly one
order-of-operations misconception, and a **belief statement** claiming the student holds a
particular misconception. They answer **YES or NO** with the **D and F keys only** (since
2026-09-18 the on-screen YES / NO boxes are labels showing which key is which, not clickable
buttons): does the statement describe what the student believes? It is about the work, NOT whether
the final answer is right. **YES = agree.** (Since 2026-09-16, at the user's request, as in
Experiment 2; before that a 6-point Likert scale was collapsed at >= 4. The scale was a leftover
from an earlier design with 2-misconception items; every item here has one misconception and a
clear answer.)

### The 6 misconceptions
| id | meaning |
|---|---|
| `add_before_mul` | does `+` before an adjacent `×` |
| `add_before_div` | does `+` before an adjacent `÷` |
| `sub_before_mul` | does `-` before an adjacent `×` |
| `sub_before_div` | does `-` before an adjacent `÷` |
| `same_priority_rtl` | evaluates equal-priority ops right-to-left instead of left-to-right |
| `outside_bracket_first` | must finish everything outside a bracket before resolving its contents |

`outside_bracket_first` is a **preference**, not a permission: a learner holding it may not enter a
bracket while literal-literal work remains outside. It is the only rule that REMOVES options rather
than adding them, and that asymmetry shows up repeatedly below.

---

## 1. First-time setup on a new machine or clone

Run these in order, once, right after cloning:
```bash
git clone https://github.com/divya603/bodmas-exp1-position.git
cd bodmas-exp1-position
npm run get_secrets          # fetch the 5 gitignored lab files from codec-lab/smile-secrets
npm run upload_config        # push the app + deploy config into THIS repo's GitHub secrets
npm run setup_project        # npm install + git hooks (post-commit / post-checkout)
pip install -r base-task/requirements.txt
(cd base-task && python3 verify.py)   # must print ALL CHECKS PASSED
npm run force_deploy         # first deployment (gh workflow run deploy.yml on the current branch)
```

What each secrets step does:
- **`npm run get_secrets`** (`scripts/get_secrets.sh`) downloads, via `gh api`, from the private
  lab repo `codec-lab/smile-secrets`: `env/.env.local` (Firebase app config), `env/.env.deploy.local`
  (lab-server SSH details), `env/.env.docs.local`, `firebase/.service-account-key.json` (needed by
  `npm run getdata`), and `scripts/get_recruitment_data.mjs` (needed by `npm run getrecruitment`).
  All five are gitignored and must never be committed. Needs `gh` logged in with access to that repo
  (divya603 has access, checked 2026-09-13; otherwise ask Mark). Fallback without access: copy the
  same five files from the old checkout `~/Desktop/NYU/Darpa/Bodmas_model/`.
- **`npm run upload_config`** (`scripts/update_config.sh`) pushes `env/.env.local` as
  `SECRET_APP_CONFIG` and every line of `env/.env.deploy.local` as its own secret
  (`EXP_DEPLOY_HOST`, `EXP_DEPLOY_KEY`, `EXP_DEPLOY_PATH`, `EXP_DEPLOY_PORT`, `EXP_DEPLOY_USER`,
  `SLACK_WEBHOOK_URL`, `SLACK_WEBHOOK_ERROR_URL`) to whatever repo `origin` points at. Only needed
  once per repo, not once per clone.

**Status as of 2026-09-13: setup done and the pipeline deploys.** All 8 secrets are uploaded to
this repo (`gh secret list`), and the manual deploy run 34770142359 ran its `deploy` job (1m12s,
not skipped). The main URL returns HTTP 200. The lab Slack message was not checked.

`deploy.yml` handles missing secrets gracefully: its `check-secrets` job SKIPS the `deploy` job and
the run still shows GREEN, with a "secrets are not configured, skipping deploy" notice. The initial
push did exactly that (5s run). So on any new repo or fork, confirm with `gh run list` then
`gh run view <id>` that the **`deploy` job itself ran**.

⚠️ The first deployment only proves the pipeline works. **Until §8 item 1 lands, the deployed site
serves the OLD study's pool and practice items**, so do not share its URL with anyone.

Node: `.node_version` pins 20.18.1; Node 24 has been working locally. If `npm install` misbehaves,
switch with `nvm use 20`.

What changes automatically because this is a new repo:
- **The deploy URL.** Path is `/<owner>/<repo>/<branch>/`, so main deploys to
  `https://www.codec-lab.org/divya603/bodmas-exp1-position/main/`, and the short codename URL is
  derived from the same path (printed in the deploy log). Any Prolific link must point here.
- **Where the data lands.** Firestore's `projectRef` (`src/core/config.js`) is derived from the
  deploy path, so this experiment's data is stored under its own key and cannot mix with the old
  study's data.

---

## 2. Repository map

```
base-task/         The model + the pool + the ideal observer (Python). See §3, §4.
analysis-Bayesian/ Ideal-observer figures. See §5.
src/               The Smile/Vue web experiment. User code in src/user/. See §6.
scripts/           Smile deploy/data scripts.
public/            consent-form.pdf, debrief.pdf served by the frontend.
env/, firebase/    Smile config. env/.env is tracked defaults; env/*.local are secrets (untracked).
data/              Pulled participant data lands here. Participant files are gitignored.
docs/ tests/ plugins/ analysis/ plans/   Smile framework infrastructure, not ours. Leave alone.
```

---

## 3. The model and the pool (`base-task/`)

### Model core
- **`dag.py`** FlatDAG representation of an expression (atoms + op nodes, shared references).
- **`parser.py`** `build_dag(expr)`. Folds signed-number literals so re-parsing intermediate trace
  strings matches `_eval`'s representation.
- **`pattern_matcher.py`** classifies 3-node "windows" into Tables 1 to 6.
- **`learner.py`** `MISCONCEPTION_FLIPS`: each misconception's bidirectional `to_true`/`to_false`
  validity flips. A learner is a list of misconception ids.
- **`valid_actions.py`**, **`traces.py`** `generate_traces(dag, misconceptions)` simulates a learner
  and returns ALL step-by-step traces it could produce. Includes the `is_zero_divide` guard.
- **`distance.py`** `correct_answer()`, `tree_edges()`, `diagnostic_traces()`.
- **`generator.py`** the original random expression generator (imported by the constrained one).
- **`inference.py`** `posterior_over_profiles(trace)` and `marginal_rule_probability()`. The
  likelihood is one factor per step, `P(s1..sT | L, s0) = prod_t pi_L(s_{t+1} | s_t)`, with
  `pi_L` uniform over the moves learner L may legally make. **`DEFAULT_EPSILON = 0.0`**: every pool
  trace is generated deterministically by one of the hypotheses, so there is no slip process and a
  nonzero epsilon is a misspecified likelihood. At epsilon 0 a forbidden step eliminates its
  hypothesis outright.
- `Bodmas_Modeling.pdf` is the written description of the model.

### The constrained generator
- **`generator_constrained.py`** draws numbers constructively left to right with one step of
  operator lookahead. Guarantees, verified 0 violations in 5000 draws: subtraction operands ordered,
  division exact with a proper divisor (no `÷ 1`, no `n ÷ n`), `×` operands <= 6, no run of more
  than 2 equal numbers. Also holds:
  - `validate_trace()`: non-negative integers only, nothing over 999, no zero anywhere. Zero is
    banned because `× 0` collapses the expression and `÷ 0` sits in the work as an operation the
    student visibly never performs. Literal constraints alone are not enough (`5 - 3 × 6` goes
    negative once evaluated, and evaluation order is the learner's choice), so this check on the
    displayed trace is the real gate.
  - `error_steps(trace)`: **the correct expert-legality test**. For each step it asks whether an
    expert could produce that line FROM THE IMMEDIATELY PRECEDING LINE
    (`expert_next` -> `_next_dags(build_dag(prev), [])`).
    ⚠️ Do NOT reimplement this as expert trace-edge membership. Once the learner diverges, every
    later state is off the expert's trace tree, so edge membership marks all subsequent steps as
    errors and no trace ever looks like it has exactly one.
- **`find_pairs.py`** `pairs_for_expression(expr, misconception)` returns `{position: trace}` for
  each requested position the expression supports. A trace qualifies when it finishes in `N_OPS`
  steps, reduces to a number, reaches a DIFFERENT answer than the expert, passes `validate_trace`,
  and has EXACTLY ONE expert-illegal move, at the requested position.
- **`lookalike.py`** `error_step_rules(trace)`: the statements that plainly describe a trace's
  error step, read from the surface of the two lines (which operation was done, what sits next to
  it), not from the model. Drives the look-alike guard (§3 item 6).

### The pool: `pool.py` -> `stimulus_pool.json`
**v5: 240 items, each on its own expression** (rebuilt 2026-09-13; rebuilt again 2026-09-17 with
**5 operators instead of 6**, at the user's request, because the expressions read as too long). Seed 2026, reproducible
byte-for-byte. v4 used 120 matched pairs (one expression supplying both the step-1 and the step-3
version); the user dropped the pairs so that no expression repeats, and the look-alike guard was
added at the same time.

Design factors:
- **Misconception present** (6 levels). Each is the true misconception in exactly 40 items.
- **Error position** (step 1 or step 3), manipulated BETWEEN expressions and held level by the cell
  counts below. See §3 item 2 for what that costs.
- **What the statement names**: category **A** names the present misconception (correct answer
  agree), category **B** names an absent foil (correct answer disagree).

Grid:
```
A: present(6) x position(2)            = 12 cells x 10 items = 120
B: present(6) x named(5) x position(2) = 60 cells x  2 items = 120
```
Each rule's 40 items are 10 each of (A, step 1), (A, step 3), (B, step 1), (B, step 3), and within
its 20 B items the named foil is balanced 5 foils x 2 positions x 2 items. That last constraint is
why the **present x named heatmap has no empty cells**: diagonal 20 and off-diagonal 4 when pooled,
10 and 2 when split by position.

Other guarantees: 240 distinct expressions, each used by exactly one item, so a participant can
never meet an expression twice. The four sampling pools (A/step 1, A/step 3, B/step 1, B/step 3)
hold 60 items each. Every trace is 5 steps (6 lines: the expression plus 5) with exactly one
expert-illegal move. Every learner answer differs from the correct answer. Numbers shown span 1 to
792: no negatives, decimals or zeros. No foil is ever probed on a trace generated by that same rule. In every A item the error
step could be made by the named rule and by no other single rule, and it visibly shows that rule.
No B item names a look-alike foil.

Worked example, two category-A items for add_before_mul (statement "believes addition should be
done before multiplication"), on different expressions since v5:
```
error at step 1 (A000)                  error at step 3 (A010)
6 + (8 ÷ 4) + 10 × 5 + 9                6 × 3 × 3 + (2 × 5) + 11
= 6 + (8 ÷ 4) + 10 × 14      <- 5+9     = 6 × 3 × 3 + 10 + 11
= 6 + (8 ÷ 4) + 140                     = 6 × 3 × 3 + 21
...                                     = 6 × 3 × 24                <- 3+21
```

Item fields: `id, category, error_position, expression, n_ops, misconceptions, num_misconceptions,
trace, probed_misconception, statement_correct, student_name, belief_statement`, plus on B items
only `foil_status` and `io_foil_marginal`. (`pair_id` and `which_target` were dropped in v5.)
`student_name` and `belief_statement` are placeholders: the frontend sampler reassigns the names.

**Answer-leak fields** (never show a solver or a participant): `statement_correct, misconceptions,
probed_misconception, category, num_misconceptions, foil_status, io_foil_marginal`.

### ⚠️ Things about this pool that will bite you
1. **5 operators is the floor; 4 would empty a cell.** The pool ran at 6 ops until 2026-09-17
   because v4's matched pairs needed one expression to support BOTH step 1 and step 3 for
   `outside_bracket_first`, and over 2500 bracketed expressions that happens **0 times at 4 ops, 0
   at 5 ops, 32 at 6 ops**. v5 has no pairs, so each expression supplies one position only, and 5
   ops is enough: measured 2026-09-17 over 4000 draws per rule, every rule yields both positions
   (the scarcest is `outside_bracket_first`, 208 at step 1 and 171 at step 3) and all 5 foils stay
   available in every cell. **Do not go to 4 ops**: there `outside_bracket_first` never reaches step
   3 at all, which silently empties that cell.
2. **Position is SELECTED, not constructed.** Nothing places the error. A misconception is a
   substitution at one window: it decides what happens when the learner touches that window, not
   when. One expression plus one misconception yields many valid traces (75 for the 6-op expression
   `4 + 9 × 4 ÷ 2 × (3 + 10) × 2` under add_before_mul), with the single error landing anywhere from
   step 1 up to the second-to-last step (the last step is forced). The builder filters for step 1 and step 3. Left unconstrained, position is
   confounded with rule (sub<÷ errors land early, add<÷ errors land late), which is why it is fixed
   by design (10 items per rule x position x category).
   **Since v5, position is also between expressions**: a step-1 and a step-3 item never share an
   expression, so a position effect in people can partly reflect which expressions support each
   position. v4's matched pairs ruled that out; the user chose non-repeating expressions instead
   (2026-09-13). Analyses should include item as a random effect.
3. **`foil_status` is RECORDED but NOT BALANCED.** Refutation (refuted vs unsupported foil) is not a
   factor in this experiment. Pool-wide (5-op v5) it is 52 refuted / 68 unsupported, but per foil it
   is lopsided: `sub_before_mul` 5/15, `add_before_div` 7/13, `same_priority_rtl` 12/8.
   **Never split a figure or analysis by `foil_status`**; the cells go lopsided and empty.
4. **The pool excludes the hardest foils.** `pool.py: foil_options()` drops any foil whose marginal
   exceeds 0.35 as "not a clean foil", so no B item ever names a rule the trace actually supports.
   See the finding in §5. Decide before running participants whether that exclusion is wanted.
5. **Most of the evidence sits in two of the 5 steps.** Counting how many of the 22 hypotheses each
   step eliminates, summed over all 240 traces (5-op pool, 2026-09-17): step 1 2607, step 2 406,
   step 3 1151, step 4 104, step 5 0. Steps 1 and 3 (the error positions) carry 88%; the last step
   carries none because it is forced. Participants read five steps of which roughly two matter.
6. **`outside_bracket_first` errors LOOK LIKE the operator rules; guarded since v5.** Its only
   illegal move is doing a `+`/`-` before an adjacent `×`/`÷` whose other operand is an unresolved
   bracket, e.g. `4 + 8 ÷ (4 - 1)` -> `12 ÷ (4 - 1)`. The four operator rules only fire when all
   three operands are plain numbers, so the model says `add_before_div` cannot make that step
   (observer P <= 0.25), yet a reader would call it "addition before division". A B item naming the
   look-alike would have a key a reasonable participant rejects; v4 had none only by chance. The
   guard: `pool.py: foil_options()` drops any foil in `lookalike.error_step_rules(trace)`, and
   `verify.py` asserts no B item names one. The surface test is deliberately broad (it also counts
   doing the right-hand one of two same-priority ops first as "right to left", even where order does
   not matter). That only removes foil options: in the v5 build it kept a trace out of a B cell 46
   times, and every cell still filled.

### Verification: `verify.py`
Independent verifier, run after ANY regeneration (`cd base-task && python3 verify.py`, exits
non-zero on failure). It re-derives everything from the model rather than trusting the builder:
regenerates each trace from its expression, re-tests every step for expert legality, re-runs the
22-hypothesis observer, and re-checks statement wiring, that every expression is used exactly
once, the four 60-item sampling pools, and the exact cell counts that guarantee a full heatmap
(asserting 0 empty cells). For A items it checks that no other single rule could make the error step
and that the named rule visibly describes it; for B items it applies the look-alike guard.
Currently ALL CHECKS PASSED (v5, 2026-09-13). It deliberately does NOT check refutation balance,
only that each stored status matches a fresh recomputation.

---

## 4. The Bayesian ideal observer

`base-task/bayes.py` -> `base-task/bayes_per_item.json`. One row per item: probed marginal, binary
judgment, correctness, MAP hypothesis.

The observer weighs **22 hypotheses** (expert + 6 singletons + 15 pairs) at epsilon 0. No item is
ever generated by a pair; the pairs exist so the observer can represent "the student might ALSO hold
rule f", which is the only way "no evidence either way" can differ from "had a chance to show it and
demonstrably did not". A 7-hypothesis space collapses every A item to exactly 1.000 and every B item
to exactly 0.000. Keep 22.

The observer sees only the trace. For any trace it computes one posterior, which yields a marginal
for each of the six rules; the belief statement is NOT an input and only picks which marginal is
read off:
```
P(L | s0..s6) ∝ P(L) · prod_t pi_L(s_{t+1} | s_t)
P(R ∈ L | trace) = sum_L P(L | trace) · [R ∈ L]
```
So category A vs B is not a difference in the observer's computation. The labels exist on the Bayes
side only so it can be scored on the same items as humans and LLMs, who do see the statement.

**Result: 240/240 = 100%.**
- A items: marginal on the present rule exactly 1.000 in all 120, at both positions, all six rules.
- B items: P(agree) 0.000; marginal min 0.000 / mean 0.137 / max 0.333, over only 10 distinct
  values.
- **Error position does nothing to the observer's answers.** Every item is answered correctly at
  both positions and A sits at 1.000 at both. B marginals average 0.146 at step 1 and 0.127 at step
  3, but since v5 the two positions are different expressions, so that gap is expression variation
  as much as position. (On v4's matched pairs the answer was identical at both positions in 116 of
  120 pairs.) The Bayes arm is a flat reference on this factor, not a contrast.

⚠️ **Use `probed_marginal` as the observer's response, never `map_profile`.** On 19 of 240 items
(8%) the MAP names TWO rules for a one-misconception item, always with `outside_bracket_first` as
the partner: on a trace that never enters its bracket early, "also holds outside()" makes the path
more likely, so the pair outscores the true singleton. Affects no item's correctness and no marginal.

---

## 5. Figures (`analysis-Bayesian/`)

- **`bayes_common.py`** shared loader and styling. Reads `base-task/bayes_per_item.json` rather than
  recomputing, so a figure can never drift from the recorded observer.
- **`plot_bayes_1misc_heatmap.py`** -> `bayes_1misc_heatmap.png` (2 panels, split by error position)
  and `bayes_1misc_heatmap_combined.png` (positions pooled). Rows = misconception PRESENT, columns =
  misconception NAMED. 0 empty cells, by design of the pool.
- **`plot_bayes_1misc_by_rule.py`** -> `bayes_1misc_by_rule.png`. **The main distribution figure.**
  One panel per misconception: P(that rule | trace) when the rule IS in the trace (a point mass at
  1.000 for all six) versus when it is ABSENT. Uses ALL 240 traces (40 present, 200 absent per rule),
  not just the items whose statement named that rule, since the statement is not an input. Shades the
  region above 0.35 where an absent rule is never used as a foil.
- **`plot_bayes_1misc_profile.py`** -> `bayes_1misc_profile.png`. The transpose: for traces containing
  rule X, the marginal on ALL SIX rules at once.

### ⚠️ Finding: the pool excludes the hardest foils
Over the 1200 (trace, absent rule) combinations of the 5-op pool, **20 (1.7%) give an ABSENT rule a
marginal above 0.35 and 8 (0.7%) above 0.5**, i.e. the trace positively favours a rule the student
does not hold. Max **0.727** (item A061: the trace contains sub_before_div, yet P(outside() | trace)
= 0.727). **All 8 over-0.5 cases are `outside_bracket_first`**, as are 19 of the 20 over 0.35. (The
6-op pool ran 42 and 27, max 0.871, so shortening the expressions roughly halved this.) Because
`foil_options()` drops foils above 0.35, no category-B item ever names one of these. Keeping the
exclusion means the disagree trials never include the genuinely tempting case; removing it means some
B items have no defensible "correct" answer, since the ideal observer would agree with the statement.

### Rules for any new figure
- Category A is a **point mass** at 1.000. Do not draw its "distribution"; there is none.
- Marginals here are discrete (11 values in B, 1 in A). Use exact-value stems, not KDEs.
- Never split by `foil_status` (§3).
- Never group by one rule while plotting the marginal selected by a different rule (e.g. group by the
  rule in the trace but plot the marginal on whichever rule the statement named). That pools
  incommensurable quantities into one panel and has already misled a reader once.

---

## 6. The web experiment (`src/`)

A Smile (codec-lab / gureckislab) Vue-3 experiment. **User code in `src/user/`.** `npm run dev` runs
it locally.

- **`src/user/design.js`** the timeline: consent -> windowsizer -> instructions -> comprehension quiz
  -> practice -> experiment -> strategy question -> feedback survey -> demographics -> save ->
  debrief -> thanks.
- **`src/user/components/trace_judgment/TraceJudgmentView.vue`** the 24-trial task: expression, work
  (`= step` per line), belief statement, the question "Is this what the student believes?" and the
  YES / NO answer (since 2026-09-16; the D / F keys only since 2026-09-18; an answer records the
  trial and moves on at once, no Submit). 3-second answer-key lock per trial, "X of 24" counter,
  mouse tracking for offline bot detection, and bonus scoring (see below). Recorded per trial:
  `response` (`'yes'`/`'no'`), `response_method` (`'key'`/`'autofill'`; `'click'` can no longer
  occur, but old test data may hold it), `rt`,
  `responded_agree`, `correct_agree`, `is_correct`, `mouse`, plus the item fields.
- **`src/user/components/trace_judgment/PracticeView.vue`** practice trials with feedback: the same
  YES / NO answer; after answering, the chosen answer stays highlighted, the erroneous step(s) are
  highlighted amber with a short note, then the feedback paragraph and "Next practice question".
- **`src/user/components/trace_judgment/YesNoButtons.vue`** (2026-09-16, copied from Experiment 2):
  a green YES (D) and a red NO (F) box (small: `w-28 py-2 text-base`) with "Answer with the
  keyboard: press D for YES or F for NO" underneath; listens for the D / F keys while mounted,
  ignores input while `disabled`, emits `answer` with `{ response, method: 'key' }`.
  **Keyboard-only since 2026-09-18 at the user's request**: the boxes are `div`s, not buttons, with
  no click handler, `pointer-events-none` and `aria-hidden`, so a mouse cannot answer. If a
  participant reports being unable to answer, check their keyboard first.
- **`src/user/utils/traceLayout.js`** (2026-09-18, the user's professor asked for it): lays the work
  out so each computed value is CENTRED under the operands it replaced, instead of every line being
  flush left, which made it hard to see which operation was done. The expression's tokens define the
  columns; untouched tokens keep their column; the new value spans the columns it replaced;
  parentheses share a cell with their contents. `layoutTrace(trace)` returns `{nCols, rows}` of
  cells with CSS grid-line numbers (column 1 is the "=" prefix), or **null** if a step is not a
  single arithmetic operation, in which case both views fall back to plain left-aligned lines.
  Verified 2026-09-18: a layout is produced for all 240 pool items and all 3 practice items. Both
  views render it as ONE grid per item, so the columns line up across lines, and the work block now
  starts with the expression itself on a row with no "=". In practice, an error step is an amber
  band across the whole row with the note to its right.
  Both 2026-09-18 changes (keyboard-only answering and this layout) are deployed and verified:
  commit 0a3ce1b, deploy run 35384161251, live bundle `assets/main-qy6RzIp1.js` has the
  keyboard-only caption, the "cannot be clicked" sentence, the layout code, and no click handler.
  Not yet applied to Experiments 2 and 3, which still share the older `YesNoButtons.vue`; the
  hidden-step design would also need care, since a hidden line breaks the step-to-step mapping and
  would fall back to flush-left lines. This file, `PracticeView.vue` and `StrategyQuestionView.vue`
  are byte-identical to Experiment 2's and to Experiment 3's (`divya603/bodmas-exp3-teaching`, seeded
  from Experiment 2 on 2026-09-16); when the user changes one, ask whether the others should follow.
- **`src/user/components/trace_judgment/StrategyQuestionView.vue`** required free-text strategy
  question after the task (asks how they decided whether to answer YES or NO).
- **`src/user/utils/sampleForm.js`** draws each participant's 24-trial form (design in §8, "Done").
  Python twin: **`base-task/sample_form.py`**. Both use the same seeded PRNG (mulberry32) and the
  same draw order, so a seed gives the identical form in both; checked identical (items, order,
  names, statements) over 500 seeds on 2026-09-13. `python3 sample_form.py` runs the 500-seed checks.
- **`src/builtins/thanks/ThanksView.vue`** upload-progress screen + Prolific completion code
  **`CNIEB9GV`** (in both the `prolific` and `web` blocks). ⚠️ That code belongs to the OLD study's
  Prolific study. A new Prolific study issues a new code; replace it in both blocks before launch.
- **`public/consent-form.pdf`** NYU IRB form (IRB-FY2026-11440, PI Mark Ho).

### Frontend status
As of 2026-09-13 `src/user/data/stimulus_pool.json` is the v5 pool (byte-identical to
`base-task/stimulus_pool.json`) and `sampleForm.js` is the new sampler. **Deployed and verified
2026-09-13:** commit 975c0dc, deploy run 34776824047 (the `deploy` job ran), and the live bundle
(`assets/main-C0VuXHPj.js` at that commit) contains the v5 expression `(9 × 2 + 4) - 1 + 8 ÷ 2 + 11`
and none of the old pool's expressions. **2026-09-17: the pool was rebuilt at 5 operators and the
three practice items regenerated to match. Deployed and verified: commit c4c995d, deploy run
35266815945, live bundle `assets/main-Bxz5v7Hi.js`, where all 240 items show 6 lines (expression
plus 5 steps) and no 6-operator expression survives.**

**Practice items (new 2026-09-13; deployed and verified: commit 0abdf0c, deploy run 34778572392,
live bundle `assets/main-CcKDMNvE.js` contains the new items and none of the old practice set).**
`src/user/data/practice_items.json` is written by `base-task/practice.py`, which holds the three
user-approved items verbatim and checks them against the model: not in the pool, one error at the
declared step that reads as the true rule only, B statements pass the foil rules and the look-alike
guard with the intended status, names outside the task's 24. Fixed order, as the user specified:

| id | statement | error | true rule | statement names | why disagree |
|---|---|---|---|---|---|
| P1 | correct | step 1 | add_before_mul | add_before_mul | |
| P2 | wrong | step 3 | sub_before_mul | add_before_mul | ruled out: at step 4 the student multiplies 2 × 2 with `9 + 2` available |
| P3 | wrong | step 1 | same_priority_rtl | sub_before_div | no chance: the problem has no subtraction |

After each answer the error step is highlighted amber with a note, plus a feedback paragraph that
explains the right answer without saying whether the participant was right (it ends "the right
answer would be YES/NO" since 2026-09-16). Answer keys are 1 YES / 2 NO (the user's choice).

**Instructions and quiz (rewritten 2026-09-13, user-approved; deployed and verified: commit 57625e0,
deploy run 34779362204, live bundle `assets/main-BQgn2sQl.js` has the new text and quiz, not the old
quiz).** `InstructionsView.vue` (since 2026-09-16 it matches Experiment 2's text at the user's request,
minus Experiment 2's "one step skipped", since nothing is skipped here) covers: the task; every
student makes exactly one mistake; "Your Job. Decide whether the statement describes what the
student believes, using their work as evidence. Answer YES when the student's mistake is the one the
statement describes and NO otherwise."; the bonus in one line ("You can earn a bonus of up to $2.");
and "You'll start with 3 practice questions. After each one, we highlight and explain the right
answer. Practice trials do not count towards your bonus. Then you'll judge 24 problems. On each one,
the answer keys unlock after 3 seconds, so take time to read the work." The "Your Job" paragraph also
says, since 2026-09-18, that you answer with the keyboard (D for YES, F for NO) and that the boxes
are not clickable. Removed on 2026-09-16: the
correct-order-of-operations paragraph, the "disagree when..." sentence, the 6-point scale and the
"What happens next" label. The user wants this text short. The user asked NOT to list the six
beliefs with examples. Its numbers mirror `MAX_BONUS`, `UNLOCK_DELAY_MS`, the form size and the
practice count; change them together. `quizQuestions.js`: 3 questions on one page, all must be
right or the participant returns to the instructions: what your answer is based on, how many
mistakes (exactly one), a different-mistake case (NO; YES / NO options since 2026-09-16). The no-chance / brackets question was removed at the
user's request 2026-09-14 (as in Experiment 2). The 2026-09-14 bonus and quiz changes are deployed and
verified: commit b66dfc9, deploy run 34865350982, live bundle `assets/main-Bv_8lgFU.js` has the
one-line bonus and no brackets question.

### Bonus
YES counts as agree; a trial is correct if that matches `statement_correct`.
`bonus = max(0, (accuracy - 0.5) / 0.5) x $2`, rounded to cents, recorded per trial (`is_correct`)
and as a `traceJudgmentBonus` block in `pageData_exp`. Participants are told only "You can earn a
bonus of up to $2." Base pay is separate.

### ⚠️ Prolific URL (a missing-params bug cost a whole batch once)
Participants MUST arrive on `#/welcome/prolific/` with the ID params, or they are recorded
`recruitmentService: "web"` with no `prolific_id` and cannot be bonused. Use params BEFORE and AFTER
the hash:
```
https://www.codec-lab.org/divya603/bodmas-exp1-position/main/?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}#/welcome/prolific/?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}
```
Test it end to end (confirm a `prolific_id` is recorded) before launching any batch.

### Checklist before running any participant
- [x] New form sampler + new pool + new practice items deployed (all verified 2026-09-13), and the LIVE
      bundle verified to contain the new pool (grep the deployed JS for a known new expression).
- [ ] Prolific completion code in `ThanksView.vue` replaced with the new Prolific study's code.
- [ ] Consent and debrief: `design.js` already points `consentPdfUrl` at `public/consent-form.pdf` and
      `debriefPdfUrl` at `public/debrief.pdf`, and both files exist. Confirm with the PI that the IRB
      protocol (IRB-FY2026-11440) covers Experiment 1 and that the consent PDF is the current version.
- [x] Instructions and comprehension quiz rewritten for this design and deployed (verified in the
      live bundle 2026-09-13).
- [ ] Prolific URL tested end to end with a fake PID: a `prolific_id` must appear in the recruitment
      data (`npm run getrecruitment`, type `testing`).
- [ ] Fresh bonus ledger for this experiment (see below).

### Running participants and paying them
- Pull data: `npm run getdata` prompts for data type (`testing` = your own test runs, `real` =
  participants), complete-only or all, branch (use `main`), and filename; it saves JSON under
  `data/`, typically `data/real-all-main-data.json` (participant records; each has
  `.data` with `seedID`, `recruitmentService`, `pageData_exp.visit_0.data` = 24 trials + bonus
  block). `npm run getrecruitment` -> `data/private/real-main-recruitment.json` (maps `session_id`
  -> `prolific_id`). **Join key: data `seedID` == recruitment `session_id`.** The interactive
  prompts can be skipped with `node scripts/get_recruitment_data.mjs --type real --branch_name main
  --filename data/private/real-main-recruitment.json`.
- Bonus list: the old study's `scripts/make_bonus_list.py` was never committed; it is at
  `~/Desktop/NYU/Darpa/Bodmas_model/scripts/make_bonus_list.py`. Copy it here when needed. It
  recomputes each bonus from raw responses against `statement_correct` (never trusting the
  client-stored value) and emits `prolific_id,amount` lines for Prolific's bulk-bonus box.
- **Keep a payment ledger** (`data/private/bonus_paid.csv`, gitignored) and start a FRESH one for
  this experiment. Workflow: run the script -> pay on Prolific -> re-run with `--mark-paid`. Batches
  that share one Prolific study id are indistinguishable otherwise, so the ledger is the only guard
  against double-paying.

### Deploys
`.github/workflows/deploy.yml` deploys on push to ANY branch except `feat-* fix-* refactor-* test-*
chore-* style-* docs-* ci-*`, each to its own path `/<owner>/<repo>/<branch>/` with its own codename.
So **pushing `main` deploys the live experiment**; pushing any other branch gives it a separate
staging site. Monitor with `gh run list` / `gh run watch`. A `deploy-error` workflow showing
"skipped" on success is normal. A transient "SSH i/o timeout" at the "create the remote folders"
step has happened before; `gh run rerun <id> --failed` fixed it. Commits that touch only `*.md`
files or `docs/` do NOT deploy (`paths-ignore` in `deploy.yml`), so a HANDOFF-only push leaves the
live site as it was and shows no run in `gh run list`.

---

## 7. Commands cheat-sheet

```bash
# Pool and observer
cd base-task && python3 pool.py            # build -> stimulus_pool.json (240 items, seed 2026)
cd base-task && python3 verify.py          # independent checks; RUN AFTER ANY REBUILD
cd base-task && python3 bayes.py           # ideal observer -> bayes_per_item.json (expect 240/240)
cd base-task && python3 find_pairs.py 12   # per-misconception matched-pair yields (v4 stat only)
cd base-task && python3 sample_form.py     # sampler checks over 500 seeds (twin of sampleForm.js)
cd base-task && python3 practice.py        # check + write the 3 practice items to src/user/data/

# Figures (from repo root)
python3 analysis-Bayesian/plot_bayes_1misc_heatmap.py
python3 analysis-Bayesian/plot_bayes_1misc_by_rule.py
python3 analysis-Bayesian/plot_bayes_1misc_profile.py

# Experiment
npm run dev                                # local
npm run build                              # production build, check it compiles
git push origin main                       # DEPLOYS THE LIVE EXPERIMENT (ask first)
npm run getdata ; npm run getrecruitment   # pull participant + recruitment data
npm run upload_config                      # (re)push deploy secrets from env/*.local
```

---

## 8. What is next

1. **Before launch:** replace the Prolific completion code (§6) and work through the §6 checklist
   (IRB coverage, end-to-end Prolific URL test, fresh bonus ledger). Deploy secrets are set up (§1).
2. **Check the advertised time with the PI.** `design.js` sets `estimated_time` to 30-40 minutes
   and pay is prorated to it; 3 practice + 24 trials will likely take less (not yet measured).
3. The hardest-foil exclusion (§3 item 4, §5) is kept as is; the user did not ask to change it
   (2026-09-13). Revisit only if they do.

Done 2026-09-16 (user's request, mirroring Experiment 2):
- **YES / NO answers** with the D / F keys replace the 6-point scale in practice and task; the
  instructions, quiz, strategy question and practice feedback were reworded to match (§6).
  Deployed and verified: commit `433cf89`, deploy run 35113581343 (`deploy` job ran), live bundle
  `assets/main-BdmX0si-.js` has the YES / NO question, the new practice paragraph, the YES / NO quiz
  question and practice feedback, and no "Strongly Disagree", no order-of-operations paragraph, no
  "one step skipped", no hidden-line code. The answer buttons, keys and 3-second lock have not been
  clicked through in a browser by Claude; the user is checking the live site.

Done 2026-09-13:
- **Instructions and quiz** rewritten for this design (details in §6 "Frontend status"). They make
  clear that a statement is rated on whether it explains the work: 62 of 120 B items name a rule the
  expression gives the student no chance to show, and "disagree" is right there only on that framing.
- **Practice items**: 3 fixed items, user-approved, built and checked by `base-task/practice.py`
  (details in §6 "Frontend status"). The old 2-misconception marker code was removed from
  `PracticeView.vue`.
- **Form sampler**, design decided by the user: four pools by category x position (A/1, A/3, B/1,
  B/3); from each pool, one item drawn at random per misconception present, so 24 trials: 12 agree
  / 12 disagree, 12 per position, every misconception present exactly 4 times (once per pool), and
  every statement named exactly twice as the correct one. Which foil a B trial names is left to the
  draw: the user explicitly did NOT want each statement shown a fixed number of times, and fixed
  counterbalanced forms were considered and rejected. Trial order fully shuffled; the 24 names
  shuffled so each appears exactly once. Over 500 seeds: the most times one statement is named as a
  WRONG statement in a form is usually 3 or 4 and at most 7, so a statement's total count per form
  ranges from 2 to 9. Every item is drawn about equally often (31 to 75 times per 500 forms, expect
  50).
- **Pool propagated** to `src/user/data/stimulus_pool.json` together with the sampler; deployed in
  975c0dc and verified in the live bundle (§6).

---

## 9. Gotchas and working rules

- **An experiment change is only done when it is committed, pushed, verified in the deployed bundle,
  and recorded here.** Local files do nothing for participants: the live site is built by CI from the
  git remote. A previous study lost a batch of 19 paid participants to a pool that was regenerated
  locally but never pushed.
- **Pushing `main` deploys the live experiment.** Ask the user before pushing experiment-material
  changes to `main`.
- **A green deploy run does not mean it deployed.** With secrets missing, the `deploy` job is skipped
  and the workflow still passes. Check the `deploy` job's steps (`gh run view <id>`), then check the
  live bundle.
- **`sampleForm.js` and its Python twin must stay in sync.** The live experiment uses the JS one.
- **Never commit** `data/real-all-main-data.json` (participant demographics), anything under
  `data/private/`, `env/*.local`, or any API key.
- **User preferences:** finish a design discussion before writing code. On a surprising result,
  audit our own stimuli and task before blaming participants. The user often runs commands themselves
  via `! <cmd>` and likes work pushed rather than left local. **No em dashes in any writing** (docs,
  reports, chat). **LaTeX compiles on Overleaf only**: keep tex folders self-contained, figures
  referenced as `figs/<exact-name>`, never install a local TeX toolchain.
- If a commit prints `Cannot find module '@codenamize/codenamize'`, `node_modules` is missing; run
  `npm run setup_project`. The commit itself still lands.
- Commit messages end with the current model's co-author line.
