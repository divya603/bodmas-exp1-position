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
particular misconception. They rate on a **6-point Likert scale** (1 = Strongly Disagree, 6 =
Strongly Agree) how well the statement explains the work, NOT whether the final answer is right.
Scoring collapses the rating at **>= 4 = agree**.

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

**Status as of 2026-09-13: secrets NOT yet uploaded, so nothing has been deployed.** `deploy.yml`
handles missing secrets gracefully: its `check-secrets` job SKIPS the `deploy` job and the run still
shows GREEN, with a "secrets are not configured, skipping deploy" notice. The initial pushes did
exactly that. After `force_deploy`, confirm with `gh run list` then `gh run view <id>` that the
**`deploy` job itself ran** (build and rsync, a few minutes), and look for the lab Slack message.
Update this status line once done.

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

### The pool: `pool.py` -> `stimulus_pool.json`
**240 items in 120 matched pairs.** Seed 2026, reproducible byte-for-byte.

Design factors:
- **Misconception present** (6 levels). Each is the true misconception in exactly 40 items.
- **Error position** (step 1 or step 3), manipulated WITHIN expression via matched pairs: both
  members of a `pair_id` share an identical expression and differ only in where the error falls.
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

Other guarantees: 120 distinct expressions, each used by exactly one pair. Every trace is 6 steps
with exactly one expert-illegal move. Every learner answer differs from the correct answer. Numbers
shown span 1 to 960: no negatives, decimals or zeros. No foil is ever probed on a trace generated by
that same rule.

