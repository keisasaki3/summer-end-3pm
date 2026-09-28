"""関数・三角比/三角関数の計算問題ジェネレータ。

答えはすべて Fraction と「a + b√c」形式の厳密計算（クラス Q）で求める。
float は検算にだけ使う。
"""
import math
from fractions import Fraction as F

MINUS = "−"


# ---------------------------------------------------------------- 厳密な数 a+b√m+...
def _sqfree(n):
    """n = k² * m (m は平方因子なし) の (k, m) を返す。"""
    k, m = 1, n
    d = 2
    while d * d <= m:
        while m % (d * d) == 0:
            m //= d * d
            k *= d
        d += 1
    return k, m


class Q:
    """有理数係数の平方根の和。terms = {平方因子なしの m: 係数}。m=1 が有理部分。"""

    def __init__(self, terms=None):
        self.t = {m: F(c) for m, c in (terms or {}).items() if c != 0}

    @staticmethod
    def R(x):
        return Q({1: F(x)})

    @staticmethod
    def S(n, coef=1):
        k, m = _sqfree(n)
        return Q({m: F(coef) * k})

    @staticmethod
    def sqrt(x):
        """有理数 x≧0 の平方根。"""
        x = F(x)
        assert x >= 0
        p, q = x.numerator, x.denominator
        return Q.S(p * q, F(1, q))

    def _lift(self, o):
        return o if isinstance(o, Q) else Q.R(o)

    def __add__(self, o):
        o = self._lift(o)
        t = dict(self.t)
        for m, c in o.t.items():
            t[m] = t.get(m, 0) + c
        return Q(t)

    __radd__ = __add__

    def __neg__(self):
        return Q({m: -c for m, c in self.t.items()})

    def __sub__(self, o):
        return self + (-self._lift(o))

    def __rsub__(self, o):
        return self._lift(o) - self

    def __mul__(self, o):
        o = self._lift(o)
        r = Q()
        for m, a in self.t.items():
            for n, b in o.t.items():
                r = r + Q.S(m * n, a * b)
        return r

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = self._lift(o)
        if not o.t:
            raise ZeroDivisionError
        surds = [m for m in o.t if m != 1]
        if len(surds) > 1:
            raise ValueError("分母の有理化に未対応")
        if not surds:
            return self * Q.R(1 / o.t[1])
        n = surds[0]
        p, q = o.t.get(1, F(0)), o.t[n]
        conj = Q({1: p, n: -q})
        den = p * p - q * q * n
        return self * conj * Q.R(1 / den)

    def __rtruediv__(self, o):
        return self._lift(o) / self

    def __eq__(self, o):
        return self.t == self._lift(o).t

    def __hash__(self):
        return hash(tuple(sorted(self.t.items())))

    def __float__(self):
        return float(sum(float(c) * math.sqrt(m) for m, c in self.t.items()))

    def is_rational(self):
        return all(m == 1 for m in self.t)

    def rat(self):
        assert self.is_rational()
        return self.t.get(1, F(0))

    def square(self):
        return self * self


def fmt(q):
    """表示用の正準形。例: 7, −3, 5/2, 4√2, −√3/2, (√6+√2)/4, 2−√3, −(√6+√2)/4"""
    if not isinstance(q, Q):
        q = Q.R(q)
    if not q.t:
        return "0"
    D = 1
    for c in q.t.values():
        D = D * c.denominator // math.gcd(D, c.denominator)
    terms = [(m, int(c * D)) for m, c in q.t.items()]
    terms.sort(key=lambda mc: (mc[0] != 1, -mc[0]))

    def body(m, k):
        k = abs(k)
        if m == 1:
            return str(k)
        return ("" if k == 1 else str(k)) + "√" + str(m)

    if len(terms) == 1:
        m, k = terms[0]
        s = (MINUS if k < 0 else "") + body(m, k)
        return s + (f"/{D}" if D > 1 else "")
    pos = [t for t in terms if t[1] > 0]
    neg = [t for t in terms if t[1] < 0]
    outer = ""
    if not pos:
        if D > 1:
            outer = MINUS
            pos, neg = [(m, -k) for m, k in neg], []
        ordered = pos + neg
    else:
        ordered = pos + neg
    s = ""
    for i, (m, k) in enumerate(ordered):
        sign = MINUS if k < 0 else ("+" if i else "")
        s += sign + body(m, k)
    if D > 1:
        return f"{outer}({s})/{D}"
    return outer + s


def ans_str(x):
    """数字入力の正準答え（ASCII）。"""
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def accepts(x):
    x = F(x)
    out = []
    if x.denominator != 1:
        d = x.denominator
        while d % 2 == 0:
            d //= 2
        while d % 5 == 0:
            d //= 5
        if d == 1:
            s = f"{float(x):.6f}".rstrip("0").rstrip(".")
            out.append(s)
    return out


def num_q(prompt, x, explain):
    x = x.rat() if isinstance(x, Q) else F(x)
    q = {"format": "数字入力", "prompt": prompt, "answer": ans_str(x), "explain": explain}
    acc = accepts(x)
    if acc:
        q["accept"] = acc
    return q


def mc_q(prompt, correct, cands, explain, rng):
    opts = [correct]
    for c in cands:
        if c is not None and c not in opts:
            opts.append(c)
        if len(opts) == 4:
            break
    if len(opts) < 4:
        return None
    rng.shuffle(opts)
    return {"format": "4択", "prompt": prompt, "options": opts,
            "answer": opts.index(correct), "explain": explain}


def run(rng, plan):
    """plan = [(maker, 個数)]。重複を避けて集め、シャッフルして返す。"""
    out, seen = [], set()
    for maker, n in plan:
        got, tries = 0, 0
        while got < n:
            tries += 1
            if tries > 3000:
                raise RuntimeError(f"{maker.__name__}: 問題が作れない")
            q = maker(rng)
            if q is None or q["prompt"] in seen or q.get("_key") in seen:
                continue
            seen.add(q["prompt"])
            if "_key" in q:
                seen.add(q.pop("_key"))
            out.append(q)
            got += 1
    rng.shuffle(out)
    return out


# ---------------------------------------------------------------- 表示ヘルパ
def d(x):
    """数値の表示（負号は −）。"""
    return fmt(Q.R(x)) if not isinstance(x, Q) else fmt(x)


def term(c, var, first):
    """c·var の項。first=True なら先頭項。"""
    c = F(c)
    if c == 0:
        return ""
    sign = (MINUS if c < 0 else "") if first else (MINUS if c < 0 else "+")
    a = abs(c)
    if var:
        if a == 1:
            mag = ""
        elif a.denominator != 1:
            mag = f"({a.numerator}/{a.denominator})"
        else:
            mag = str(a)
    else:
        mag = ans_str(a)
    return sign + mag + var


def poly(coefs):
    """[(係数, 変数文字列)] を並べる。"""
    s = ""
    for c, v in coefs:
        if c != 0:
            s += term(c, v, s == "")
    return s or "0"


def lin(a, b):
    return "y=" + poly([(a, "x"), (b, "")])


def quad(a, b, c, var="x"):
    return poly([(a, var + "²"), (b, var), (c, "")])


def vform(a, p, q):
    """a(x−p)²+q"""
    inner = "x" if p == 0 else ("x" + (MINUS + d(p) if p > 0 else "+" + d(-p)))
    sq = f"({inner})²" if p != 0 else "x²"
    s = ("" if a == 1 else (MINUS if a == -1 else d(a))) + sq
    if q:
        s += (MINUS if q < 0 else "+") + d(abs(q))
    return s


def pn(x):
    """負なら括弧付き。"""
    return f"({d(x)})" if x < 0 else d(x)


def pt(x, y):
    return f"({d(x)}, {d(y)})"


