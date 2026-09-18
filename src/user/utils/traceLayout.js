// Lays out a student's work so that each computed value sits CENTRED under the
// operands it replaced, instead of every line being flush left (user's request,
// 2026-09-18: left-aligned lines make it hard to see which operation was done).
//
//     2 + 3 × 4
//   =   5   × 4        <- 5 sits under "2 + 3"; "× 4" does not move
//
// How: the first line's tokens define the columns. On every later line the
// tokens that did not change keep their columns, and the new value spans the
// columns of the tokens it replaced. The views render this as one CSS grid, so
// the columns line up across all lines.
//
// Column numbers are CSS grid lines and assume the grid's first column holds the
// "=" prefix, so token columns start at 2.

const TOKEN = /\d+|[-+×÷()]/g
const OPS = ['+', '-', '×', '÷']

export function tokenize(line) {
  return line.match(TOKEN) ?? []
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

// Which tokens of `prev` collapsed into the one new token of `next`: inclusive
// indices into `prev`, or null if the step is not one arithmetic operation.
// A bracket that is reduced to a single number loses its parentheses in the same
// step, so the range then covers them too.
export function collapsedRange(prev, next) {
  for (let i = 1; i < prev.length - 1; i++) {
    if (!OPS.includes(prev[i])) continue
    if (!/^\d+$/.test(prev[i - 1]) || !/^\d+$/.test(prev[i + 1])) continue
    const v = apply(prev[i - 1], prev[i], prev[i + 1])
    if (v === null) continue
    const cand = [...prev.slice(0, i - 1), String(v), ...prev.slice(i + 2)]
    if (same(cand, next)) return { start: i - 1, end: i + 1 }
    const j = i - 1
    if (cand[j - 1] === '(' && cand[j + 1] === ')') {
      const dropped = [...cand.slice(0, j - 1), cand[j], ...cand.slice(j + 2)]
      if (same(dropped, next)) return { start: i - 2, end: i + 2 }
    }
  }
  return null
}

// Parentheses share a cell with what they enclose, so a bracket reads as
// "(8 ÷ 4)" rather than being spaced out as "( 8 ÷ 4 )".
function tightenParens(row) {
  const out = []
  for (const cell of row) {
    const last = out[out.length - 1]
    if (cell.text === ')' && last) {
      out[out.length - 1] = { text: last.text + ')', colStart: last.colStart, colEnd: cell.colEnd }
    } else if (last && last.text.endsWith('(')) {
      out[out.length - 1] = { text: last.text + cell.text, colStart: last.colStart, colEnd: cell.colEnd }
    } else {
      out.push({ ...cell })
    }
  }
  return out
}

/**
 * @param {string[]} trace lines, starting with the expression itself
 * @returns {{nCols: number, rows: {text: string, colStart: number, colEnd: number}[][]} | null}
 *          null if any step cannot be read as a single operation, in which case
 *          the caller should fall back to plain left-aligned lines.
 */
export function layoutTrace(trace) {
  if (!Array.isArray(trace) || trace.length === 0) return null
  const first = tokenize(trace[0])
  if (first.length === 0) return null

  let spans = first.map((_, i) => [i + 2, i + 3])
  const rows = [tightenParens(first.map((text, i) => ({ text, colStart: spans[i][0], colEnd: spans[i][1] })))]
  let prev = first

  for (let k = 1; k < trace.length; k++) {
    const next = tokenize(trace[k])
    const range = collapsedRange(prev, next)
    if (!range) return null
    if (next.length !== prev.length - (range.end - range.start)) return null
    const merged = [spans[range.start][0], spans[range.end][1]]
    const shift = range.end - range.start
    const nextSpans = next.map((_, i) =>
      i < range.start ? spans[i] : i === range.start ? merged : spans[i + shift]
    )
    rows.push(tightenParens(next.map((text, i) => ({ text, colStart: nextSpans[i][0], colEnd: nextSpans[i][1] }))))
    prev = next
    spans = nextSpans
  }

  return { nCols: first.length, rows }
}
