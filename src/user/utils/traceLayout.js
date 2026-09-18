// Lays out a student's work so that each computed value sits under the OPERATOR
// that produced it, while every line stays compact (user, 2026-09-18: flush-left
// lines made it hard to see which operation was done, but a strict column grid
// left odd blanks inside the lines).
//
// Only the line as a whole moves. Nothing is padded inside a line:
//
//     2 + 3 × 4
//   =   5 × 4        <- the 5 sits under the "+"; "× 4" just follows it
//
// Each line gets an `indent` in `ch` units (the width of one character in the
// monospace font the views use), so the views only need a margin.

const TOKEN = /\d+|[-+×÷()]/g
const OPS = ['+', '-', '×', '÷']

// [{ text, start }] for one line, `start` being the character offset.
export function tokensWithPos(line) {
  const out = []
  let m
  TOKEN.lastIndex = 0
  while ((m = TOKEN.exec(line)) !== null) out.push({ text: m[0], start: m.index })
  return out
}

function apply(a, op, b) {
  const x = Number(a)
  const y = Number(b)
  if (op === '+') return x + y
  if (op === '-') return x - y
  if (op === '×') return x * y
  if (op === '÷') return y !== 0 && x % y === 0 ? x / y : null
  return null
}

function same(a, b) {
  return a.length === b.length && a.every((t, i) => t === b[i])
}

/**
 * Which tokens of `prev` collapsed into one token of `next`.
 * @returns {{ newIndex: number, opIndex: number } | null}
 *          newIndex: index of the computed value in `next`
 *          opIndex:  index in `prev` of the operator that was applied
 * A bracket reduced to a single number loses its parentheses in the same step,
 * so the collapsed run then starts two tokens earlier.
 */
export function collapsedStep(prev, next) {
  for (let i = 1; i < prev.length - 1; i++) {
    if (!OPS.includes(prev[i])) continue
    if (!/^\d+$/.test(prev[i - 1]) || !/^\d+$/.test(prev[i + 1])) continue
    const v = apply(prev[i - 1], prev[i], prev[i + 1])
    if (v === null) continue
    const cand = [...prev.slice(0, i - 1), String(v), ...prev.slice(i + 2)]
    if (same(cand, next)) return { newIndex: i - 1, opIndex: i }
    const j = i - 1
    if (cand[j - 1] === '(' && cand[j + 1] === ')') {
      const dropped = [...cand.slice(0, j - 1), cand[j], ...cand.slice(j + 2)]
      if (same(dropped, next)) return { newIndex: i - 2, opIndex: i }
    }
  }
  return null
}

/**
 * @param {string[]} trace lines, starting with the expression itself
 * @returns {{ lines: {text: string, indent: number}[] } | null}
 *          null if any step is not a single arithmetic operation, in which case
 *          the caller should fall back to plain flush-left lines.
 */
export function layoutTrace(trace) {
  if (!Array.isArray(trace) || trace.length === 0) return null

  const indents = [0]
  let prevLine = trace[0]
  let prevTokens = tokensWithPos(prevLine)

  for (let k = 1; k < trace.length; k++) {
    const nextLine = trace[k]
    const nextTokens = tokensWithPos(nextLine)
    const step = collapsedStep(
      prevTokens.map((t) => t.text),
      nextTokens.map((t) => t.text)
    )
    if (!step) return null
    const op = prevTokens[step.opIndex]
    const value = nextTokens[step.newIndex]
    if (!op || !value) return null
    const opCentre = op.start + op.text.length / 2
    const valueCentre = value.start + value.text.length / 2
    indents.push(indents[k - 1] + opCentre - valueCentre)
    prevLine = nextLine
    prevTokens = nextTokens
  }

  // shift the whole block so nothing hangs off the left edge
  const lift = Math.min(...indents)
  return { lines: trace.map((text, i) => ({ text, indent: indents[i] - lift })) }
}