def nz(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v:
            return v


# ================================================================ 関数
def f003_const(rng):
    a = rng.choice([2, 3, 4, 5, -2, -3, -4, 6, F(1, 2), F(-3, 2), F(2, 3)])
    x = nz(rng, -6, 6) * a.denominator if isinstance(a, F) else nz(rng, -6, 6)
    if abs(x) == 1:
        return None
    y = F(a) * x
    return num_q(f"yはxに比例し、x={d(x)}のときy={d(y)}である。比例定数を求めなさい。", a,
                 f"y=axに代入して a={d(y)}÷{'(' + d(x) + ')' if x < 0 else d(x)}={d(a)}。")


def f003_value(rng):
    a = nz(rng, -7, 7)
    if abs(a) == 1:
        return None
    x = nz(rng, -8, 8)
    if abs(x) == 1:
        return None
    return num_q(f"y={d(a)}xで、x={d(x)}のときのyの値を求めなさい。", a * x,
                 f"y={d(a)}×{'(' + d(x) + ')' if x < 0 else d(x)}={d(a * x)}。")


def f003_value2(rng):
    a = nz(rng, -5, 5)
    if abs(a) == 1:
        return None
    x1, x2 = nz(rng, -4, 4), nz(rng, -8, 8)
    if x1 == x2 or abs(x1) == 1 or abs(x2) == 1:
        return None
    return num_q(f"yはxに比例し、x={d(x1)}のときy={d(a * x1)}である。x={d(x2)}のときのyの値を求めなさい。",
                 a * x2, f"比例定数は{d(a)}なので y={d(a)}x。x={d(x2)}を代入して{d(a * x2)}。")


def f004_const(rng):
    x, y = nz(rng, -8, 8), nz(rng, -9, 9)
    if abs(x) == 1 or abs(y) == 1:
        return None
    return num_q(f"yはxに反比例し、x={d(x)}のときy={d(y)}である。比例定数を求めなさい。", x * y,
                 f"a=xy={d(x * y)}。")


def f004_value(rng):
    a = rng.choice([12, 18, 24, 30, 36, -12, -24, 48, 60, -36])
    x = rng.choice([v for v in range(-12, 13) if v and a % v == 0 and abs(v) not in (1, abs(a))])
    return num_q(f"y={d(a)}/xで、x={d(x)}のときのyの値を求めなさい。", F(a, x),
                 f"y={d(a)}÷{'(' + d(x) + ')' if x < 0 else d(x)}={d(F(a, x))}。")


def f004_value2(rng):
    x1, y1 = nz(rng, -6, 6), nz(rng, -6, 6)
    a = x1 * y1
    if abs(x1) == 1 or abs(a) < 4:
        return None
    x2 = rng.choice([v for v in range(-12, 13) if v and a % v == 0 and v != x1 and abs(v) != 1])
    return num_q(f"yはxに反比例し、x={d(x1)}のときy={d(y1)}である。x={d(x2)}のときのyの値を求めなさい。",
                 F(a, x2), f"a=xy={d(a)}より y={d(a)}/x。x={d(x2)}で y={d(F(a, x2))}。")


def f006_value(rng):
    a = rng.choice([2, 3, -2, -3, 4, -4, 5, F(1, 2), F(-1, 2), F(3, 2)])
    b = nz(rng, -9, 9)
    x = nz(rng, -5, 6) * F(a).denominator
    y = F(a) * x + b
    return num_q(f"{lin(a, b)}で、x={d(x)}のときのyの値を求めなさい。", y,
                 f"x={d(x)}を代入して y={d(y)}。")


def f006_inverse(rng):
    a, b = nz(rng, -5, 5), nz(rng, -9, 9)
    if abs(a) == 1:
        return None
    x = nz(rng, -6, 6)
    y = a * x + b
    return num_q(f"{lin(a, b)}で、y={d(y)}となるxの値を求めなさい。", x,
                 f"{d(y)}={poly([(a, 'x'), (b, '')])} を解いて x={d(x)}。")


def _lin_cands(a, b, extra=()):
    c = list(extra)
    c += [lin(b, a) if b != 0 else None, lin(a, -b), lin(-a, b), lin(-a, -b), lin(a, b + 2), lin(a, b - 2)]
    return c


def f006_form1(rng):
    a, b = nz(rng, -5, 5), nz(rng, -8, 8)
    if a == b:
        return None
    return mc_q(f"傾きが{d(a)}、切片が{d(b)}の一次関数の式を求めなさい。", lin(a, b), _lin_cands(a, b),
                f"y=ax+bに a={d(a)}, b={d(b)} を入れる。", rng)


def f006_form2(rng):
    a, b = nz(rng, -4, 4), nz(rng, -8, 8)
    p = nz(rng, -4, 4)
    q = a * p + b
    wrong_b = q + a * p  # b=q+ap と符号を誤る
    if wrong_b == b:
        return None
    return mc_q(f"傾きが{d(a)}で、点{pt(p, q)}を通る直線の式を求めなさい。", lin(a, b),
                _lin_cands(a, b, [lin(a, wrong_b)]),
                f"y={poly([(a, 'x')])}+bに({d(p)}, {d(q)})を代入して b={d(b)}。", rng)


def f006_form3(rng):
    a, b = nz(rng, -4, 4), nz(rng, -7, 7)
    x1, x2 = sorted(rng.sample([v for v in range(-4, 6)], 2))
    y1, y2 = a * x1 + b, a * x2 + b
    inv = F(x2 - x1, y2 - y1)
    extra = [lin(inv, y1 - inv * x1), lin(-a, y1 + a * x1)]
    return mc_q(f"2点{pt(x1, y1)}、{pt(x2, y2)}を通る直線の式を求めなさい。", lin(a, b),
                _lin_cands(a, b, extra),
                f"傾きは{pn(y2 - y1)}÷{d(x2 - x1)}={d(a)}、切片は{d(b)}。",
                rng)


def f007_read(rng):
    a = rng.choice([2, 3, 4, 5, -2, -3, -4, -5, F(1, 2), F(-2, 3), F(3, 4)])
    b = nz(rng, -9, 9)
    return num_q(f"一次関数 {lin(a, b)} の変化の割合を求めなさい。", a,
                 f"一次関数 y=ax+b の変化の割合は傾き a に等しく {d(a)}。")


def f007_incr(rng):
    a, b = nz(rng, -5, 5), nz(rng, -9, 9)
    if abs(a) == 1:
        return None
    dx = rng.randint(2, 6)
    return num_q(f"一次関数 {lin(a, b)} で、xの増加量が{dx}のときのyの増加量を求めなさい。", a * dx,
                 f"yの増加量＝変化の割合×xの増加量＝{d(a)}×{dx}={d(a * dx)}。")


def f007_two(rng):
    x1 = rng.randint(-3, 3)
    dx = rng.randint(2, 5)
    x2 = x1 + dx
    a = rng.choice([2, 3, 4, -2, -3, -4, F(1, 2), F(-3, 2), F(2, 3)])
    if (F(a) * dx).denominator != 1:
        return None
    y1 = rng.randint(-6, 8)
    y2 = y1 + F(a) * dx
    if y2 > y1:
        tail = f"yは{d(y1)}から{d(y2)}まで増加する"
    else:
        tail = f"yは{d(y1)}から{d(y2)}まで減少する"
    return num_q(f"ある一次関数で、xが{d(x1)}から{d(x2)}まで増加するとき、{tail}。変化の割合を求めなさい。", a,
                 f"(yの増加量)÷(xの増加量)={pn(y2 - y1)}÷{dx}={d(a)}。")


def f007_points(rng):
    x1, x2 = sorted(rng.sample(range(-4, 6), 2))
    y1, y2 = rng.randint(-8, 8), rng.randint(-8, 8)
    if y1 == y2:
        return None
    a = F(y2 - y1, x2 - x1)
    return num_q(f"2点{pt(x1, y1)}、{pt(x2, y2)}を通る直線の変化の割合を求めなさい。", a,
                 f"変化の割合={pn(y2 - y1)}÷{d(x2 - x1)}={d(a)}。")


def f008_value(rng):
    a = rng.choice([2, 3, -1, -2, -3, 4, F(1, 2), F(-1, 2), F(1, 3), F(1, 4), F(-1, 4)])
    x = nz(rng, -6, 6)
    if abs(x) == 1:
        return None
    y = F(a) * x * x
    if y.denominator != 1 and rng.random() < 0.7:
        return None
    ax = "x²" if a == 1 else ("−x²" if a == -1 else term(a, "x²", True))
    return num_q(f"y={ax}で、x={d(x)}のときのyの値を求めなさい。", y,
                 f"y={pn(a)}×{pn(x)}²={pn(a)}×{x * x}={d(y)}。")


def f008_const(rng):
    a = rng.choice([2, 3, -2, -3, 4, 5, -1, F(1, 2), F(-1, 2), F(1, 3), F(3, 4)])
    x = nz(rng, -5, 5)
    if abs(x) == 1:
        return None
    y = F(a) * x * x
    if y.denominator != 1:
        return None
    if rng.random() < 0.5:
        p = f"yはxの2乗に比例し、x={d(x)}のときy={d(y)}である。比例定数を求めなさい。"
    else:
        p = f"y=ax²のグラフが点{pt(x, y)}を通る。aの値を求めなさい。"
    q = num_q(p, a, f"{d(y)}=a×{pn(x)}² より a={d(y)}÷{x * x}={d(a)}。")
    q["_key"] = ("f008", x, y)
    return q


def _vertex_cands(p, q):
    return [pt(-p, q), pt(p, -q), pt(-p, -q), pt(q, p)]


def f010_vertex(rng):
    a = rng.choice([1, 2, -1, -2, 3, F(1, 2), -3])
    p, q = nz(rng, -5, 5), nz(rng, -7, 7)
    return mc_q(f"放物線 y={vform(a, p, q)} の頂点の座標を求めなさい。", pt(p, q), _vertex_cands(p, q),
                f"y=a(x−p)²+q の頂点は(p, q)なので{pt(p, q)}。", rng)


def f010_complete(rng):
    a = rng.choice([1, 1, 1, 2, -1, -2])
    p, q = nz(rng, -4, 4), nz(rng, -6, 6)
    b, c = -2 * a * p, a * p * p + q
    cands = [vform(a, -p, q), vform(a, p, c), vform(a, p, c + a * p * p)]
    if a != 1:
        cands.append(vform(a, p, c - p * p))
    cands.append(vform(a, -p, -q))
    return mc_q(f"y={quad(a, b, c)} を平方完成しなさい。", "y=" + vform(a, p, q),
                ["y=" + s for s in cands],
                f"y={vform(a, p, 0)}{term(-a * p * p, '', False)}{term(c, '', False)}={vform(a, p, q)}。",
                rng) if b else None


def f010_general(rng):
    a = rng.choice([1, 1, 2, -1, -2, 3])
    p, q = nz(rng, -4, 4), nz(rng, -8, 8)
    b, c = -2 * a * p, a * p * p + q
    if c == q:
        return None
    return mc_q(f"放物線 y={quad(a, b, c)} の頂点の座標を求めなさい。", pt(p, q),
                [pt(-p, q), pt(p, c), pt(-p, -q), pt(p, -q)],
                f"平方完成すると y={vform(a, p, q)} なので頂点は{pt(p, q)}。", rng)


def f011_free(rng):
    a = rng.choice([1, 1, 2, -1, -1, -2, 3])
    p, q = nz(rng, -4, 4), rng.randint(-9, 9)
    kind = "最小値" if a > 0 else "最大値"
    if rng.random() < 0.35:
        expr = vform(a, p, q)
    else:
        expr = quad(a, -2 * a * p, a * p * p + q)
    return num_q(f"y={expr} の{kind}を求めなさい。", q,
                 f"y={vform(a, p, q)} より x={d(p)} のとき{kind} {d(q)}。")


def _dom(rng):
    a = rng.choice([1, 1, -1, -1, 2])
    p = rng.randint(-3, 4)
    l = rng.randint(p - 3, p + 1)
    r = l + rng.randint(2, 5)
    f = lambda x: a * (x - p) ** 2
    c = rng.randint(-5, 5)
    fx = lambda x: f(x) + c
    b, cc = -2 * a * p, a * p * p + c
    if b == 0:
        return None
    pts = [l, r] + ([p] if l <= p <= r else [])
    return a, p, l, r, fx, quad(a, b, cc), pts


def f011_domain(rng):
    g = _dom(rng)
    if not g:
        return None
    a, p, l, r, fx, expr, pts = g
    kind = rng.choice(["最大値", "最小値"])
    vals = [fx(t) for t in pts]
    best = max(vals) if kind == "最大値" else min(vals)
    at = [t for t in pts if fx(t) == best]
    if len(set(at)) != 1:
        return None
    t = at[0]
    how = "頂点" if t == p else "端点"
    return num_q(f"y={expr}（{d(l)}≦x≦{d(r)}）の{kind}を求めなさい。", best,
                 f"y={vform(a, p, fx(p))}。{how} x={d(t)} で{kind} {d(best)}。")


def f011_with_x(rng):
    g = _dom(rng)
    if not g:
        return None
    a, p, l, r, fx, expr, pts = g
    kind = rng.choice(["最大値", "最小値"])
    vals = [fx(t) for t in pts]
    best = max(vals) if kind == "最大値" else min(vals)
    at = [t for t in pts if fx(t) == best]
    if len(set(at)) != 1:
        return None
    t = at[0]
    S = lambda x, v: f"x={d(x)} のとき{kind} {d(v)}"
    cands = [S(u, fx(u)) for u in [l, r, p, -p] if u != t]
    cands += [S(t, fx(p)), S(p, fx(t)), S(t, best + 1)]
    return mc_q(f"y={expr}（{d(l)}≦x≦{d(r)}）の{kind}と、そのときのxの値を求めなさい。", S(t, best),
                cands, f"y={vform(a, p, fx(p))}。グラフから x={d(t)} で{kind} {d(best)}。", rng)


def _roots_str(rs):
    return "x=" + ", ".join(d(r) for r in sorted(set(rs)))


def _fact(rng, allow2=True):
    """(αx−β)(γx−δ) の係数と2解を返す。"""
    al = rng.choice([1, 1, 1, 2]) if allow2 else 1
    be = rng.randint(-5, 5)
    ga, de = 1, rng.randint(-5, 5)
    r1, r2 = F(be, al), F(de, ga)
    if r1 == r2 or be == 0 and de == 0:
        return None
    A, B, C = al * ga, -(al * de + be * ga), be * de
    if math.gcd(math.gcd(A, abs(B)), abs(C)) != 1:
        return None
    return A, B, C, min(r1, r2), max(r1, r2)


def f012_cross(rng):
    g = _fact(rng)
    if not g or g[2] == 0 and rng.random() < 0.6:
        return None
    A, B, C, r1, r2 = g
    cands = [_roots_str([-r1, -r2]), _roots_str([r1, -r2]), _roots_str([-r1, r2]),
             _roots_str([r1 * 2, r2]) if r1 * 2 != r2 else None]
    return mc_q(f"放物線 y={quad(A, B, C)} とx軸の共有点のx座標を求めなさい。", _roots_str([r1, r2]),
                cands, f"{quad(A, B, C)}=0 を因数分解して解くと {_roots_str([r1, r2])}。", rng)


def f012_touch(rng):
    al = rng.choice([1, 1, 1, 2, 3])
    be = nz(rng, -5, 5)
    if math.gcd(al, be) != 1:
        return None
    A, B, C = al * al, -2 * al * be, be * be
    r = F(be, al)
    return num_q(f"放物線 y={quad(A, B, C)} はx軸と接する。接点のx座標を求めなさい。", r,
                 f"{quad(A, B, C)}=({'x' if al == 1 else str(al) + 'x'}{term(-be, '', False)})² なので x={d(r)}。")


def f012_count(rng):
    A = rng.choice([1, 1, 2, -1])
    B = rng.randint(-6, 6)
    C = rng.randint(-6, 6)
    if C == 0 or B == 0:
        return None
    D = B * B - 4 * A * C
    n = 2 if D > 0 else (1 if D == 0 else 0)
    return num_q(f"放物線 y={quad(A, B, C)} とx軸の共有点の個数を求めなさい。", n,
                 f"判別式 D={d(B)}²−4×{'(' + d(A) + ')' if A < 0 else d(A)}×{'(' + d(C) + ')' if C < 0 else d(C)}={d(D)} {'>' if D > 0 else ('=' if D == 0 else '<')} 0 より{n}個。")


def _ineq_ans(r1, r2, op):
    inside = op in ("<", "≦")
    le = "≦" if op in ("≦", "≧") else "<"
    if inside:
        return f"{d(r1)}{le}x{le}{d(r2)}"
    return f"x{le}{d(r1)}, {d(r2)}{le}x"


def f012_ineq(rng):
    g = _fact(rng)
    if not g:
        return None
    A, B, C, r1, r2 = g
    op = rng.choice(["<", ">", "≦", "≧"])
    flip = {"<": ">", ">": "<", "≦": "≧", "≧": "≦"}
    strict = {"<": "≦", "≦": "<", ">": "≧", "≧": ">"}
    neg = rng.random() < 0.25
    shown_A, shown_B, shown_C, shown_op = (-A, -B, -C, flip[op]) if neg else (A, B, C, op)
    cands = [_ineq_ans(r1, r2, flip[op]) if neg else None,
             _ineq_ans(r1, r2, {"<": "≧", ">": "≦", "≦": ">", "≧": "<"}[op]),
             _ineq_ans(r1, r2, strict[op]),
             _ineq_ans(-r2, -r1, op),
             _ineq_ans(r1, r2, flip[op])]
    how = f"両辺に−1を掛けて {quad(A, B, C)}{op}0。" if neg else ""
    return mc_q(f"2次不等式 {quad(shown_A, shown_B, shown_C)}{shown_op}0 を解きなさい。", _ineq_ans(r1, r2, op),
                cands, how + f"{quad(A, B, C)}=0 の解は x={d(r1)}, {d(r2)} なので {_ineq_ans(r1, r2, op)}。", rng)


def f012_special(rng):
    p = nz(rng, -4, 4)
    kind = rng.randint(0, 3)
    if kind < 2:
        k = rng.randint(1, 4)
        A, B, C = 1, -2 * p, p * p + k  # (x−p)²+k > 0
        op = ">" if kind == 0 else "<"
        ans = "すべての実数" if kind == 0 else "解なし"
        cands = ["解なし" if kind == 0 else "すべての実数", f"x={d(p)}", f"{d(p)}以外のすべての実数", f"x>{d(p)}"]
        exp = f"{quad(A, B, C)}=(x{term(-p, '', False)})²+{k}>0 は常に成り立つので{ans}。"
    else:
        A, B, C = 1, -2 * p, p * p
        op = ">" if kind == 2 else "≦"
        ans = f"{d(p)}以外のすべての実数" if kind == 2 else f"x={d(p)}"
        cands = ["すべての実数", "解なし", f"x={d(p)}" if kind == 2 else f"{d(p)}以外のすべての実数", f"x={d(-p)}"]
        exp = f"(x{term(-p, '', False)})²{op}0 なので{ans}。"
    return mc_q(f"2次不等式 {quad(A, B, C)}{op}0 を解きなさい。", ans, cands, exp, rng)


# ================================================================ 三角比
BASE = {0: Q.R(0), 30: Q.R(F(1, 2)), 45: Q.S(2, F(1, 2)), 60: Q.S(3, F(1, 2)), 90: Q.R(1)}
SQ2_2 = Q.S(2, F(1, 2))


def sin_deg(x):
    x %= 360
    if x % 30 and x % 45:
        return sin_deg(x - 45) * SQ2_2 + cos_deg(x - 45) * SQ2_2
    if x <= 90:
        return BASE[x]
    if x <= 180:
        return BASE[180 - x]
    if x <= 270:
        return -BASE[x - 180]
    return -BASE[360 - x]


def cos_deg(x):
    return sin_deg(x + 90)


def tan_deg(x):
    x %= 180
    if x % 30 and x % 45:
        t = tan_deg(x - 45)  # tan(y+45°)=(tany+1)/(1−tany)
        return (t + 1) / (1 - t)
    return sin_deg(x) / cos_deg(x)


# 自己検算
for _x in range(0, 360, 15):
    if _x % 180 != 90:
        assert abs(float(tan_deg(_x)) - math.tan(math.radians(_x))) < 1e-9
    assert abs(float(sin_deg(_x)) - math.sin(math.radians(_x))) < 1e-12
    assert abs(float(cos_deg(_x)) - math.cos(math.radians(_x))) < 1e-12

NICE = [30, 45, 60, 90, 120, 135, 150]


def pos(q):
    return float(q) > 1e-12


def f_t004_side(rng):
    A, B = rng.sample(NICE, 2)
    if A + B >= 180:
        return None
    C = 180 - A - B
    ask_c = C in NICE and rng.random() < 0.3
    k = rng.randint(2, 8)
    a = Q.R(k * rng.choice([1, 2]))
    if rng.random() < 0.3:
        a = Q.S(rng.choice([2, 3]), k)
    T = C if ask_c else B
    tgt = "c" if ask_c else "b"
    ans = a * sin_deg(T) / sin_deg(A)
    cands = [a * sin_deg(A) / sin_deg(T), a * sin_deg(T), a / sin_deg(T), a * sin_deg(T) * sin_deg(A),
             ans * 2, ans / 2]
    cands = [fmt(c) for c in cands if pos(c)]
    extra = "" if not ask_c else f"C={C}°なので、"
    exp = f"{extra}{d(a)}/sin{A}°={tgt}/sin{T}° より {tgt}={d(ans)}。"
    p = f"△ABCにおいて、A={A}°、B={B}°、a={d(a)}のとき、{tgt}を求めなさい。"
    if ans.is_rational():
        return num_q(p, ans, exp)
    return mc_q(p, fmt(ans), cands, exp, rng)


def f_t004_radius(rng):
    A = rng.choice(NICE)
    k = rng.randint(2, 9)
    a = Q.R(k) if rng.random() < 0.7 else Q.S(rng.choice([2, 3]), k)
    mode = rng.randint(0, 2)
    if mode == 2:
        R = Q.R(k)
        a = 2 * R * sin_deg(A)
        p = f"△ABCにおいて、外接円の半径が{k}、A={A}°のとき、aを求めなさい。"
        ans = a
        cands = [R * sin_deg(A), R / sin_deg(A), 2 * R / sin_deg(A), 2 * R * cos_deg(A)]
        exp = f"a=2R sinA=2×{k}×sin{A}°={d(ans)}。"
    else:
        two = mode == 1
        ans = a / sin_deg(A) / (1 if two else 2)
        tgt = "外接円の直径2R" if two else "外接円の半径R"
        p = f"△ABCにおいて、A={A}°、a={d(a)}のとき、{tgt}を求めなさい。"
        cands = [ans * 2, ans / 2, a * sin_deg(A), a * sin_deg(A) / 2]
        if A != 90:
            cands.append(a / cos_deg(A) / (1 if two else 2))
        exp = f"2R=a/sinA={d(a)}/sin{A}°={d(a / sin_deg(A))}" + ("。" if two else f"、R={d(ans)}。")
    cands = [fmt(c) for c in cands if pos(c)]
    if ans.is_rational():
        return num_q(p, ans, exp)
    return mc_q(p, fmt(ans), cands, exp, rng)


def _cos_triples():
    out = []
    for A in (60, 120):
        for b in range(2, 17):
            for c in range(2, 17):
                if b == c:
                    continue
                a2 = b * b + c * c - 2 * b * c * cos_deg(A).rat()
                r = math.isqrt(int(a2))
                if r * r == a2:
                    out.append((A, b, c, r))
    return out


COS_TRIPLES = _cos_triples()


def f_t005_side_int(rng):
    A, b, c, a = rng.choice(COS_TRIPLES)
    return num_q(f"△ABCにおいて、b={b}、c={c}、A={A}°のとき、aを求めなさい。", a,
                 f"a²={b}²+{c}²−2×{b}×{c}×cos{A}°={a * a} より a={a}。")


def f_t005_side_surd(rng):
    A = rng.choice([60, 120, 45, 135, 30, 150])
    k = rng.randint(1, 5)
    if A in (45, 135):
        b = Q.S(2, k)
    elif A in (30, 150):
        b = Q.S(3, k)
    else:
        b = Q.R(rng.randint(2, 9))
    c = Q.R(rng.randint(2, 9))
    if b == c:
        return None
    a2 = (b.square() + c.square() - 2 * b * c * cos_deg(A)).rat()
    if a2 <= 0:
        return None
    ans = Q.sqrt(a2)
    if ans.is_rational():
        return None
    alt = [(b.square() + c.square() + 2 * b * c * cos_deg(A)).rat(),
           (b.square() + c.square() - b * c * cos_deg(A)).rat()]
    alt = [x for x in alt if x > 0 and x.denominator == 1]
    cands = [fmt(Q.sqrt(x)) for x in alt] + [fmt(Q.R(a2)), fmt(Q.sqrt(b.square().rat() + c.square().rat())),
                                             fmt(Q.sqrt(a2 + 2)), fmt(Q.sqrt(a2 - 2))]
    return mc_q(f"△ABCにおいて、b={d(b)}、c={d(c)}、A={A}°のとき、aを求めなさい。", fmt(ans), cands,
                f"a²=b²+c²−2bc cos{A}°={d(a2)} より a={fmt(ans)}。", rng)


def f_t005_cos(rng):
    s = [rng.randint(2, 10) for _ in range(3)]
    a, b, c = s
    if len(set(s)) == 1 or a + b <= c or b + c <= a or c + a <= b:
        return None
    which = rng.randint(0, 2)
    names = "ABC"
    x = s[which]
    y, z = s[(which + 1) % 3], s[(which + 2) % 3]
    cosv = F(y * y + z * z - x * x, 2 * y * z)
    ln = "abc"
    return num_q(f"△ABCにおいて、a={a}、b={b}、c={c}のとき、cos{names[which]}の値を求めなさい。", cosv,
                 f"cos{names[which]}=({ln[(which + 1) % 3]}²+{ln[(which + 2) % 3]}²−{ln[which]}²)/(2{ln[(which + 1) % 3]}{ln[(which + 2) % 3]})={pn(y * y + z * z - x * x)}/{2 * y * z}={d(cosv)}。")


def f_t005_angle(rng):
    A, b, c, a = rng.choice(COS_TRIPLES)
    if a == b or a == c:
        return None
    cv = cos_deg(A).rat()
    return num_q(f"△ABCにおいて、a={a}、b={b}、c={c}のとき、Aは何度か求めなさい。", A,
                 f"cosA=(b²+c²−a²)/(2bc)={d(cv)} より A={A}°。")


def _meas(dist, th):
    return {"sin": dist * sin_deg(th), "cos": dist * cos_deg(th), "tan": dist * tan_deg(th),
            "cot": dist / tan_deg(th)}


def _meas_q(rng, prompt, dist, th, key, exp):
    m = _meas(Q.R(dist), th)
    ans = m[key]
    cands = [fmt(v) for k, v in m.items() if k != key] + [fmt(ans * 2), fmt(ans / 2)]
    if ans.is_rational():
        return num_q(prompt, ans, exp.format(ans=d(ans)))
    return mc_q(prompt, fmt(ans), cands, exp.format(ans=fmt(ans)), rng)


def f_t006_look(rng):
    dd = rng.choice([6, 10, 12, 15, 20, 24, 30, 40, 50])
    th = rng.choice([30, 45, 60])
    return _meas_q(rng, f"建物から水平に{dd}m離れた地点で、建物の頂上を見上げた角が{th}°であった。建物の高さは何mか求めなさい（目の高さは考えない）。",
                   dd, th, "tan", f"高さ={dd}×tan{th}°={{ans}}(m)。")


def f_t006_slope(rng):
    L = rng.choice([10, 20, 40, 60, 100, 200])
    th = rng.choice([30, 45, 60])
    if rng.random() < 0.5:
        return _meas_q(rng, f"傾斜が{th}°の坂道を{L}m登った。何m高くなったか求めなさい。", L, th, "sin",
                       f"高さ={L}×sin{th}°={{ans}}(m)。")
    return _meas_q(rng, f"傾斜が{th}°の坂道を{L}m登った。水平方向に何m進んだか求めなさい。", L, th, "cos",
                   f"水平距離={L}×cos{th}°={{ans}}(m)。")


def f_t006_ladder(rng):
    L = rng.choice([4, 6, 8, 10, 12])
    th = rng.choice([45, 60])
    if rng.random() < 0.5:
        return _meas_q(rng, f"長さ{L}mのはしごを、地面と{th}°の角をなすように壁に立てかけた。はしごの上端の高さは何mか求めなさい。",
                       L, th, "sin", f"高さ={L}×sin{th}°={{ans}}(m)。")
    return _meas_q(rng, f"長さ{L}mのはしごを、地面と{th}°の角をなすように壁に立てかけた。はしごの下端と壁の距離は何mか求めなさい。",
                   L, th, "cos", f"距離={L}×cos{th}°={{ans}}(m)。")


def f_t006_down(rng):
    h = rng.choice([30, 40, 50, 60, 80, 100])
    th = rng.choice([30, 60])
    return _meas_q(rng, f"高さ{h}mのがけの上から海上の船を見下ろした角（俯角）が{th}°であった。がけの下から船までの距離は何mか求めなさい。",
                   h, th, "cot", f"距離={h}÷tan{th}°={{ans}}(m)。")


def f_t006_two(rng):
    dd = rng.choice([10, 20, 30, 40, 60])
    ans = Q.S(3, F(dd, 2))
    cands = [fmt(Q.S(3, dd)), fmt(Q.R(F(dd, 2))), fmt(Q.S(3, F(dd, 3))), fmt(Q.R(dd))]
    return mc_q(f"塔に向かって一直線上の2地点A、B（AB={dd}m、Bが塔に近い）から塔の頂上を見上げた角は、Aで30°、Bで60°であった。塔の高さは何mか求めなさい。",
                fmt(ans), cands, f"頂上をPとすると∠APB=60°−30°=30°より BP=AB={dd}m。高さ={dd}×sin60°={fmt(ans)}(m)。", rng)


def _area_cands(x, y, th, ans):
    x, y = Q.R(x) if not isinstance(x, Q) else x, Q.R(y) if not isinstance(y, Q) else y
    c = [x * y * sin_deg(th), x * y / 2]
    if cos_deg(th) != Q.R(0):
        c.append(x * y * cos_deg(th) / 2)
        c.append(-x * y * cos_deg(th) / 2)
    c += [ans * 2, ans / 2]
    return [fmt(v) for v in c if pos(v)]


def f_t007_sas(rng):
    th = rng.choice([30, 45, 60, 120, 135, 150])
    x, y = rng.randint(2, 10), rng.randint(2, 10)
    ang = rng.choice(["abC", "bcA", "caB"])
    s1, s2, A = ang[0], ang[1], ang[2]
    ans = Q.R(x * y) * sin_deg(th) / 2
    p = f"△ABCにおいて、{s1}={x}、{s2}={y}、{A}={th}°のとき、面積を求めなさい。"
    exp = f"S=(1/2)×{x}×{y}×sin{th}°={d(ans)}。"
    if ans.is_rational():
        return num_q(p, ans, exp)
    return mc_q(p, fmt(ans), _area_cands(x, y, th, ans), exp, rng)


def f_t007_para(rng):
    th = rng.choice([30, 45, 60, 120, 135, 150])
    x, y = rng.randint(3, 10), rng.randint(3, 10)
    ans = Q.R(x * y) * sin_deg(th)
    p = f"AB={x}、AD={y}、∠A={th}°の平行四辺形ABCDの面積を求めなさい。"
    exp = f"S=AB×AD×sinA={x}×{y}×sin{th}°={d(ans)}。"
    if ans.is_rational():
        return num_q(p, ans, exp)
    c = [ans / 2, Q.R(x * y), Q.R(x * y) * cos_deg(th), -Q.R(x * y) * cos_deg(th), ans * 2]
    return mc_q(p, fmt(ans), [fmt(v) for v in c if pos(v)], exp, rng)


def f_t007_sss(rng):
    A, b, c, a = rng.choice(COS_TRIPLES)
    sides = sorted({a, b, c})
    if len(sides) < 3:
        return None
    ans = Q.R(b * c) * sin_deg(A) / 2
    return mc_q(f"3辺の長さが{sides[0]}、{sides[1]}、{sides[2]}の三角形の面積を求めなさい。", fmt(ans),
                _area_cands(b, c, A, ans),
                f"長さ{a}の辺の対角をθとすると cosθ={d(cos_deg(A))} より θ={A}°。S=(1/2)×{b}×{c}×sin{A}°={fmt(ans)}。", rng)


def f_t007_angle(rng):
    th = rng.choice([30, 45, 60])
    b, c = rng.randint(2, 9), rng.randint(2, 9)
    S = Q.R(b * c) * sin_deg(th) / 2
    return num_q(f"△ABCにおいて、b={b}、c={c}、面積が{d(S)}で、Aが鋭角のとき、Aは何度か求めなさい。", th,
                 f"(1/2)×{b}×{c}×sinA={d(S)} より sinA={d(sin_deg(th))}、Aは鋭角なので{th}°。")


SPLIT = {15: (45, 30, "−"), 75: (45, 30, "+"), 105: (60, 45, "+"), 165: (120, 45, "+")}


def _add_q(rng, fn, x):
    al, be, op = SPLIT[x]
    sg = 1 if op == "+" else -1
    sa, ca, sb, cb = sin_deg(al), cos_deg(al), sin_deg(be), cos_deg(be)
    if fn == "sin":
        ans = sa * cb + sg * ca * sb
        wrong = sa * cb - sg * ca * sb
        other = cos_deg(x)
        form = f"sin{al}°cos{be}°{op}cos{al}°sin{be}°"
    elif fn == "cos":
        ans = ca * cb - sg * sa * sb
        wrong = ca * cb + sg * sa * sb
        other = sin_deg(x)
        form = f"cos{al}°cos{be}°{'−' if op == '+' else '+'}sin{al}°sin{be}°"
    else:
        ta, tb = tan_deg(al), tan_deg(be)
        ans = (ta + sg * tb) / (1 - sg * ta * tb)
        wrong = (ta + sg * tb) / (1 + sg * ta * tb)
        other = 1 / ans
        form = f"(tan{al}°{op}tan{be}°)/(1{'−' if op == '+' else '+'}tan{al}°tan{be}°)"
    assert ans == {"sin": sin_deg, "cos": cos_deg, "tan": tan_deg}[fn](x)
    cands = [wrong, other, -ans, -wrong, ans * 2, -other]
    return mc_q(f"加法定理を用いて、{fn}{x}°の値を求めなさい。", fmt(ans), [fmt(c) for c in cands],
                f"{fn}({al}°{op}{be}°)={form}={fmt(ans)}。", rng)


def f_t012_sin(rng):
    return _add_q(rng, "sin", rng.choice(list(SPLIT)))


def f_t012_cos(rng):
    return _add_q(rng, "cos", rng.choice(list(SPLIT)))


def f_t012_tan(rng):
    return _add_q(rng, "tan", rng.choice([15, 75, 105]))


TRIPLES = [(3, 4, 5), (4, 3, 5), (5, 12, 13), (12, 5, 13), (8, 15, 17), (15, 8, 17), (7, 24, 25)]


def f_t012_ratio(rng):
    (p1, q1, h1), (p2, q2, h2) = rng.sample(TRIPLES, 2)
    sa, ca = F(p1, h1), F(q1, h1)
    sb, cb = F(p2, h2), F(q2, h2)
    give = rng.choice(["sin_cos", "cos_sin", "sin_sin"])
    ga = ("sinα", sa) if give[0] == "s" else ("cosα", ca)
    gb = ("sinβ", sb) if give.split("_")[1] == "sin" else ("cosβ", cb)
    fn, op = rng.choice(["sin", "cos"]), rng.choice(["+", "−"])
    sg = 1 if op == "+" else -1
    if fn == "sin":
        ans = sa * cb + sg * ca * sb
        form = f"sinαcosβ{op}cosαsinβ"
    else:
        ans = ca * cb - sg * sa * sb
        form = f"cosαcosβ{'−' if op == '+' else '+'}sinαsinβ"
    known = {"sinα": sa, "cosα": ca, "sinβ": sb, "cosβ": cb}
    rest = [k for k in known if k not in (ga[0], gb[0])]
    return num_q(f"α、βは鋭角で、{ga[0]}={d(ga[1])}、{gb[0]}={d(gb[1])}のとき、{fn}(α{op}β)の値を求めなさい。", ans,
                 f"{rest[0]}={d(known[rest[0]])}、{rest[1]}={d(known[rest[1]])}。{fn}(α{op}β)={form}={d(ans)}。")


def f_t013_sin2(rng):
    p, q, h = rng.choice(TRIPLES)
    obtuse = rng.random() < 0.35
    s, c = F(p, h), F(q, h) * (-1 if obtuse else 1)
    if rng.random() < 0.5:
        g = f"sinθ={d(s)}"
        other = f"cosθ={d(c)}"
    else:
        g = f"cosθ={d(c)}"
        other = f"sinθ={d(s)}"
    rng_s = "90°<θ<180°" if obtuse else "0°<θ<90°"
    ans = 2 * s * c
    return num_q(f"{rng_s}で、{g}のとき、sin2θの値を求めなさい。", ans,
                 f"{other}。sin2θ=2sinθcosθ={d(ans)}。")


def f_t013_cos2(rng):
    x = rng.choice([F(1, 3), F(2, 3), F(1, 4), F(3, 4), F(1, 5), F(2, 5), F(3, 5), F(1, 2), F(-1, 3), F(-2, 5)])
    if rng.random() < 0.5 and x > 0:
        ans = 1 - 2 * x * x
        return num_q(f"sinθ={d(x)}のとき、cos2θの値を求めなさい。", ans, f"cos2θ=1−2sin²θ=1−2×{d(x * x)}={d(ans)}。")
    ans = 2 * x * x - 1
    return num_q(f"cosθ={d(x)}のとき、cos2θの値を求めなさい。", ans, f"cos2θ=2cos²θ−1=2×{d(x * x)}−1={d(ans)}。")


def f_t013_tan2(rng):
    t = rng.choice([F(2), F(3), F(1, 2), F(1, 3), F(-2), F(-3), F(2, 3), F(3, 4)])
    ans = 2 * t / (1 - t * t)
    return num_q(f"tanθ={d(t)}のとき、tan2θの値を求めなさい。", ans,
                 f"tan2θ=2tanθ/(1−tan²θ)=({d(2 * t)})÷({d(1 - t * t)})={d(ans)}。")


def f_t013_halfsq(rng):
    c = rng.choice([F(1, 3), F(1, 2), F(-1, 3), F(1, 4), F(3, 5), F(-3, 5), F(1, 5), F(-1, 2), F(2, 3), F(5, 7)])
    if rng.random() < 0.5:
        ans = (1 + c) / 2
        return num_q(f"cosθ={d(c)}のとき、cos²(θ/2)の値を求めなさい。", ans, f"cos²(θ/2)=(1+cosθ)/2={d(ans)}。")
    ans = (1 - c) / 2
    return num_q(f"cosθ={d(c)}のとき、sin²(θ/2)の値を求めなさい。", ans, f"sin²(θ/2)=(1−cosθ)/2={d(ans)}。")


def f_t013_half(rng):
    v = rng.choice([F(1, 3), F(2, 3), F(3, 5), F(4, 5), F(1, 4), F(3, 4), F(2, 5)])
    fn = rng.choice(["sin", "cos"])
    upper = rng.random() < 0.5
    cth = 1 - 2 * v * v if fn == "sin" else 2 * v * v - 1
    if abs(cth) >= 1:
        return None
    rng_s = "180°<θ<360°" if upper else "0°<θ<180°"
    sign = -1 if (upper and fn == "cos") else 1
    ans = sign * v
    formula = "(1−cosθ)/2" if fn == "sin" else "(1+cosθ)/2"
    where = "90°<θ/2<180°" if upper else "0°<θ/2<90°"
    return num_q(f"{rng_s}で、cosθ={d(cth)}のとき、{fn}(θ/2)の値を求めなさい。", ans,
                 f"{fn}²(θ/2)={formula}={d(v * v)}。{where} より {fn}(θ/2){'<' if sign < 0 else '>'}0 なので{d(ans)}。")


HALF_SET = {
    "sin22.5°": ("√(2−√2)/2", ["√(2+√2)/2", "(2−√2)/4", "(√6−√2)/4"], "sin²22.5°=(1−cos45°)/2=(2−√2)/4、正なので√(2−√2)/2。"),
    "cos22.5°": ("√(2+√2)/2", ["√(2−√2)/2", "(2+√2)/4", "(√6+√2)/4"], "cos²22.5°=(1+cos45°)/2=(2+√2)/4、正なので√(2+√2)/2。"),
    "tan22.5°": ("√2−1", ["√2+1", "1−√2", "2−√3"], "tan22.5°=sin45°/(1+cos45°)=1/(√2+1)=√2−1。"),
    "cos67.5°": ("√(2−√2)/2", ["√(2+√2)/2", "−√(2−√2)/2", "(√6−√2)/4"], "cos²67.5°=(1+cos135°)/2=(2−√2)/4、正なので√(2−√2)/2。"),
}
_HALF_VAL = {"√(2−√2)/2": math.sqrt(2 - math.sqrt(2)) / 2, "√(2+√2)/2": math.sqrt(2 + math.sqrt(2)) / 2,
             "(2−√2)/4": (2 - math.sqrt(2)) / 4, "(2+√2)/4": (2 + math.sqrt(2)) / 4,
             "(√6−√2)/4": (math.sqrt(6) - math.sqrt(2)) / 4, "(√6+√2)/4": (math.sqrt(6) + math.sqrt(2)) / 4,
             "√2−1": math.sqrt(2) - 1, "√2+1": math.sqrt(2) + 1, "1−√2": 1 - math.sqrt(2), "2−√3": 2 - math.sqrt(3),
             "−√(2−√2)/2": -math.sqrt(2 - math.sqrt(2)) / 2}
for _k, (_c, _w, _) in HALF_SET.items():
    _true = {"sin22.5°": math.sin(math.radians(22.5)), "cos22.5°": math.cos(math.radians(22.5)),
             "tan22.5°": math.tan(math.radians(22.5)), "cos67.5°": math.cos(math.radians(67.5))}[_k]
    assert abs(_HALF_VAL[_c] - _true) < 1e-12
    assert all(abs(_HALF_VAL[w] - _true) > 1e-6 for w in _w)


def f_t013_22(rng):
    k = rng.choice(list(HALF_SET))
    c, w, e = HALF_SET[k]
    return mc_q(f"半角の公式を用いて、{k}の値を求めなさい。", c, w, e, rng)


# ---------------------------------------------------------------- 三角方程式・不等式
FUN = {"sin": sin_deg, "cos": cos_deg, "tan": None}


def rad(k):
    """k·π/12 の表示。"""
    r = F(k, 12)
    if r == 0:
        return "0"
    n, m = r.numerator, r.denominator
    s = ("" if n == 1 else str(n)) + "π"
    return s if m == 1 else s + f"/{m}"


def fval(fn, k):
    x = 15 * k
    if fn == "tan":
        if x % 180 == 90:
            return None
        return tan_deg(x)
    return FUN[fn](x)


def ffloat(fn, t):
    return {"sin": math.sin, "cos": math.cos, "tan": math.tan}[fn](t)


def solve_eq(fn, vals):
    return [k for k in range(24) if fval(fn, k) is not None and fval(fn, k) in vals]


def eq_str(ks):
    return "θ=" + ", ".join(rad(k) for k in ks)


def cmp(a, op, b):
    return {"<": a < b, ">": a > b, "≦": a <= b, "≧": a >= b}[op]


def solve_ineq(fn, op, v):
    """区間の表示文字列を返す。空・全体・1点なら None。"""
    vf = float(v)
    seq = []  # (kind, k, truth)
    for k in range(24):
        fv = fval(fn, k)
        if fv is None:
            tp = False
        elif fv == v:
            tp = op in ("≦", "≧")
        else:
            tp = cmp(float(fv), op, vf)
        seq.append(("P", k, tp))
        mid = (k + 0.5) * math.pi / 12
        seq.append(("I", k, cmp(ffloat(fn, mid), op, vf)))
    runs, cur = [], None
    for kind, k, t in seq:
        if t:
            cur = [(kind, k), (kind, k)] if cur is None else [cur[0], (kind, k)]
        elif cur:
            runs.append(cur)
            cur = None
    if cur:
        runs.append(cur)
    if not runs or (len(runs) == 1 and runs[0] == [("P", 0), ("I", 23)]):
        return None
    parts = []
    for (k1, s), (k2, e) in runs:
        if k1 == "P" and k2 == "P" and s == e:
            return None
        lo = f"{rad(s)}≦θ" if k1 == "P" else f"{rad(s)}<θ"
        hi = f"≦{rad(e)}" if k2 == "P" else f"<{rad(e + 1) if e < 23 else '2π'}"
        parts.append(lo + hi)
    return ", ".join(parts)


def rad_is_sane():
    assert rad(12) == "π" and rad(2) == "π/6" and rad(10) == "5π/6" and rad(18) == "3π/2" and rad(8) == "2π/3"


rad_is_sane()

VALS = {
    "sin": [F(1, 2), F(-1, 2), Q.S(2, F(1, 2)), Q.S(2, F(-1, 2)), Q.S(3, F(1, 2)), Q.S(3, F(-1, 2)), 0],
    "cos": [F(1, 2), F(-1, 2), Q.S(2, F(1, 2)), Q.S(2, F(-1, 2)), Q.S(3, F(1, 2)), Q.S(3, F(-1, 2)), 0],
    "tan": [1, -1, Q.S(3), Q.S(3, -1), Q.S(3, F(1, 3)), Q.S(3, F(-1, 3)), 0],
}
# v → (係数, 右辺)  係数·f(θ)=右辺
LINFORM = {fmt(Q.R(F(1, 2))): ("2", "1"), fmt(Q.R(F(-1, 2))): ("2", "−1"),
           fmt(Q.S(2, F(1, 2))): ("√2", "1"), fmt(Q.S(2, F(-1, 2))): ("√2", "−1"),
           fmt(Q.S(3, F(1, 2))): ("2", "√3"), fmt(Q.S(3, F(-1, 2))): ("2", "−√3"),
           fmt(Q.S(3, F(1, 3))): ("√3", "1"), fmt(Q.S(3, F(-1, 3))): ("√3", "−1")}


def show(fn, v, op, rng):
    v = v if isinstance(v, Q) else Q.R(v)
    key = fmt(v)
    if key in LINFORM and rng.random() < 0.5:
        c, r = LINFORM[key]
        tail = ("+" + r[1:]) if r.startswith("−") else ("−" + r)
        return f"{c}{fn}θ{tail}{op}0"
    return f"{fn}θ{op}{key}"


def _vq(v):
    return v if isinstance(v, Q) else Q.R(v)


def f_t014_eq(rng):
    fn = rng.choice(["sin", "sin", "cos", "cos", "tan"])
    v = _vq(rng.choice(VALS[fn]))
    ks = solve_eq(fn, [v])
    if not ks:
        return None
    other = {"sin": "cos", "cos": "sin", "tan": "sin"}[fn]
    cands = [eq_str(solve_eq(fn, [-v])) if solve_eq(fn, [-v]) else None,
             eq_str(solve_eq(other, [v])) if solve_eq(other, [v]) and fn != "tan" else None,
             eq_str(ks[:1]) if len(ks) > 1 else None,
             eq_str(sorted({(24 - k) % 24 for k in ks})),
             eq_str(sorted({(12 - k) % 24 for k in ks})),
             eq_str(sorted({(k + 12) % 24 for k in ks}))]
    return mc_q(f"0≦θ<2πのとき、方程式 {show(fn, v, '=', rng)} を解きなさい。", eq_str(ks), cands,
                f"{fn}θ={fmt(v)} となるθを単位円で読み取って {eq_str(ks)}。", rng)


def f_t014_quad(rng):
    fn = rng.choice(["sin", "cos"])
    r1 = F(rng.choice([1, -1]), 2)
    r2 = F(rng.choice([1, -1, 0]))
    # (2t − 2r1)(t − r2) = 2t² − (2r2 + 2r1)t + 2r1r2
    B, C = -(2 * r2 + 2 * r1), 2 * r1 * r2
    ks = sorted(set(solve_eq(fn, [Q.R(r1), Q.R(r2)])))
    other = "cos" if fn == "sin" else "sin"
    cands = [eq_str(solve_eq(fn, [Q.R(r1)])), eq_str(solve_eq(fn, [Q.R(-r1), Q.R(-r2)])),
             eq_str(sorted(set(solve_eq(other, [Q.R(r1), Q.R(r2)])))), eq_str(solve_eq(fn, [Q.R(r2)]))]
    expr = poly([(2, f"{fn}²θ"), (B, f"{fn}θ"), (C, "")])
    return mc_q(f"0≦θ<2πのとき、方程式 {expr}=0 を解きなさい。", eq_str(ks), cands,
                f"因数分解して {fn}θ={d(r1)}, {d(r2)}。よって {eq_str(ks)}。", rng)


def f_t014_ineq(rng):
    fn = rng.choice(["sin", "sin", "cos", "cos", "tan"])
    v = _vq(rng.choice([x for x in VALS[fn] if x != 0 or fn != "tan"]))
    op = rng.choice(["<", ">", "≦", "≧"])
    ans = solve_ineq(fn, op, v)
    if not ans:
        return None
    comp = {"<": "≧", ">": "≦", "≦": ">", "≧": "<"}[op]
    strict = {"<": "≦", "≦": "<", ">": "≧", "≧": ">"}[op]
    other = {"sin": "cos", "cos": "sin", "tan": "sin"}[fn]
    cands = [solve_ineq(fn, comp, v), solve_ineq(fn, strict, v), solve_ineq(fn, op, -v)]
    if fn != "tan":
        cands.append(solve_ineq(other, op, v))
    return mc_q(f"0≦θ<2πのとき、不等式 {show(fn, v, op, rng)} を解きなさい。", ans, cands,
                f"単位円（グラフ）で {fn}θ={fmt(v)} となるθを境に読み取ると {ans}。", rng)


GENERATORS = {
    "math-functions-003": lambda rng: run(rng, [(f003_const, 6), (f003_value, 4), (f003_value2, 5)]),
    "math-functions-004": lambda rng: run(rng, [(f004_const, 6), (f004_value, 4), (f004_value2, 5)]),
    "math-functions-006": lambda rng: run(rng, [(f006_value, 4), (f006_inverse, 2), (f006_form1, 3), (f006_form2, 3), (f006_form3, 3)]),
    "math-functions-007": lambda rng: run(rng, [(f007_read, 4), (f007_incr, 3), (f007_two, 4), (f007_points, 4)]),
    "math-functions-008": lambda rng: run(rng, [(f008_value, 7), (f008_const, 8)]),
    "math-functions-010": lambda rng: run(rng, [(f010_vertex, 5), (f010_complete, 5), (f010_general, 5)]),
    "math-functions-011": lambda rng: run(rng, [(f011_free, 5), (f011_domain, 6), (f011_with_x, 4)]),
    "math-functions-012": lambda rng: run(rng, [(f012_cross, 5), (f012_touch, 1), (f012_count, 1), (f012_ineq, 6), (f012_special, 2)]),
    "math-trigonometry-004": lambda rng: run(rng, [(f_t004_side, 8), (f_t004_radius, 7)]),
    "math-trigonometry-005": lambda rng: run(rng, [(f_t005_side_int, 4), (f_t005_side_surd, 4), (f_t005_cos, 5), (f_t005_angle, 2)]),
    "math-trigonometry-006": lambda rng: run(rng, [(f_t006_look, 4), (f_t006_slope, 3), (f_t006_ladder, 3), (f_t006_down, 3), (f_t006_two, 2)]),
    "math-trigonometry-007": lambda rng: run(rng, [(f_t007_sas, 7), (f_t007_para, 2), (f_t007_sss, 3), (f_t007_angle, 3)]),
    "math-trigonometry-012": lambda rng: run(rng, [(f_t012_sin, 4), (f_t012_cos, 4), (f_t012_tan, 2), (f_t012_ratio, 5)]),
    "math-trigonometry-013": lambda rng: run(rng, [(f_t013_sin2, 3), (f_t013_cos2, 3), (f_t013_tan2, 1), (f_t013_halfsq, 3), (f_t013_half, 3), (f_t013_22, 2)]),
    "math-trigonometry-014": lambda rng: run(rng, [(f_t014_eq, 5), (f_t014_quad, 2), (f_t014_ineq, 8)]),
}
