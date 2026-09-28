"""文字と式・方程式と不等式の計算問題ジェネレータ。

GENERATORS = {topic_id: fn(rng) -> list[dict]}。各 fn は 15 問を返す。
答えから逆算して問題を作り、正解・誤答はすべてコードで計算する。
4択の誤答は「値が正解と異なること」をキー（多項式の係数・数値の組など）で確認してから採用する。
"""
import math
from fractions import Fraction as F

M = "−"  # 表示用マイナス
SUPD = "⁰¹²³⁴⁵⁶⁷⁸⁹"
N = 15


class Retry(Exception):
    """この乱数では良い問題にならないので作り直す。"""


# ---------------------------------------------------------------- 表示


def sup(k):
    return "" if k == 1 else "".join(SUPD[int(d)] for d in str(k))


def num(v):
    v = F(v)
    return (M if v < 0 else "") + str(abs(v))


def pn(v):
    """負の数はかっこで囲む（代入の途中式用）。"""
    return f"({num(v)})" if F(v) < 0 else num(v)


def xp(var, k):
    return "" if k == 0 else var + sup(k)


def fsum(terms):
    """[(係数, 文字部分)] を順に並べる（同類項はまとめない）。係数1は省略。"""
    out = ""
    for c, v in terms:
        c = F(c)
        if c == 0:
            continue
        a = abs(c)
        if v:
            assert a.denominator == 1, "文字の係数が分数"
            body = ("" if a == 1 else str(a)) + v
        else:
            body = str(a)
        if not out:
            out = (M if c < 0 else "") + body
        else:
            out += (M if c < 0 else "+") + body
    return out or "0"


# ---------------------------------------------------------------- 多項式（係数は低次から）


def trim(c):
    c = [F(x) for x in c]
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    return tuple(c)


def P(*hi):
    """P(1, 5, 6) = x²+5x+6（高次から指定）。"""
    return trim(list(reversed(hi)))


def L(a, b):
    return P(a, b)


ONE = P(1)
X = P(1, 0)


def padd(a, b):
    n = max(len(a), len(b))
    return trim([(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)])


def pscale(a, k):
    return trim([x * k for x in a])


def psub(a, b):
    return padd(a, pscale(b, -1))


