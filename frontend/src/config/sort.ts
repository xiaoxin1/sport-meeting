/** 全站共享的排序工具。 */
import { GRADE_GROUPS } from "./constants";

const GRADE_INDEX = new Map<string, number>(GRADE_GROUPS.map((g, i) => [g, i]));

/**
 * 年级排序：按规范顺序（一年级…高三）。
 * 未知年级排到最后，再按自然序兜底。
 */
export function compareGrade(a: string, b: string): number {
  const ia = GRADE_INDEX.has(a) ? GRADE_INDEX.get(a)! : Number.MAX_SAFE_INTEGER;
  const ib = GRADE_INDEX.has(b) ? GRADE_INDEX.get(b)! : Number.MAX_SAFE_INTEGER;
  if (ia !== ib) return ia - ib;
  return naturalCompare(a, b);
}

/**
 * 自然排序：数字部分按数值比较（10 排在 9 之后），
 * 其余按中文/字符序比较。适用于「1班…10班」「60米…100米」这类含数字的名称。
 */
export function naturalCompare(a: string, b: string): number {
  const ax = tokenize(a);
  const bx = tokenize(b);
  const n = Math.min(ax.length, bx.length);
  for (let i = 0; i < n; i++) {
    const t1 = ax[i];
    const t2 = bx[i];
    if (typeof t1 === "number" && typeof t2 === "number") {
      if (t1 !== t2) return t1 - t2;
    } else {
      const s1 = String(t1);
      const s2 = String(t2);
      const c = s1.localeCompare(s2, "zh");
      if (c !== 0) return c;
    }
  }
  return ax.length - bx.length;
}

/** 将字符串拆成 数字段 / 非数字段 交替的 token 序列。 */
function tokenize(s: string): (string | number)[] {
  const tokens: (string | number)[] = [];
  const re = /(\d+)|(\D+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s)) !== null) {
    tokens.push(m[1] !== undefined ? Number(m[1]) : m[2]);
  }
  return tokens;
}