Worked example, one matched category-A pair (`pair_id` P000, statement "believes addition should be
done before multiplication"):
```
error at step 1 (A000)                  error at step 3 (A001)
4 + 9 × 4 ÷ 2 × (3 + 10) × 2            4 + 9 × 4 ÷ 2 × (3 + 10) × 2
= 13 × 4 ÷ 2 × (3 + 10) × 2   <- 4+9    = 4 + 9 × 2 × (3 + 10) × 2
= 52 ÷ 2 × (3 + 10) × 2                 = 4 + 9 × 2 × 13 × 2
...                                     = 13 × 2 × 13 × 2           <- 4+9
```

Item fields: `id, pair_id, category, error_position, expression, n_ops, misconceptions,
num_misconceptions, trace, probed_misconception, statement_correct, which_target (always null, kept
for schema compatibility), student_name, belief_statement`, plus on B items only `foil_status` and
`io_foil_marginal`.

**Answer-leak fields** (never show a solver or a participant): `statement_correct, misconceptions,
probed_misconception, category, num_misconceptions, foil_status, io_foil_marginal`.

### ⚠️ Things about this pool that will bite you
1. **6 operators is FORCED, not preferred.** Over 2500 bracketed expressions, the number supporting
   BOTH step 1 and step 3 for `outside_bracket_first` is **0 at 4 ops, 0 at 5 ops, 32 at 6 ops**. At
   4 ops that rule never reaches step 3 at all; at 5 ops no single expression does both, so matched
   pairs are impossible. Shortening the expressions silently kills the outside() step-3 cell.
2. **Position is SELECTED, not constructed.** Nothing places the error. A misconception is a
   substitution at one window: it decides what happens when the learner touches that window, not
   when. One expression plus one misconception yields many valid traces (75 for the example above),
   with the single error landing anywhere from step 1 to step 5. The builder filters for step 1 and
   step 3 and pairs them. Left unconstrained, position is confounded with rule (sub<÷ errors land
   early, add<÷ errors land late), which is why it is fixed by design.
3. **`foil_status` is RECORDED but NOT BALANCED.** Refutation (refuted vs unsupported foil) is not a
   factor in this experiment. Pool-wide it is 58 refuted / 62 unsupported, but per foil it is
   lopsided: `same_priority_rtl` 16/4 and **`outside_bracket_first` 2 refuted / 18 unsupported**.
   **Never split a figure or analysis by `foil_status`**; the cells go lopsided and empty.
4. **The pool excludes the hardest foils.** `pool.py: foil_options()` drops any foil whose marginal
   exceeds 0.35 as "not a clean foil", so no B item ever names a rule the trace actually supports.
   See the finding in §5. Decide before running participants whether that exclusion is wanted.
5. **Only about 2.6 of the 6 steps carry evidence.** Counting how many of the 22 hypotheses each step
   eliminates, summed over all 240 traces: step 1 2482, step 2 335, step 3 1333, step 4 85, step 5
   81, step 6 0. Steps 1 and 3 (the error positions) carry 88%; the last step carries none because it
   is forced. Participants read six lines of which roughly two and a half matter.

### Verification: `verify.py`
Independent verifier, run after ANY regeneration (`cd base-task && python3 verify.py`, exits
non-zero on failure). It re-derives everything from the model rather than trusting the builder:
regenerates each trace from its expression, re-tests every step for expert legality, re-runs the
22-hypothesis observer, and re-checks statement wiring, pair matching, expression uniqueness, and
the exact cell counts that guarantee a full heatmap (asserting 0 empty cells). Currently ALL CHECKS
PASSED. It deliberately does NOT check refutation balance, only that each stored status matches a
fresh recomputation and is stable across a pair.

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
- B items: P(agree) 0.000; marginal min 0.000 / mean 0.130 / max 0.333, over only 8 distinct values.
- **Error position does nothing to the observer.** Its answer is identical at both positions in 116
  of 120 matched pairs (all 60 A pairs, 56 of 60 B pairs); the 4 that differ do not agree on a
  direction. Position reorders the work but not which operations are performed. So any position
  effect in people cannot be a response to evidence, which is what makes it a clean processing
  measure, but it also means the Bayes arm is a flat reference on this factor, not a contrast.

⚠️ **Use `probed_marginal` as the observer's response, never `map_profile`.** On 24 of 240 items
(10%) the MAP names TWO rules for a one-misconception item, always with `outside_bracket_first` as
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
Over the 1200 (trace, absent rule) combinations, **36 (3.0%) give an ABSENT rule a marginal above
0.35 and 15 (1.2%) above 0.5**, i.e. the trace positively favours a rule the student does not hold.
Max **0.871** (item B224: the trace contains add_before_div, yet P(outside() | trace) = 0.871). **All
15 over-0.5 cases are `outside_bracket_first`**, as are 30 of the 36 over 0.35. Because
`foil_options()` drops foils above 0.35, no category-B item ever names one of these. Keeping the
exclusion means the disagree trials never include the genuinely tempting case; removing it means some
B items have no defensible "correct" answer, since the ideal observer would agree with the statement.

### Rules for any new figure
- Category A is a **point mass** at 1.000. Do not draw its "distribution"; there is none.
- Marginals here are discrete (8 values in B, 1 in A). Use exact-value stems, not KDEs.
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
  (`= step` per line), belief statement, 6-point Likert. 3-second answer lock per trial, "X of 24"
  counter, mouse tracking for offline bot detection, and bonus scoring (see below).
- **`src/user/components/trace_judgment/PracticeView.vue`** practice trials with feedback: after the
  participant answers, the erroneous step(s) are highlighted amber with a short note.
- **`src/user/components/trace_judgment/StrategyQuestionView.vue`** required free-text strategy
  question after the task.
- **`src/user/utils/sampleForm.js`** draws each participant's 24-trial form.
- **`src/builtins/thanks/ThanksView.vue`** upload-progress screen + Prolific completion code
  **`CNIEB9GV`** (in both the `prolific` and `web` blocks). ⚠️ That code belongs to the OLD study's
  Prolific study. A new Prolific study issues a new code; replace it in both blocks before launch.
- **`public/consent-form.pdf`** NYU IRB form (IRB-FY2026-11440, PI Mark Ho).

### ⚠️ The frontend does NOT yet use this experiment's pool
`src/user/data/stimulus_pool.json` is still the OLD study's 480-item pool, `src/user/data/
practice_items.json` is still its 5-item practice set (with 2-misconception trials), and
`sampleForm.js` still implements the old study's sampling. They were carried over only so the app
builds and deploys. **The site as deployed serves the wrong experiment.** Fixing this is §8 item 1.

### Bonus
Binary direction only: rating >= 4 counts as agree, correct if that matches `statement_correct`.
`bonus = max(0, (accuracy - 0.5) / 0.5) x $2`, rounded to cents, recorded per trial (`is_correct`)
and as a `traceJudgmentBonus` block in `pageData_exp`. Confidence is deliberately NOT rewarded,
because the Likert distribution is the dependent variable and paying for extremes would distort it.
Base pay is separate.

### ⚠️ Prolific URL (a missing-params bug cost a whole batch once)
Participants MUST arrive on `#/welcome/prolific/` with the ID params, or they are recorded
`recruitmentService: "web"` with no `prolific_id` and cannot be bonused. Use params BEFORE and AFTER
the hash:
```
https://www.codec-lab.org/divya603/bodmas-exp1-position/main/?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}#/welcome/prolific/?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}
```
Test it end to end (confirm a `prolific_id` is recorded) before launching any batch.

### Checklist before running any participant
- [ ] New form sampler + new pool + new practice items deployed (§8 items 1 to 3), and the LIVE
      bundle verified to contain the new pool (grep the deployed JS for a known new expression).
- [ ] Prolific completion code in `ThanksView.vue` replaced with the new Prolific study's code.
- [ ] Consent and debrief: `design.js` already points `consentPdfUrl` at `public/consent-form.pdf` and
      `debriefPdfUrl` at `public/debrief.pdf`, and both files exist. Confirm with the PI that the IRB
      protocol (IRB-FY2026-11440) covers Experiment 1 and that the consent PDF is the current version.
- [ ] Instructions and comprehension quiz reviewed for this design (§8 item 4).
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
step has happened before; `gh run rerun <id> --failed` fixed it.

---

## 7. Commands cheat-sheet

```bash
# Pool and observer
cd base-task && python3 pool.py            # build -> stimulus_pool.json (240 items, seed 2026)
cd base-task && python3 verify.py          # independent checks; RUN AFTER ANY REBUILD
cd base-task && python3 bayes.py           # ideal observer -> bayes_per_item.json (expect 240/240)
cd base-task && python3 find_pairs.py 12   # per-misconception matched-pair yields

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

1. **The form sampler** (blocks everything else). `src/user/utils/sampleForm.js`, plus a Python
   twin for checking, must draw each participant's 24 trials from `base-task/stimulus_pool.json`.
   Constraints: at most ONE item per `pair_id` (the two members share an expression, so seeing both
   would repeat it), distinct student names, and balance across rule x position x category. Note
   24 = 6 rules x 2 positions x 2 categories, so one trial per cell per participant is the natural
   design; which foil each B trial names then has to rotate across participants. Verify balance over
   500 seeds in both languages. The design choices here are the user's; discuss before coding.
2. **Propagate the pool.** Copy `base-task/stimulus_pool.json` to `src/user/data/stimulus_pool.json`
   ONLY together with the new sampler. Doing it earlier breaks form assembly.
3. **Practice items.** Needed for this design (1 misconception, A and B trials). The old practice
   generator is gone. Keep the answer keys balanced: the old set was 4 agree / 1 disagree and
   visibly shifted participants toward agreeing. Practice expressions must not appear in the pool.
4. **Check the instructions and comprehension quiz** (`InstructionsView.vue`, `quizQuestions.js`)
   still match this design; they were written for the old study.
5. **Set up deploy secrets** (§1) and verify the built bundle actually contains the new pool before
   any participant runs. Replace the Prolific completion code (§6). Work through the §6 checklist.
6. Decide on the hardest-foil exclusion (§3 item 4, §5) before running participants.

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