def pmul(a, b):
    r = [F(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    return trim(r)


def pprod(*ps):
    r = ONE
    for p in ps:
        r = pmul(r, p)
    return r


def ppow(a, n):
    return pprod(*([a] * n))


def pdivmod(a, b):
    a = list(a)
    q = [F(0)] * max(1, len(a) - len(b) + 1)
    while len(a) >= len(b) and any(a):
        k = len(a) - len(b)
        c = a[-1] / b[-1]
        q[k] = c
        for i, y in enumerate(b):
            a[i + k] -= c * y
        a.pop()
    return trim(q), trim(a or [0])


def peval(p, x):
    return sum(c * x ** i for i, c in enumerate(p))


def deg(p):
    return len(p) - 1


def fpoly(p, var="x"):
    return fsum([(p[k], xp(var, k)) for k in range(len(p) - 1, -1, -1)])


def is_mono(p):
    return all(c == 0 for c in p[:-1]) and p[-1] == 1


def ffac(factors, coef=1, mono=0):
    """coef·x^mono·(因数)(因数)… を表示。同じ因数は累乗にまとめる。"""
    s = M if coef == -1 else ("" if coef == 1 else num(coef))
    s += xp("x", mono)
    groups = []
    for f in factors:
        for g in groups:
            if g[0] == f:
                g[1] += 1
                break
        else:
            groups.append([f, 1])
    for f, c in groups:
        s += "(" + fpoly(f) + ")" + sup(c)
    return s


def fac_val(factors, coef=1, mono=0):
    return pmul(pscale(pprod(*factors), coef), trim([0] * mono + [1]))


def lin_order(cs):
    """(x+c) を正の定数→負の定数、それぞれ絶対値の小さい順に並べる。"""
    return sorted(cs, key=lambda c: (c < 0, abs(c)))


def perturb(p):
    out = []
    for k in range(len(p)):
        if p[k] != 0:
            q = list(p)
            q[k] = -q[k]
            out.append(trim(q))
    for d in (1, -1, 2, -2):
        for k in range(len(p)):
            q = list(p)
            q[k] += d
            if k == len(p) - 1 and q[k] == 0:
                continue
            out.append(trim(q))
    return out


# ---------------------------------------------------------------- 問題 dict


def numq(prompt, value, explain):
    v = F(value)
    q = {"format": "数字入力", "prompt": prompt, "answer": str(v), "explain": explain}
    if v.denominator != 1:
        d = v.denominator
        for p in (2, 5):
            while d % p == 0:
                d //= p
        if d == 1:
            k = 0
            while (v * 10 ** k).denominator != 1:
                k += 1
            n = abs(int(v * 10 ** k))
            q["accept"] = [("-" if v < 0 else "") + f"{n // 10 ** k}.{n % 10 ** k:0{k}d}"]
    return q


def mcq(rng, prompt, correct, cands, explain):
    """correct=(表示, キー)。cands は典型ミスを優先順に。キーが正解と同じものは捨てる。"""
    opts, keys = [correct[0]], [correct[1]]
    for t, k in cands:
        if t in opts or any(k == kk for kk in keys):
            continue
        opts.append(t)
        keys.append(k)
        if len(opts) == 4:
            break
    if len(opts) < 4:
        raise Retry
    idx = list(range(4))
    rng.shuffle(idx)
    return {"format": "4択", "prompt": prompt, "options": [opts[i] for i in idx],
            "answer": idx.index(0), "explain": explain}


def poly_mc(rng, prompt, ans, wrongs, explain):
    cands = [(fpoly(w), w) for w in wrongs] + [(fpoly(w), w) for w in perturb(ans)]
    return mcq(rng, prompt, (fpoly(ans), ans), cands, explain)


def collect(rng, makers, n=N):
    out, seen, tries = [], set(), 0
    while len(out) < n:
        tries += 1
        if tries > 20000:
            raise RuntimeError("問題を作れない")
        mk = makers[len(out) % len(makers)]
        try:
            q = mk(rng)
        except Retry:
            continue
        if q["prompt"] in seen:
            continue
        seen.add(q["prompt"])
        out.append(q)
    return out


def ri(rng, lo, hi, nz=True, excl=()):
    while True:
        v = rng.randint(lo, hi)
        if (nz and v == 0) or v in excl:
            continue
        return v


def sgn(rng):
    return rng.choice((1, -1))


# ================================================================ 文字と式


# ---- 004 代入と式の値
def _subst(terms):
    """terms: [(係数, 代入後の表示 or None, その値)] -> '2×3+5=6+5=11'"""
    s = ""
    for c, shown, _ in terms:
        a = abs(c)
        body = str(a) if shown is None else (shown if a == 1 else f"{a}×{shown}")
        s += (M if c < 0 else ("+" if s else "")) + body
    vals = [c * v for c, _, v in terms]
    tot = sum(vals)
    mid = fsum([(v, "") for v in vals])
    if len(vals) > 1 and mid != num(tot):
        return f"{s}={mid}={num(tot)}", tot
    return f"{s}={num(tot)}", tot


def _poly_subst(p, v):
    terms = []
    for k in range(len(p) - 1, -1, -1):
        if p[k] != 0:
            terms.append((p[k], None if k == 0 else pn(v) + sup(k), F(v) ** k))
    return _subst(terms)


def _a004_one(neg, quad):
    def mk(rng):
        if quad:
            p = P(rng.choice((1, 1, 2, -1, 3)), ri(rng, -6, 6), ri(rng, -8, 8, nz=False))
        else:
            p = P(ri(rng, -6, 6, excl=(1,)), ri(rng, -9, 9))
        v = -ri(rng, 1, 5) if neg else ri(rng, 2, 6)
        ex, tot = _poly_subst(p, v)
        return numq(f"x={num(v)} のとき、{fpoly(p)} の値を求めなさい。", tot, ex + "。")
    return mk


def _a004_two(rng):
    a, b = ri(rng, -5, 5, excl=(1,)), ri(rng, -5, 5)
    x, y = ri(rng, -5, 5), ri(rng, -5, 5)
    if x > 0 and y > 0:
        raise Retry
    ex, tot = _subst([(a, pn(x), x), (b, pn(y), y)])
    return numq(f"x={num(x)}, y={num(y)} のとき、{fsum([(a, 'x'), (b, 'y')])} の値を求めなさい。",
                tot, ex + "。")


def gen_a004(rng):
    return collect(rng, [_a004_one(False, False), _a004_one(True, True), _a004_one(False, True),
                         _a004_one(True, False), _a004_two])


# ---- 005 一次式の加法・減法
def _a005_plain(sub):
    def mk(rng):
        a, c = ri(rng, 1, 7), ri(rng, 1, 7)
        b, d = ri(rng, -9, 9), ri(rng, -9, 9)
        if rng.random() < 0.25:
            c = -c
        s = -1 if sub else 1
        if a + s * c == 0:
            raise Retry
        ans = P(a + s * c, b + s * d)
        opened = fsum([(a, "x"), (b, ""), (s * c, "x"), (s * d, "")])
        prompt = f"({fpoly(P(a, b))}){'−' if sub else '+'}({fpoly(P(c, d))}) を計算しなさい。"
        if sub:
            wrong = [P(a - c, b + d), P(a + c, b - d), P(c - a, d - b)]
            ex = f"−({fpoly(P(c, d))}) は {fsum([(-c, 'x'), (-d, '')])} となるので、{opened}={fpoly(ans)}。"
        else:
            wrong = [P(a + c, b - d), P(a - c, b + d), P(a + c, -b - d)]
            ex = f"かっこをはずして {opened}={fpoly(ans)}。"
        return poly_mc(rng, prompt, ans, wrong, ex)
    return mk


def _a005_coef(sub):
    def mk(rng):
        k, m = ri(rng, 2, 5), ri(rng, 2, 5)
        a, c = ri(rng, 1, 5), ri(rng, 1, 5)
        b, d = ri(rng, -6, 6), ri(rng, -6, 6)
        s = -1 if sub else 1
        if k * a + s * m * c == 0:
            raise Retry
        ans = P(k * a + s * m * c, k * b + s * m * d)
        opened = fsum([(k * a, "x"), (k * b, ""), (s * m * c, "x"), (s * m * d, "")])
        prompt = f"{k}({fpoly(P(a, b))}){'−' if sub else '+'}{m}({fpoly(P(c, d))}) を計算しなさい。"
        wrong = [P(k * a + s * m * c, b + s * d), P(k * a + s * m * c, k * b + s * d),
                 P(k * a + s * m * c, k * b - s * m * d), P(k * a - s * m * c, k * b - s * m * d)]
        return poly_mc(rng, prompt, ans, wrong, f"分配法則でかっこをはずすと {opened}={fpoly(ans)}。")
    return mk


def gen_a005(rng):
    return collect(rng, [_a005_plain(False), _a005_plain(True), _a005_coef(False), _a005_coef(True)])


# ---- 006 整式の加法・減法
def _rand_quad(rng):
    return P(rng.choice((1, 2, 3, -1, 4, -2)), ri(rng, -7, 7), ri(rng, -9, 9))


def _open(p, s):
    return [(s * p[k], xp("x", k)) for k in range(len(p) - 1, -1, -1)]


def _a006_plain(sub):
    def mk(rng):
        A, B = _rand_quad(rng), _rand_quad(rng)
        s = -1 if sub else 1
        ans = padd(A, pscale(B, s))
        if len(ans) < 3 or A == B:
            raise Retry
        opened = fsum(_open(A, 1) + _open(B, s))
        prompt = f"({fpoly(A)}){'−' if sub else '+'}({fpoly(B)}) を計算しなさい。"
        if sub:
            # 後ろの式の先頭の項だけ符号を変えてしまうミス、全部たしてしまうミス
            wrong = [psub(A, P(B[2], -B[1], -B[0])), padd(A, B), psub(B, A)]
            ex = f"かっこをはずすと {opened}、同類項をまとめて {fpoly(ans)}。"
        else:
            wrong = [padd(A, P(B[2], B[1], -B[0])), psub(A, B), padd(A, P(B[2], -B[1], B[0]))]
            ex = f"同類項をまとめると {opened}={fpoly(ans)}。"
        return poly_mc(rng, prompt, ans, wrong, ex)
    return mk


def _a006_ab(rng):
    A, B = _rand_quad(rng), _rand_quad(rng)
    k, m = rng.choice(((1, -1), (1, 1), (2, -1), (1, -2), (2, 1)))
    ans = padd(pscale(A, k), pscale(B, m))
    if len(ans) < 3:
        raise Retry
    op = fsum([(k, "A"), (m, "B")])
    lead = "" if k == 1 else str(k)
    mid = ("+" if m > 0 else M) + ("" if abs(m) == 1 else str(abs(m)))
    subst = f"{lead}({fpoly(A)}){mid}({fpoly(B)})"
    wrong = [padd(pscale(A, k), pscale(B, -m)), padd(A, pscale(B, m)), padd(pscale(A, k), B if m < 0 else pscale(B, -1)),
             padd(pscale(A, k), pscale(P(B[2], -B[1], -B[0]), abs(m) * (-1 if m < 0 else 1)))]
    return poly_mc(rng, f"A={fpoly(A)}, B={fpoly(B)} のとき、{op} を計算しなさい。", ans, wrong,
                   f"{op}={subst}={fsum(_open(A, k) + _open(B, m))}={fpoly(ans)}。")


def gen_a006(rng):
    return collect(rng, [_a006_plain(False), _a006_plain(True), _a006_ab])


# ---- 007 単項式の乗法・除法
def fmono(c, ex, ey=0):
    return fsum([(c, xp("x", ex) + xp("y", ey))])


def fmono_p(c, ex, ey=0):
    s = fmono(c, ex, ey)
    return f"({s})" if c < 0 else s


def _mono_cands(key, extra):
    c, ex, ey = key
    out = list(extra) + [(-c, ex, ey), (c, ex + 1, ey), (c, max(ex - 1, 0), ey), (c, ex, ey + 1), (c + 1, ex, ey)]
    return [(fmono(*k), k) for k in out if (k[1] + k[2]) > 0 and k[0] != 0]


def _letters(ex, ey):
    return xp("x", ex) + xp("y", ey)


def _a007_mul(with_y):
    def mk(rng):
        c1, c2 = ri(rng, 2, 6) * sgn(rng), ri(rng, -6, 6, excl=(1,))
        e1, e2 = ri(rng, 1, 3), ri(rng, 1, 3)
        y1, y2 = (ri(rng, 0, 2, nz=False), ri(rng, 1, 2)) if with_y else (0, 0)
        ans = (c1 * c2, e1 + e2, y1 + y2)
        extra = [(c1 + c2, e1 + e2, y1 + y2), (c1 * c2, e1 * e2, y1 * y2), (c1 * c2, e1 * e2, y1 + y2)]
        ex = (f"係数は {pn(c1)}×{pn(c2)}={num(c1 * c2)}、文字は {_letters(e1, y1)}×{_letters(e2, y2)}"
              f"={_letters(e1 + e2, y1 + y2)} なので {fmono(*ans)}。")
        return mcq(rng, f"{fmono(c1, e1, y1)}×{fmono_p(c2, e2, y2)} を計算しなさい。", (fmono(*ans), ans),
                   _mono_cands(ans, extra), ex)
    return mk


def _a007_sq(rng):
    c1, e1 = ri(rng, 2, 4) * sgn(rng), ri(rng, 1, 2)
    c2, e2, y2 = ri(rng, -5, 5, excl=(1, -1)), ri(rng, 1, 2), ri(rng, 0, 1, nz=False)
    ans = (c1 * c1 * c2, 2 * e1 + e2, y2)
    extra = [(c1 * c2, 2 * e1 + e2, y2), (c1 * c1 * c2, e1 + e2, y2), (2 * c1 * c2, 2 * e1 + e2, y2),
             (-c1 * c1 * c2, 2 * e1 + e2, y2)]
    ex = f"({fmono(c1, e1)})²={fmono(c1 * c1, 2 * e1)} なので、{fmono(c1 * c1, 2 * e1)}×{fmono_p(c2, e2, y2)}={fmono(*ans)}。"
    return mcq(rng, f"({fmono(c1, e1)})²×{fmono_p(c2, e2, y2)} を計算しなさい。", (fmono(*ans), ans),
               _mono_cands(ans, extra), ex)


def _a007_div(with_y):
    def mk(rng):
        cr, cd = ri(rng, 2, 6) * sgn(rng), ri(rng, 2, 6) * sgn(rng)
        er, ed = ri(rng, 0, 2, nz=False), ri(rng, 1, 2)
        fr, fd = (ri(rng, 0, 2, nz=False), ri(rng, 1, 2)) if with_y else (0, 0)
        if er + fr == 0:
            raise Retry
        dc, dx, dy = cr * cd, er + ed, fr + fd
        ans = (cr, er, fr)
        extra = [(cr, dx + ed, dy + fd), (cr * cd * cd, er, fr), (dc - cd, er, fr)]
        if ed > 1 and dx % ed == 0:
            extra.insert(1, (cr, dx // ed, fr))
        ex = (f"係数は {num(dc)}÷{pn(cd)}={num(cr)}、文字は {_letters(dx, dy)}÷{_letters(ed, fd)}"
              f"={_letters(er, fr)} なので {fmono(*ans)}。")
        return mcq(rng, f"{fmono(dc, dx, dy)}÷{fmono_p(cd, ed, fd)} を計算しなさい。", (fmono(*ans), ans),
                   _mono_cands(ans, extra), ex)
    return mk


def gen_a007(rng):
    return collect(rng, [_a007_mul(False), _a007_div(False), _a007_sq, _a007_div(True), _a007_mul(True)])


# ---- 009 多項式の乗法
def _expand_mc(rng, f1, f2, prompt):
    ans = pmul(f1, f2)
    partial = [(f1[i] * f2[j], i + j) for i in range(len(f1) - 1, -1, -1)
               for j in range(len(f2) - 1, -1, -1) if f1[i] * f2[j] != 0]
    opened = fsum([(c, xp("x", k)) for c, k in partial])

    def term(c, k):
        return trim([0] * k + [c])
    flips = [psub(ans, term(2 * c, k)) for c, k in partial if 0 < k < deg(ans)]
    omits = [psub(ans, term(c, k)) for c, k in partial if 0 < k < deg(ans)]
    rng.shuffle(flips)
    rng.shuffle(omits)
    wrong = flips[:2] + omits[:1] + flips[2:] + omits[1:]
    return poly_mc(rng, prompt, ans, wrong, f"{opened}={fpoly(ans)}。")


def _a009_lin(rng):
    a, c = rng.choice((1, 1, 1, 2, 3)), rng.choice((1, 1, 2))
    b, d = ri(rng, -7, 7), ri(rng, -7, 7)
    f1, f2 = L(a, b), L(c, d)
    if f1 == f2 or a * d + b * c == 0:
        raise Retry
    return _expand_mc(rng, f1, f2, f"({fpoly(f1)})({fpoly(f2)}) を展開しなさい。")


def _a009_quad(rng):
    f1 = L(rng.choice((1, 1, 2)), ri(rng, -5, 5))
    f2 = P(1, ri(rng, -5, 5), ri(rng, -5, 5))
    return _expand_mc(rng, f1, f2, f"({fpoly(f1)})({fpoly(f2)}) を展開しなさい。")


def gen_a009(rng):
    return collect(rng, [_a009_lin, _a009_quad])


# ---- 010 因数分解
def _fac_mc(rng, prompt, correct, cands, explain):
    """correct/cands: (表示, 展開した多項式)。展開して等しいものは誤答にしない。"""
    return mcq(rng, prompt, correct, cands, explain)


def _a010_common(rng):
    g, m = ri(rng, 2, 6), rng.choice((1, 1, 2))
    if rng.random() < 0.5:
        inner = P(ri(rng, 1, 3), ri(rng, -6, 6))
    else:
        inner = P(ri(rng, 1, 2), ri(rng, -5, 5), ri(rng, -5, 5))
        D = int(inner[1] ** 2 - 4 * inner[2] * inner[0])
        if D >= 0 and math.isqrt(D) ** 2 == D:  # 中の二次式がさらに因数分解できるものは除く
            raise Retry
    if math.gcd(*[int(c) for c in inner]) != 1:
        raise Retry
    full = fac_val([inner], g, m)
    neg = list(inner)
    neg[0] = -neg[0]
    neg = trim(neg)
    bigc = list(inner)
    bigc[0] = bigc[0] * g
    bigc = trim(bigc)
    alts = [([neg], g, m), ([bigc], g, m), ([inner], g, m + 1), ([inner], g, m - 1) if m > 1 else ([inner], g + 1, m),
            ([P(*[-c for c in reversed(inner)])], g, m)]
    cands = [(ffac(f, c, mm), fac_val(f, c, mm)) for f, c, mm in alts]
    return _fac_mc(rng, f"{fpoly(full)} を因数分解しなさい。", (ffac([inner], g, m), full), cands,
                   f"共通因数 {ffac([], g, m)} でくくると {ffac([inner], g, m)}。")


def _pair_disp(p, q):
    a, b = lin_order([p, q])
    return ffac([L(1, a), L(1, b)]), pmul(L(1, a), L(1, b))


def _a010_trin(rng):
    p, q = ri(rng, -9, 9), ri(rng, -9, 9)
    if p == q or p + q == 0:
        raise Retry
    full = pmul(L(1, p), L(1, q))
    cands = [_pair_disp(-p, -q), _pair_disp(p, -q), _pair_disp(-p, q)]
    c = p * q
    for r in range(1, abs(c) + 1):
        if c % r == 0:
            for s in (r, -r):
                cands.append(_pair_disp(s, c // s))
    a, b = lin_order([p, q])
    return _fac_mc(rng, f"{fpoly(full)} を因数分解しなさい。", _pair_disp(p, q), cands,
                   f"かけて {num(c)}、たして {num(p + q)} になる2数は {num(a)} と {num(b)}。")


def gen_a010(rng):
    return collect(rng, [_a010_common, _a010_trin])


# ---- 011 二次の展開公式・因数分解公式
def _first(b):
    return "x" if b == 1 else f"{b}x"


def _a011_sq_exp(big):
    def mk(rng):
        b = rng.choice((2, 3)) if big else 1
        a = ri(rng, -9, 9) if not big else ri(rng, -5, 5)
        if math.gcd(a, b) != 1:
            raise Retry
        ans = ppow(L(b, a), 2)
        wrong = [P(b * b, 0, a * a), P(b * b, a * b, a * a), P(b * b, -2 * a * b, a * a), P(b * b, 2 * a * b, -a * a),
                 P(b, 2 * a * b, a * a)]
        f = "x" if b == 1 else f"({b}x)"
        ex = f"(a+b)²=a²+2ab+b² より {f}²+2×{_first(b)}×{pn(a)}+{pn(a)}²={fpoly(ans)}。"
        return poly_mc(rng, f"({fpoly(L(b, a))})² を展開しなさい。", ans, wrong, ex)
    return mk


def _a011_diff_exp(rng):
    b, a = rng.choice((1, 1, 1, 2, 3)), ri(rng, 1, 9)
    if math.gcd(a, b) != 1:
        raise Retry
    ans = P(b * b, 0, -a * a)
    f1, f2 = L(b, a), L(b, -a)
    wrong = [P(b * b, 0, a * a), P(b * b, -2 * a * b, -a * a), P(b * b, 2 * a * b, -a * a), P(b, 0, -a * a),
             P(b * b, 0, -2 * a)]
    f = "x" if b == 1 else f"({b}x)"
    ex = f"(a+b)(a−b)=a²−b² より {f}²−{a}²={fpoly(ans)}。"
    return poly_mc(rng, f"({fpoly(f1)})({fpoly(f2)}) を展開しなさい。", ans, wrong, ex)


def _fc(factors, coef=1, mono=0):
    return ffac(factors, coef, mono), fac_val(factors, coef, mono)


def _a011_sq_fac(rng):
    b = rng.choice((1, 1, 1, 2, 3))
    a = ri(rng, -9, 9) if b == 1 else ri(rng, -5, 5)
    if math.gcd(a, b) != 1:
        raise Retry
    full = ppow(L(b, a), 2)
    cands = [_fc([L(b, -a)] * 2), _fc([L(b, a), L(b, -a)]), _fc([L(b, 2 * a)] * 2), _fc([L(1, 1), L(b * b, a * a)]),
             _fc([L(1, a * a), L(b * b, 1)]), _fc([L(b, a * a)] * 2)]
    f = "x" if b == 1 else f"({b}x)"
    ex = f"{fpoly(full)}={f}²+2×{_first(b)}×{pn(a)}+{pn(a)}² なので {ffac([L(b, a)] * 2)}。"
    return mcq(rng, f"{fpoly(full)} を因数分解しなさい。", _fc([L(b, a)] * 2), cands, ex)


def _a011_diff_fac(rng):
    b, a = rng.choice((1, 1, 2, 3)), ri(rng, 1, 9)
    if math.gcd(a, b) != 1:
        raise Retry
    full = P(b * b, 0, -a * a)
    cands = [_fc([L(b, a)] * 2), _fc([L(b, -a)] * 2), _fc([L(b, a * a), L(b, -a * a)]),
             _fc([L(b * b, a), L(1, -a)]), _fc([L(b, a), L(b, -2 * a)])]
    f = "x" if b == 1 else f"({b}x)"
    ex = f"a²−b²=(a+b)(a−b) より {f}²−{a}²={ffac([L(b, a), L(b, -a)])}。"
    return mcq(rng, f"{fpoly(full)} を因数分解しなさい。", _fc([L(b, a), L(b, -a)]), cands, ex)


def _a011_tasuki(rng):
    r, q, s = rng.choice((2, 3)), ri(rng, -5, 5), ri(rng, -5, 5)
    if math.gcd(r, s) != 1 or s + r * q == 0 or q == s:
        raise Retry
    full = pmul(L(1, q), L(r, s))
    cands = [_fc([L(1, s), L(r, q)]), _fc([L(1, -q), L(r, -s)]), _fc([L(1, q), L(r, -s)]), _fc([L(1, -q), L(r, s)])]
    ex = f"たすき掛けで 1×{pn(s)}+{pn(q)}×{r}={num(s + r * q)} となる組を探すと {ffac([L(1, q), L(r, s)])}。"
    return mcq(rng, f"{fpoly(full)} を因数分解しなさい。", _fc([L(1, q), L(r, s)]), cands, ex)


def gen_a011(rng):
    return collect(rng, [_a011_sq_exp(False), _a011_sq_fac, _a011_diff_exp, _a011_diff_fac,
                         _a011_sq_exp(True), _a011_tasuki])


# ---- 012 三次の展開公式・因数分解公式
def _a012_cube_exp(rng):
    b = rng.choice((1, 1, 1, 2))
    c = ri(rng, -3, 3)
    if b == 2 and c % 2 == 0:
        raise Retry
    ans = ppow(L(b, c), 3)
    wrong = [P(b ** 3, 0, 0, c ** 3), P(b ** 3, 3 * b * b * c, 3 * b * c, c ** 3), P(b ** 3, b * b * c, b * c * c, c ** 3),
             P(b ** 3, 3 * b * b * abs(c), 3 * b * c * c, abs(c) ** 3), P(b ** 3, 3 * b * b * c, -3 * b * c * c, c ** 3)]
    f = "x" if b == 1 else f"({b}x)"
    ex = f"(a+b)³=a³+3a²b+3ab²+b³ で a={_first(b)}, b={num(c)} として {fpoly(ans)}。"
    return poly_mc(rng, f"({fpoly(L(b, c))})³ を展開しなさい。", ans, wrong, ex)


def _a012_sum_exp(rng):
    b, a = rng.choice((1, 1, 2, 3)), ri(rng, 1, 4) * sgn(rng)
    if math.gcd(a, b) != 1:
        raise Retry
    f1, f2 = L(b, a), P(b * b, -a * b, a * a)
    ans = pmul(f1, f2)
    wrong = [P(b ** 3, 0, 0, -a ** 3), ppow(f1, 3), P(b ** 3, 0, 0, 3 * a ** 3), P(b ** 3, -2 * a * b * b, 0, a ** 3),
             P(b ** 3, 2 * a * b * b, 2 * a * a * b, a ** 3)]
    ex = (f"(a+b)(a²−ab+b²)=a³+b³ より {fpoly(ans)}。" if a > 0 else
          f"(a−b)(a²+ab+b²)=a³−b³ より {fpoly(ans)}。")
    return poly_mc(rng, f"({fpoly(f1)})({fpoly(f2)}) を展開しなさい。", ans, wrong, ex)


def _a012_sum_fac(rng):
    b, a = rng.choice((1, 1, 2, 3)), ri(rng, 1, 5) * sgn(rng)
    if math.gcd(a, b) != 1 or (b == 1 and abs(a) == 1 and rng.random() < 0.5):
        raise Retry
    full = P(b ** 3, 0, 0, a ** 3)
    cands = [_fc([L(b, a), P(b * b, a * b, a * a)]), _fc([L(b, -a), P(b * b, a * b, a * a)]),
             _fc([L(b, -a), P(b * b, -a * b, a * a)]), _fc([L(b, a), P(b * b, -2 * a * b, a * a)]), _fc([L(b, a)] * 3)]
    form = "a³+b³=(a+b)(a²−ab+b²)" if a > 0 else "a³−b³=(a−b)(a²+ab+b²)"
    ex = f"{fpoly(full)}={'x' if b == 1 else f'({b}x)'}³{'+' if a > 0 else M}{abs(a)}³ なので {form} を使う。"
    return mcq(rng, f"{fpoly(full)} を因数分解しなさい。", _fc([L(b, a), P(b * b, -a * b, a * a)]), cands, ex)


def _a012_cube_fac(rng):
    a = ri(rng, -3, 3)
    full = ppow(L(1, a), 3)
    cands = [_fc([L(1, -a)] * 3), _fc([L(1, a), P(1, -a, a * a)]), _fc([L(1, 3 * a)] * 3),
             _fc([L(1, a), P(1, a, a * a)])]
    ex = f"a³+3a²b+3ab²+b³=(a+b)³ の形なので {ffac([L(1, a)] * 3)}。"
    return mcq(rng, f"{fpoly(full)} を因数分解しなさい。", _fc([L(1, a)] * 3), cands, ex)


def gen_a012(rng):
    return collect(rng, [_a012_cube_exp, _a012_sum_fac, _a012_sum_exp, _a012_sum_fac, _a012_cube_exp, _a012_cube_fac])


# ---- 013 多項式の除法
def _a013(rem):
    def mk(rng):
        d = ri(rng, -5, 5)
        div = L(1, d)
        if rng.random() < 0.5:
            q = L(1, ri(rng, -6, 6))
        else:
            q = P(1, ri(rng, -5, 5), ri(rng, -6, 6))
        r = ri(rng, -9, 9) if rem else 0
        full = padd(pmul(div, q), P(r))
        if len(full) != len(q) + 1 or full[0] == 0:
            raise Retry
        wq, wr = pdivmod(full, L(1, -d))  # 符号を逆にして割ってしまうミス
        prompt = f"{fpoly(full)} を {fpoly(div)} で割った{'商と余り' if rem else '商'}を求めなさい。"
        if not rem:
            ex = f"{fpoly(full)}=({fpoly(div)})({fpoly(q)}) より、商は {fpoly(q)}。"
            return poly_mc(rng, prompt, q, [wq] + perturb(q)[:1], ex)

        def disp(qq, rr):
            return f"商 {fpoly(qq)}、余り {num(rr)}"
        cands = [(disp(q, -r), (q, F(-r))), (disp(wq, wr[0]), (wq, wr[0])), (disp(wq, -wr[0]), (wq, -wr[0]))]
        cands += [(disp(pq, r), (pq, F(r))) for pq in perturb(q)]
        ex = f"{fpoly(full)}=({fpoly(div)})({fpoly(q)}){'+' if r > 0 else M}{abs(r)} より、商 {fpoly(q)}、余り {num(r)}。"
        return mcq(rng, prompt, (disp(q, r), (q, F(r))), cands, ex)
    return mk


def gen_a013(rng):
    return collect(rng, [_a013(False), _a013(True)])


# ---- 014 分数式の四則計算
PTS = [F(7, 3), F(11, 5), F(13, 7), F(17, 11)]


def rkey(n, d):
    return tuple(peval(n, t) / peval(d, t) for t in PTS)


def _numer(s):
    return f"({s})" if any(ch in "+" + M for ch in s[1:]) else s


def _fden(fs):
    parts = [("x" + sup(deg(f))) if is_mono(f) else f"({fpoly(f)})" for f in fs]
    return parts[0] if len(parts) == 1 else "{" + "".join(parts) + "}"


def fr(n, dens):
    """n: 多項式 or 表示文字列、dens: 分母の因数リスト。(表示, キー) を返す。"""
    ns = _numer(fpoly(n)) if isinstance(n, tuple) else n
    return None if not dens else f"{ns}/{_fden(dens)}"


def rc(n, dens, nval=None):
    """分数式の候補 (表示, キー)。"""
    nv = nval if nval is not None else n
    if not dens:
        return fpoly(n), rkey(nv, ONE)
    return fr(n, dens), rkey(nv, pprod(*dens))


def _a014_mul1(rng):
    a, b, c = ri(rng, -6, 6), ri(rng, -6, 6), ri(rng, -6, 6)
    if len({a, b, c}) < 3 or a + b == 0:
        raise Retry
    n1 = pmul(L(1, a), L(1, b))
    prompt = f"{fr(n1, [L(1, c)])} × {fr(L(1, c), [L(1, a)])} を計算しなさい。"
    cands = [rc(L(1, a), []), rc(L(1, -b), []), rc(L(1, b), [L(1, c)]), rc(L(1, c), [L(1, a)]), rc(L(1, a), [L(1, c)])]
    ex = f"{fpoly(n1)}={ffac([L(1, a), L(1, b)])} と因数分解して約分すると {fpoly(L(1, b))}。"
    return mcq(rng, prompt, rc(L(1, b), []), cands, ex)


def _a014_div(rng):
    a = ri(rng, -6, 6)
    prompt = f"{fr(L(1, a), [P(1, 0, 0)])} ÷ {fr(P(1, 0, -a * a), [X])} を計算しなさい。"
    corr = rc(ONE, [X, L(1, -a)])
    cands = [rc(ONE, [X, L(1, a)]), rc(X, [L(1, -a)]), rc(ONE, [L(1, -a)]),
             (f"{ffac([L(1, a)] * 2 + [L(1, -a)])}/x³", rkey(pmul(ppow(L(1, a), 2), L(1, -a)), P(1, 0, 0, 0)))]
    ex = (f"÷ は逆数をかける。{fr(L(1, a), [P(1, 0, 0)])} × x/{{{ffac([L(1, a), L(1, -a)])}}} を約分して "
          f"{corr[0]}。")
    return mcq(rng, prompt, corr, cands, ex)


def _a014_mul2(rng):
    a, b = ri(rng, -6, 6), ri(rng, 1, 6)
    if abs(a) == b:
        raise Retry
    prompt = f"{fr(L(1, a), [L(1, -b)])} × {fr(P(1, 0, -b * b), [L(1, a)] * 2)} を計算しなさい。"
    fd = "(" + fpoly(L(1, a)) + ")²"
    prompt = f"{fr(L(1, a), [L(1, -b)])} × {_numer(fpoly(P(1, 0, -b * b)))}/{fd} を計算しなさい。"
    corr = rc(L(1, b), [L(1, a)])
    cands = [rc(L(1, -b), [L(1, a)]), rc(L(1, a), [L(1, b)]), rc(L(1, b), [L(1, -a)]), rc(ONE, [L(1, a)])]
    ex = f"{fpoly(P(1, 0, -b * b))}={ffac([L(1, b), L(1, -b)])} と因数分解して約分すると {corr[0]}。"
    return mcq(rng, prompt, corr, cands, ex)


def _a014_add1(rng):
    a = ri(rng, -6, 6)
    sub = rng.random() < 0.4
    dens = [X, L(1, a)]
    if not sub:
        n = L(2, a)
        prompt = f"1/x + 1/({fpoly(L(1, a))}) を計算しなさい。"
        cands = [(f"2/({fpoly(L(2, a))})", rkey(P(2), L(2, a))), rc(P(2), dens), rc(L(2, -a), dens), rc(P(a), dens),
                 rc(L(1, 2 * a), dens)]
        ex = f"通分すると ({fpoly(L(1, a))}+x)/{_fden(dens)}={fr(n, dens)}。"
    else:
        n = P(a)
        prompt = f"1/x − 1/({fpoly(L(1, a))}) を計算しなさい。"
        cands = [rc(P(-a), dens), rc(L(2, a), dens), rc(ONE, dens), (f"0/{_fden(dens)}", None)]
        cands = [c for c in cands if c[1] is not None] + [rc(P(2 * a), dens)]
        ex = f"通分すると ({fpoly(L(1, a))}−x)/{_fden(dens)}={fr(n, dens)}。"
    return mcq(rng, prompt, rc(n, dens), cands, ex)


def _a014_add2(rng):
    a = ri(rng, 1, 6)
    dens = [L(1, -a), L(1, a)]
    sub = rng.random() < 0.5
    op = M if sub else "+"
    n = P(2 * a) if sub else P(2, 0)
    prompt = f"1/({fpoly(L(1, -a))}) {op} 1/({fpoly(L(1, a))}) を計算しなさい。"
    cands = [rc(P(2, 0) if sub else P(2 * a), dens), rc(P(-2 * a), dens), rc(P(2), dens), rc(P(-2, 0), dens), rc(P(a), dens)]
    ex = f"通分すると {{({fpoly(L(1, a))}){op}({fpoly(L(1, -a))})}}/{_fden(dens)}={fr(n, dens)}。"
    return mcq(rng, prompt, rc(n, dens), cands, ex)


def _a014_add3(rng):
    p, q = ri(rng, 1, 4), ri(rng, 1, 4)
    a, b = ri(rng, -5, 5), ri(rng, -5, 5)
    if a >= b:
        raise Retry
    s = -1 if rng.random() < 0.4 else 1
    n = padd(pscale(L(1, b), p), pscale(L(1, a), s * q))
    if deg(n) < 1 or n[-1] < 0 or peval(n, -a) == 0 or peval(n, -b) == 0 or math.gcd(*[int(c) for c in n]) != 1:
        raise Retry
    dens = [L(1, a), L(1, b)]
    op = M if s < 0 else "+"
    prompt = f"{p}/({fpoly(L(1, a))}) {op} {q}/({fpoly(L(1, b))}) を計算しなさい。"
    wn = padd(pscale(L(1, b), p), pscale(L(1, a), -s * q))
    swap = padd(pscale(L(1, a), p), pscale(L(1, b), s * q))
    cands = [rc(wn, dens), rc(swap, dens), (f"{num(p + s * q)}/({fpoly(L(2, a + b))})", rkey(P(p + s * q), L(2, a + b)))
             if p + s * q != 0 else rc(pscale(n, -1), dens), rc(pscale(n, -1), dens)]
    ex = (f"通分すると {{{p}({fpoly(L(1, b))}){op}{q}({fpoly(L(1, a))})}}/{_fden(dens)}={fr(n, dens)}。"
          .replace("{1(", "{(").replace(f"{op}1(", f"{op}("))
    return mcq(rng, prompt, rc(n, dens), cands, ex)


def gen_a014(rng):
    return collect(rng, [_a014_mul1, _a014_add1, _a014_div, _a014_add2, _a014_mul2, _a014_add3])


# ================================================================ 方程式・不等式


# ---- 002 一元一次方程式
def _e002_basic(rng):
    a, b, x = ri(rng, -9, 9, excl=(1, -1)), ri(rng, -9, 9), ri(rng, -9, 9)
    c = a * x + b
    return numq(f"{fpoly(L(a, b))}={num(c)} を解きなさい。", x,
                f"{num(b)} を移項して {fpoly(P(a, 0))}={num(c)}{'−' if b > 0 else '+'}{abs(b)}={num(c - b)}、x={num(x)}。")


def _e002_both(rng):
    a, c = ri(rng, -9, 9), ri(rng, -9, 9)
    b, d = ri(rng, -9, 9), ri(rng, -9, 9)
    if a == c or c == 0:
        raise Retry
    x = F(d - b, a - c)
    if x.denominator not in (1, 2) or (x.denominator == 2 and rng.random() < 0.6):
        raise Retry
    ex = (f"移項して {fsum([(a, 'x'), (-c, 'x')])}={fsum([(d, ''), (-b, '')])}、"
          f"{fpoly(P(a - c, 0))}={num(d - b)} より x={num(x)}。")
    return numq(f"{fpoly(L(a, b))}={fpoly(L(c, d))} を解きなさい。", x, ex)


def _e002_paren(rng):
    k, b, x = ri(rng, 2, 6) * sgn(rng), ri(rng, -8, 8), ri(rng, -9, 9)
    rhs = k * (x + b)
    ex = f"かっこをはずして {fpoly(L(k, k * b))}={num(rhs)}、{fpoly(P(k, 0))}={num(rhs - k * b)} より x={num(x)}。"
    return numq(f"{num(k)}({fpoly(L(1, b))})={num(rhs)} を解きなさい。", x, ex)


def _e002_paren2(rng):
    k, b, m, x = ri(rng, 2, 5), ri(rng, -6, 6), ri(rng, 2, 5), ri(rng, -8, 8)
    lhs = pscale(L(1, b), k)
    # k(x+b) = m x + e
    e = k * (x + b) - m * x
    if k == m:
        raise Retry
    rhs = L(m, e)
    ex = f"かっこをはずして {fpoly(lhs)}={fpoly(rhs)}、{fpoly(P(k - m, 0))}={num(e - k * b)} より x={num(x)}。"
    return numq(f"{k}({fpoly(L(1, b))})={fpoly(rhs)} を解きなさい。", x, ex)


def gen_e002(rng):
    return collect(rng, [_e002_basic, _e002_paren, _e002_both, _e002_paren2])


# ---- 003 比例式
def _e003(pos):
    def mk(rng):
        p, q = ri(rng, 1, 9), ri(rng, 1, 9)
        if p == q or math.gcd(p, q) != 1:
            raise Retry
        k = ri(rng, 2, 6)
        # p:q = pk:qk。pos の位置を x にする
        vals = [p, q, p * k, q * k]
        if rng.random() < 0.3:  # 比の左側を約分されていない形にする
            t = ri(rng, 2, 3)
            vals[0], vals[1] = p * t, q * t
        x = vals[pos]
        if len({v for i, v in enumerate(vals) if i != pos}) < 3:
            raise Retry
        shown = [str(v) for v in vals]
        shown[pos] = "x"
        a, b, c, d = shown
        prompt = f"{a}:{b}={c}:{d} のとき、x の値を求めなさい。"
        # 外項の積 = 内項の積 (a·d = b·c)
        outer, inner = (0, 3), (1, 2)
        side_x, side_o = (outer, inner) if pos in outer else (inner, outer)
        other = [vals[i] for i in side_x if i != pos][0]
        prod = vals[side_o[0]] * vals[side_o[1]]
        ex = f"外項の積＝内項の積 より {fpoly(P(other, 0))}={vals[side_o[0]]}×{vals[side_o[1]]}={prod}"
        ex += "。" if other == 1 else f"、x={num(F(prod, other))}。"
        return numq(prompt, x, ex)
    return mk


def gen_e003(rng):
    return collect(rng, [_e003(2), _e003(3), _e003(0), _e003(1)])


# ---- 004 二元一次方程式
def _e004(find_y):
    def mk(rng):
        a, b = ri(rng, -5, 5), ri(rng, -5, 5)
        x, y = ri(rng, -6, 8), ri(rng, -6, 8)
        c = a * x + b * y
        if c == 0:
            raise Retry
        eq = f"{fsum([(a, 'x'), (b, 'y')])}={num(c)}"
        if find_y:
            ex = f"x={num(x)} を代入すると {fsum([(a * x, ''), (b, 'y')])}={num(c)}" + (f"、{fsum([(b, 'y')])}={num(c - a * x)} より y={num(y)}。" if b != 1 else f"、y={num(y)}。")
            return numq(f"{eq} で x={num(x)} のとき、y の値を求めなさい。", y, ex)
        ex = f"y={num(y)} を代入すると {fsum([(a, 'x'), (b * y, '')])}={num(c)}" + (f"、{fsum([(a, 'x')])}={num(c - b * y)} より x={num(x)}。" if a != 1 else f"、x={num(x)}。")
        return numq(f"{eq} で y={num(y)} のとき、x の値を求めなさい。", x, ex)
    return mk


def gen_e004(rng):
    return collect(rng, [_e004(True), _e004(False), _e004(True)])


# ---- 005 連立二元一次方程式
def _xy(x, y):
    return f"x={num(x)}, y={num(y)}"


def _pair_cands(x, y):
    out = [(y, x), (x, -y), (-x, y), (-y, -x), (-x, -y), (x + 1, y - 1), (x - 1, y + 1)]
    return [(_xy(a, b), (a, b)) for a, b in out]


def _e005_elim(rng):
    x, y = ri(rng, -6, 7), ri(rng, -6, 7)
    a1, b1 = ri(rng, 1, 5), ri(rng, -4, 4)
    a2 = ri(rng, -5, 5)
    mode = rng.choice(("same", "same", "mult"))
    if mode == "same":
        b2 = b1 * rng.choice((1, -1))
    else:
        b2 = b1 * rng.choice((2, 3, -2, -3))
    if a1 * b2 - a2 * b1 == 0 or (a1, b1) == (a2, b2):
        raise Retry
    c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
    e1, e2 = f"{fsum([(a1, 'x'), (b1, 'y')])}={num(c1)}", f"{fsum([(a2, 'x'), (b2, 'y')])}={num(c2)}"
    if b2 == -b1:
        step = f"2式をたすと {fpoly(P(a1 + a2, 0))}={num(c1 + c2)}"
    elif b2 == b1:
        step = f"2式をひくと {fpoly(P(a1 - a2, 0))}={num(c1 - c2)}"
    else:
        m = b2 // b1
        how = f"上の式×{m}−下の式" if m > 0 else f"上の式×{-m}+下の式"
        step = f"{how} で y を消すと {fpoly(P(m * a1 - a2, 0))}={num(m * c1 - c2)}"
    ex = f"{step} より x={num(x)}、代入して y={num(y)}。"
    return mcq(rng, f"連立方程式 {e1}, {e2} を解きなさい。", (_xy(x, y), (x, y)), _pair_cands(x, y), ex)


def _e005_subst(rng):
    x, y = ri(rng, -6, 7), ri(rng, -6, 7)
    p, q = ri(rng, -4, 4), ri(rng, -6, 6, nz=False)
    a, b = ri(rng, 1, 5), ri(rng, -4, 4)
    y = p * x + q
    if a + b * p == 0 or b == 0:
        raise Retry
    c = a * x + b * y
    e1 = f"y={fpoly(L(p, q))}"
    e2 = f"{fsum([(a, 'x'), (b, 'y')])}={num(c)}"
    ex = (f"y を代入して {fsum([(a, 'x'), (b * p, 'x'), (b * q, '')])}={num(c)}、"
          f"{fpoly(P(a + b * p, 0))}={num(c - b * q)} より x={num(x)}、y={num(y)}。")
    return mcq(rng, f"連立方程式 {e1}, {e2} を解きなさい。", (_xy(x, y), (x, y)), _pair_cands(x, y), ex)


def gen_e005(rng):
    return collect(rng, [_e005_elim, _e005_subst])


# ---- 解の表示とキー
def rkey_vals(vals):
    return tuple(sorted((round(complex(v).real, 9), round(complex(v).imag, 9)) for v in vals))


def simp_sqrt(n):
    k, m = 1, n
    for f in range(2, int(math.isqrt(n)) + 1):
        while m % (f * f) == 0:
            m //= f * f
            k *= f
    return k, m


def fsurd(p, k, m, d=1, imag=False):
    """(p ± k√m)/d（imag なら k√m i）。"""
    rt = ("" if k == 1 else str(k)) + (f"√{m}" if m != 1 else ("" if imag else "1"))
    if m == 1 and not imag and k == 1:
        rt = "1"
    if imag:
        rt += "i"
    core = (num(p) if p != 0 else "") + "±" + rt
    if d == 1:
        return core
    return f"({core})/{d}" if p != 0 else f"±{rt}/{d}"


def quad_roots(a, b, c):
    """ax²+bx+c=0 の解。(表示の中身, 値のリスト, 無理数/虚数か)"""
    D = b * b - 4 * a * c
    if D >= 0 and math.isqrt(D) ** 2 == D:
        s = math.isqrt(D)
        vals = sorted({F(-b + s, 2 * a), F(-b - s, 2 * a)})
        return ", ".join(num(v) for v in vals), vals, False
    k, m = simp_sqrt(abs(D))
    p, d = -b, 2 * a
    if d < 0:
        p, d = -p, -d
    g = math.gcd(math.gcd(p, k), d)
    p, k, d = p // g, k // g, d // g
    r = k * math.sqrt(m) / d
    vals = [p / d + (1j * r if D < 0 else r), p / d - (1j * r if D < 0 else r)]
    return fsurd(p, k, m, d, D < 0), vals, True


def fsol(vals):
    return "x=" + ", ".join(num(v) for v in sorted(set(vals)))


# ---- 006 二次方程式
def _e006_fac(rng):
    p, q = ri(rng, -8, 8, nz=False), ri(rng, -8, 8)
    if rng.random() < 0.7 and p == 0:
        raise Retry
    if p == q and rng.random() < 0.8:
        raise Retry
    k = rng.choice((1, 1, 1, 2, 3)) if p != 0 else 1
    full = pscale(pmul(L(1, -p), L(1, -q)), k)
    facs = [L(1, -v) for v in sorted([p, q], key=lambda v: (v > 0, abs(v))) if v != 0]
    fac = ffac(facs, 1, 1 if p == 0 else 0)
    ans = (fsol([p, q]), rkey_vals([p, q]))
    cands = [(fsol(s), rkey_vals(s)) for s in ([-p, -q], [p, -q], [-p, q], [p], [q], [p + q, p * q])]
    ex = (f"両辺を {k} で割って " if k > 1 else "") + f"{fac}=0 より {ans[0]}。"
    return mcq(rng, f"{fpoly(full)}=0 を解きなさい。", ans, cands, ex)


def _e006_sqrt(rng):
    kind = rng.choice(("sq", "sq", "nonsq", "shift"))
    if kind == "sq":
        m = ri(rng, 2, 12)
        k = rng.choice((1, 1, 2, 3))
        prompt = f"{fpoly(P(k, 0, 0))}={k * m * m} を解きなさい。"
        ans = (f"x=±{m}", rkey_vals([m, -m]))
        cands = [(f"x={m}", rkey_vals([m])), (f"x=±{m * m}", rkey_vals([m * m, -m * m])),
                 (f"x=±√{m}", rkey_vals([math.sqrt(m), -math.sqrt(m)])), (f"x={M}{m}", rkey_vals([-m]))]
        ex = (f"両辺を {k} で割って x²={m * m}、" if k > 1 else "") + f"x は {m * m} の平方根なので x=±{m}。"
        return mcq(rng, prompt, ans, cands, ex)
    if kind == "nonsq":
        n = ri(rng, 2, 50)
        k, mm = simp_sqrt(n)
        if mm == 1:
            raise Retry
        r = k * math.sqrt(mm)
        prompt = f"x²={n} を解きなさい。"
        ans = (f"x={fsurd(0, k, mm)}", rkey_vals([r, -r]))
        cands = [(f"x={fsurd(0, k, mm)[1:]}", rkey_vals([r])), (f"x=±{n}", rkey_vals([n, -n])),
                 (f"x=±{F(n, 2)}", rkey_vals([n / 2, -n / 2])), (f"x=±{n * n}", rkey_vals([n * n, -n * n]))]
        if k > 1:
            cands.insert(1, (f"x=±{mm}√{k}", rkey_vals([mm * math.sqrt(k), -mm * math.sqrt(k)])))
        ex = f"x は {n} の平方根なので x={fsurd(0, k, mm)}。"
        return mcq(rng, prompt, ans, cands, ex)
    a = ri(rng, -6, 6)
    n = ri(rng, 2, 30)
    prompt = f"({fpoly(L(1, a))})²={n} を解きなさい。"
    k, mm = simp_sqrt(n)
    if mm == 1:
        vals = [-a + k, -a - k]
        ans = (fsol(vals), rkey_vals(vals))
        cands = [(fsol([a + k, a - k]), rkey_vals([a + k, a - k])), (fsol([-a + k]), rkey_vals([-a + k])),
                 (fsol([-a + n, -a - n]), rkey_vals([-a + n, -a - n])), (fsol([a + n, a - n]), rkey_vals([a + n, a - n]))]
        ex = f"{fpoly(L(1, a))}=±{k} より {ans[0]}。"
    else:
        r = k * math.sqrt(mm)
        ans = (f"x={fsurd(-a, k, mm)}", rkey_vals([-a + r, -a - r]))
        cands = [(f"x={fsurd(a, k, mm)}", rkey_vals([a + r, a - r])), (fsol([-a + n, -a - n]), rkey_vals([-a + n, -a - n])),
                 (f"x={num(-a)}+{fsurd(0, k, mm)[1:]}", rkey_vals([-a + r])), (f"x=±{fsurd(0, k, mm)[1:]}", rkey_vals([r, -r]))]
        ex = f"{fpoly(L(1, a))}={fsurd(0, k, mm)} より x={fsurd(-a, k, mm)}。"
    return mcq(rng, prompt, ans, cands, ex)


def gen_e006(rng):
    return collect(rng, [_e006_fac, _e006_sqrt])


# ---- 007 解の公式
def _e007(rng):
    a = rng.choice((1, 1, 1, 2, 3))
    b, c = ri(rng, -7, 7), ri(rng, -6, 6)
    disp, vals, irr = quad_roots(a, b, c)
    if not irr or b * b - 4 * a * c < 0:
        raise Retry
    D = b * b - 4 * a * c
    cands = []
    for aa, bb, cc in ((a, -b, c), (a, b, -c), (a, 2 * b, 4 * c), (a, -b, -c), (a, b, c + 1), (a, b, c - 1)):
        dd, vv, ii = quad_roots(aa, bb, cc)
        if ii and bb * bb - 4 * aa * cc > 0:
            cands.append((f"x={dd}", rkey_vals(vv)))
    raw = f"({num(-b)}±√{D})/{2 * a}"
    ex = f"解の公式より x={raw}" + ("" if raw == disp else f"={disp}") + "。"
    return mcq(rng, f"{fpoly(P(a, b, c))}=0 を解きなさい。", (f"x={disp}", rkey_vals(vals)), cands, ex)


def gen_e007(rng):
    return collect(rng, [_e007])


# ---- 008 一次不等式
FLIP = {">": "<", "<": ">", "≧": "≦", "≦": "≧"}
STRICT = {">": "≧", "≧": ">", "<": "≦", "≦": "<"}


def _ineq(op, t):
    return f"x{op}{num(t)}"


def _e008(neg, both):
    def mk(rng):
        op = rng.choice((">", "<", "≧", "≦"))
        if both:
            a, c = ri(rng, -6, 6), ri(rng, -6, 6)
            if (a - c > 0) == neg or a == c or c == 0:
                raise Retry
        else:
            a, c = ri(rng, 2, 7) * (-1 if neg else 1), 0
        k = a - c
        b = ri(rng, -9, 9)
        t = ri(rng, -6, 8, nz=False) if rng.random() < 0.85 else F(ri(rng, -9, 9), abs(k))
        d = k * t + b if both else None
        if both:
            if F(d).denominator != 1:
                raise Retry
            lhs, rhs = fpoly(L(a, b)), fpoly(L(c, d))
            rest = d - b
        else:
            rhs_v = k * t + b
            if F(rhs_v).denominator != 1:
                raise Retry
            lhs, rhs = fpoly(L(a, b)), num(rhs_v)
            rest = rhs_v - b
        t = F(t)
        res_op = FLIP[op] if k < 0 else op
        ans = (_ineq(res_op, t), (res_op, t))
        cands = [(_ineq(FLIP[res_op], t), (FLIP[res_op], t)), (_ineq(res_op, -t), (res_op, -t)),
                 (_ineq(FLIP[res_op], -t), (FLIP[res_op], -t)), (_ineq(STRICT[res_op], t), (STRICT[res_op], t))]
        if neg:
            cands = [cands[0], cands[1], cands[2], cands[3]]
        else:
            cands = [cands[1], cands[0], cands[3], cands[2]]
        step = f"移項して {fpoly(P(k, 0))}{op}{num(rest)}"
        if k < 0:
            ex = f"{step}、両辺を {num(k)} で割ると不等号の向きが変わり {ans[0]}。"
        elif k == 1:
            ex = f"{step}。"
        else:
            ex = f"{step}、両辺を {k} で割って {ans[0]}。"
        return mcq(rng, f"{lhs}{op}{rhs} を解きなさい。", ans, cands, ex)
    return mk


def gen_e008(rng):
    return collect(rng, [_e008(False, False), _e008(True, False), _e008(False, True), _e008(True, True)])


# ---- 009 二次不等式
def _region(kind, p, q, strict):
    lt = "<" if strict else "≦"
    if kind == "out":
        return f"x{lt}{num(p)}, {num(q)}{lt}x"
    return f"{num(p)}{lt}x{lt}{num(q)}"


def _e009(rng):
    p, q = ri(rng, -7, 7, nz=False), ri(rng, -7, 7, nz=False)
    if p >= q:
        raise Retry
    a = rng.choice((1, 1, 1, 2, -1))
    op = rng.choice((">", "<", "≧", "≦"))
    full = pscale(pmul(L(1, -p), L(1, -q)), a)
    eff = FLIP[op] if a < 0 else op
    kind = "out" if eff in (">", "≧") else "in"
    strict = eff in (">", "<")
    other = "in" if kind == "out" else "out"
    ans = (_region(kind, p, q, strict), (kind, p, q, strict))
    cands = [(_region(other, p, q, strict), (other, p, q, strict)), (_region(kind, -q, -p, strict), (kind, -q, -p, strict)),
             (_region(kind, p, q, not strict), (kind, p, q, not strict)),
             (_region(other, -q, -p, strict), (other, -q, -p, strict))]
    base = pmul(L(1, -p), L(1, -q))
    facs = [L(1, -v) for v in (p, q) if v != 0]
    fac = ffac(facs, 1, 1 if 0 in (p, q) else 0)
    pre = ""
    if a == -1:
        pre = f"両辺に −1 をかけると向きが変わり {fpoly(base)}{eff}0。"
    elif a == 2:
        pre = f"両辺を 2 で割って {fpoly(base)}{eff}0。"
    ex = pre + f"{fac}{eff}0 より {ans[0]}。"
    return mcq(rng, f"{fpoly(full)}{op}0 を解きなさい。", ans, cands, ex)


def gen_e009(rng):
    return collect(rng, [_e009])


# ---- 011 複素数の四則計算
def fcx(re, im):
    re, im = F(re), F(im)
    if im == 0:
        return num(re)
    ims = ("" if abs(im) == 1 else str(abs(im))) + "i"
    if re == 0:
        return (M if im < 0 else "") + ims
    return num(re) + (M if im < 0 else "+") + ims


def _cx_cands(ans, extra):
    re, im = ans
    out = list(extra) + [(re, -im), (-re, im), (re + 1, im), (re, im + 1), (re - 1, im - 1)]
    return [(fcx(*k), k) for k in out]


def _rand_cx(rng, real_nz=True):
    return ri(rng, -6, 6) if real_nz else ri(rng, -6, 6, nz=False), ri(rng, -6, 6)


def _e011_addsub(sub):
    def mk(rng):
        (a, b), (c, d) = _rand_cx(rng), _rand_cx(rng)
        s = -1 if sub else 1
        ans = (a + s * c, b + s * d)
        if ans == (0, 0):
            raise Retry
        extra = [(a + s * c, b - s * d), (a - s * c, b + s * d)] if sub else [(a + c, b - d), (a - c, b + d)]
        ex = f"実部どうし {fsum([(a, ''), (s * c, '')])}={num(ans[0])}、虚部どうし {fsum([(b, ''), (s * d, '')])}={num(ans[1])} で {fcx(*ans)}。"
        return mcq(rng, f"({fcx(a, b)}){'−' if sub else '+'}({fcx(c, d)}) を計算しなさい。", (fcx(*ans), ans),
                   _cx_cands(ans, extra), ex)
    return mk


def _e011_mul(rng):
    (a, b), (c, d) = _rand_cx(rng), _rand_cx(rng)
    if (a, b) == (c, d) or (a, b) == (c, -d):
        raise Retry
    ans = (a * c - b * d, a * d + b * c)
    extra = [(a * c + b * d, a * d + b * c), (a * c, b * d), (a * c - b * d, -(a * d + b * c))]
    opened = fsum([(a * c, ""), (a * d, "i"), (b * c, "i"), (b * d, "i²")])
    ex = f"展開すると {opened}、i²=−1 より {fcx(*ans)}。"
    return mcq(rng, f"({fcx(a, b)})({fcx(c, d)}) を計算しなさい。", (fcx(*ans), ans), _cx_cands(ans, extra), ex)


def _e011_special(rng):
    kind = rng.choice(("sq", "conj", "i"))
    a, b = _rand_cx(rng)
    if kind == "sq":
        ans = (a * a - b * b, 2 * a * b)
        extra = [(a * a + b * b, 2 * a * b), (a * a - b * b, 0), (a * a + b * b, 0)]
        ex = f"{fsum([(a * a, ''), (2 * a * b, 'i'), (b * b, 'i²')])} で、i²=−1 より {fcx(*ans)}。"
        prompt = f"({fcx(a, b)})² を計算しなさい。"
    elif kind == "conj":
        ans = (a * a + b * b, 0)
        extra = [(a * a - b * b, 0), (a * a + b * b, 2 * a * b), (a * a - b * b, -2 * a * b)]
        ex = f"(a+bi)(a−bi)=a²+b² より {a * a}+{b * b}={a * a + b * b}。"
        prompt = f"({fcx(a, b)})({fcx(a, -b)}) を計算しなさい。"
    else:
        k = ri(rng, -4, 4)
        ans = (-k * b, k * a)
        extra = [(k * b, k * a), (k * a, -k * b), (k * a, k * b)]
        ex = f"{fsum([(k * a, 'i'), (k * b, 'i²')])} で、i²=−1 より {fcx(*ans)}。"
        prompt = f"{fcx(0, k)}({fcx(a, b)}) を計算しなさい。"
    return mcq(rng, prompt, (fcx(*ans), ans), _cx_cands(ans, extra), ex)


def gen_e011(rng):
    return collect(rng, [_e011_addsub(False), _e011_mul, _e011_addsub(True), _e011_special])


# ---- 012 判別式
def _dexpl(a, b, c):
    D = b * b - 4 * a * c
    return D, f"D={pn(b)}²−4×{pn(a)}×{pn(c)}={num(D)}"


def _e012_value(rng):
    a = rng.choice((1, 1, 2, 3, -1))
    b, c = ri(rng, -8, 8), ri(rng, -8, 8)
    D, ex = _dexpl(a, b, c)
    return numq(f"{fpoly(P(a, b, c))}=0 の判別式 D の値を求めなさい。", D, ex + "。")


def _e012_count(sign):
    def mk(rng):
        if sign == 0:
            p, q = rng.choice((1, 1, 2, 3)), ri(rng, -5, 5)
            if math.gcd(p, q) != 1:
                raise Retry
            a, b, c = p * p, 2 * p * q, q * q
        else:
            a, b, c = rng.choice((1, 1, 2, 3)), ri(rng, -7, 7), ri(rng, -8, 8)
        D, ex = _dexpl(a, b, c)
        if (D > 0) - (D < 0) != sign:
            raise Retry
        cnt = {1: 2, 0: 1, -1: 0}[sign]
        tail = {1: " > 0 なので実数解は2個。", 0: " なので重解（実数解は1個）。", -1: " < 0 なので実数解はない（0個）。"}[sign]
        return numq(f"{fpoly(P(a, b, c))}=0 の実数解の個数を求めなさい。", cnt, ex + tail)
    return mk


def gen_e012(rng):
    return collect(rng, [_e012_value, _e012_count(1), _e012_value, _e012_count(0), _e012_value, _e012_count(-1)])


# ---- 015 高次方程式
def _found_root(poly):
    for r in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5):
        if peval(poly, r) == 0:
            return r
    raise Retry


def _cubic_explain(poly, r, sol):
    q, rem = pdivmod(poly, L(1, -r))
    assert rem == (0,)
    return f"x={num(r)} のとき左辺=0 なので、{ffac([L(1, -r), q])}=0 より {sol}。"


def _e015_int(rng):
    rs = [ri(rng, -4, 5, nz=False) for _ in range(3)]
    if len(set(rs)) < 3 and rng.random() < 0.85:
        raise Retry
    if 0 in rs:
        raise Retry
    poly = pprod(*[L(1, -r) for r in rs])
    if any(c == 0 for c in poly):
        raise Retry
    ans = (fsol(rs), rkey_vals(rs))
    r = _found_root(poly)
    wrongs = [[-v for v in rs]]
    for i in range(3):
        w = list(rs)
        w[i] = -w[i]
        wrongs.append(w)
    wrongs.append([rs[0], rs[1] + 1, rs[2] - 1])
    cands = [(fsol(w), rkey_vals(w)) for w in wrongs]
    return mcq(rng, f"{fpoly(poly)}=0 を解きなさい。", ans, cands, _cubic_explain(poly, r, ans[0]))


def _e015_surd(rng):
    r = ri(rng, -3, 3)
    b, c = ri(rng, -4, 4), ri(rng, -5, 5)
    qd, qv, irr = quad_roots(1, b, c)
    if not irr or b * b - 4 * c < 0:
        raise Retry
    poly = pmul(L(1, -r), P(1, b, c))
    if any(x == 0 for x in poly) or _found_root(poly) != r:
        raise Retry
    ans = (f"x={num(r)}, {qd}", rkey_vals([r] + qv))
    cands = []
    for rr, bb, cc in ((r, -b, c), (-r, b, c), (-r, -b, c), (r, b, -c)):
        d2, v2, i2 = quad_roots(1, bb, cc)
        if i2:
            cands.append((f"x={num(rr)}, {d2}", rkey_vals([rr] + v2)))
    return mcq(rng, f"{fpoly(poly)}=0 を解きなさい。", ans, cands, _cubic_explain(poly, r, ans[0]))


def _e015_cube(rng):
    a = ri(rng, 1, 3) * sgn(rng)
    qd, qv, _ = quad_roots(1, a, a * a)
    ans = (f"x={num(a)}, {qd}", rkey_vals([a] + qv))
    cands = [(f"x={num(a)}", rkey_vals([a])), (f"x=±{a if a > 0 else -a}", rkey_vals([a, -a]))]
    for rr, bb in ((-a, -a), (a, -a), (-a, a)):
        d2, v2, _ = quad_roots(1, bb, a * a)
        cands.append((f"x={num(rr)}, {d2}", rkey_vals([rr] + v2)))
    prompt = f"x³={num(a ** 3)} を解きなさい。" if rng.random() < 0.5 else f"{fpoly(P(1, 0, 0, -a ** 3))}=0 を解きなさい。"
    ex = f"{fpoly(P(1, 0, 0, -a ** 3))}={ffac([L(1, -a), P(1, a, a * a)])}=0 より {ans[0]}。"
    return mcq(rng, prompt, ans, cands, ex)


def _e015_quartic(rng):
    p, q = ri(rng, 1, 4), ri(rng, 1, 5)
    if p >= q:
        raise Retry
    poly = pmul(P(1, 0, -p * p), P(1, 0, -q * q))
    ans = (f"x=±{p}, ±{q}", rkey_vals([p, -p, q, -q]))
    cands = [(f"x={p}, {q}", rkey_vals([p, q])), (f"x=±{p * p}, ±{q * q}", rkey_vals([p * p, -p * p, q * q, -q * q])),
             (f"x={p * p}, {q * q}", rkey_vals([p * p, q * q])), (f"x=±{p}, ±{q}i", rkey_vals([p, -p, q * 1j, -q * 1j]))]
    ex = f"x²=t とおくと {fpoly(P(1, -(p * p + q * q), p * p * q * q), 't')}=0 より t={p * p}, {q * q}、よって {ans[0]}。"
    return mcq(rng, f"{fpoly(poly)}=0 を解きなさい。", ans, cands, ex)


def gen_e015(rng):
    return collect(rng, [_e015_int, _e015_surd, _e015_int, _e015_cube, _e015_int, _e015_quartic])


GENERATORS = {
    "math-algebraic-expressions-004": gen_a004,
    "math-algebraic-expressions-005": gen_a005,
    "math-algebraic-expressions-006": gen_a006,
    "math-algebraic-expressions-007": gen_a007,
    "math-algebraic-expressions-009": gen_a009,
    "math-algebraic-expressions-010": gen_a010,
    "math-algebraic-expressions-011": gen_a011,
    "math-algebraic-expressions-012": gen_a012,
    "math-algebraic-expressions-013": gen_a013,
    "math-algebraic-expressions-014": gen_a014,
    "math-equations-inequalities-002": gen_e002,
    "math-equations-inequalities-003": gen_e003,
    "math-equations-inequalities-004": gen_e004,
    "math-equations-inequalities-005": gen_e005,
    "math-equations-inequalities-006": gen_e006,
    "math-equations-inequalities-007": gen_e007,
    "math-equations-inequalities-008": gen_e008,
    "math-equations-inequalities-009": gen_e009,
    "math-equations-inequalities-011": gen_e011,
    "math-equations-inequalities-012": gen_e012,
    "math-equations-inequalities-015": gen_e015,
}
