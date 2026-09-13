// Draws one participant's 24-trial form from the Experiment 1 pool.
// Python twin: base-task/sample_form.py. Both use the same PRNG (mulberry32)
// and the same sequence of draws, so one seed gives the identical form in both
// languages. Change one, change the other, then rerun its checks.
//
// Design (decided 2026-09-13): four pools by category x error position (A/1,
// A/3, B/1, B/3). From each pool, one item is drawn at random for each of the 6
// misconceptions (the rule present in the trace), so 24 trials: 12 agree / 12
// disagree, 12 at each position, and every misconception present exactly 4
// times, once per pool. Which foil a B trial names is left to the draw. Trial
// order is shuffled, and the 24 names are shuffled so each appears exactly
// once. Every pool expression is unique, so no form repeats one.

const IDS = [
  'add_before_mul',
  'add_before_div',
  'sub_before_mul',
  'sub_before_div',
  'same_priority_rtl',
  'outside_bracket_first',
]

const POOLS = [
  ['A', 1],
  ['A', 3],
  ['B', 1],
  ['B', 3],
]

// One name per trial (24), so no participant ever sees the same student twice.
// Names baked into the pool JSON are placeholders, replaced here at sampling
// time. Keep in sync with STUDENT_NAMES in base-task/pool.py.
const STUDENT_NAMES = [
  'Noah', 'Maya', 'Liam', 'Ava', 'Ethan', 'Zoe',
  'Mia', 'Lucas', 'Emma', 'Owen', 'Sofia', 'Caleb',
  'Ruby', 'Jonah', 'Isla', 'Felix', 'Nora', 'Dylan',
  'Priya', 'Marcus', 'Elena', 'Theo', 'Jasmine', 'Omar',
]

// Small seeded PRNG (mulberry32) so a given seed always reproduces the same form.
function makeRng(seed) {
  let s = seed >>> 0
  function next() {
    s = (s + 0x6d2b79f5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  return {
    choice(arr) {
      return arr[Math.floor(next() * arr.length)]
    },
    shuffle(arr) {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(next() * (i + 1))
        ;[arr[i], arr[j]] = [arr[j], arr[i]]
      }
      return arr
    },
  }
}

export function sampleForm(pool, seed) {
  const rng = makeRng(seed)
  const form = []
  for (const [category, position] of POOLS) {
    for (const mid of IDS) {
      const members = pool.filter(
        (it) => it.category === category && it.error_position === position && it.misconceptions[0] === mid
      )
      form.push(rng.choice(members))
    }
  }
  rng.shuffle(form)

  // Assign each trial a distinct student name (copies, so the shared pool
  // objects are never mutated), rewriting the belief statement to match. Every
  // pool statement begins with its placeholder name.
  const names = rng.shuffle(STUDENT_NAMES.slice())
  return form.map((it, i) => ({
    ...it,
    student_name: names[i],
    belief_statement: names[i] + it.belief_statement.slice(it.student_name.length),
  }))
}

export function randomSeed() {
  return Math.floor(Math.random() * 2 ** 31)
}
