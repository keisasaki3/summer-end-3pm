"""図形と方程式・指数対数・場合の数と確率・数列の計算問題を生成する。

GENERATORS = {topic_id: fn(rng) -> list[dict]}。答えはすべてコードで計算する。
"""
import math
from decimal import Decimal
from fractions import Fraction as F

N_PER_TOPIC = 15

# ---------------------------------------------------------------- 表示ヘルパ
_SUP = str.maketrans("0123456789+-−nx()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻ⁿˣ⁽⁾")
_SUB = str.maketrans("0123456789+-−nk", "₀₁₂₃₄₅₆₇₈₉₊₋₋ₙₖ")


def sup(s):
    return str(s).translate(_SUP)


def sub(s):
    return str(s).translate(_SUB)


def m(s):
    """表示用に ASCII の - を − にする。"""
    return str(s).replace("-", "−")


def fs(x):
    """数（int/Fraction）の表示文字列。"""
    x = F(x)
    s = str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"
    return m(s)


def fa(x):
    """数の ASCII 正規形（答え用）。"""
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def paren(x):
    """負なら括弧でくくる。"""
    return f"({fs(x)})" if x < 0 else fs(x)


def pt(x, y):
    return f"({fs(x)}, {fs(y)})"


def lin(a, b, var="x"):
    """a·var + b の表示（a≠0）。"""
    a, b = F(a), F(b)
    if a == 1:
        s = var
    elif a == -1:
        s = "−" + var
    else:
        s = fs(a) + var
    if b > 0:
        s += "+" + fs(b)
    elif b < 0:
        s += fs(b)
    return s


def logb(b):
    return {F(1, 2): "log½", F(1, 3): "log⅓"}.get(F(b), "log" + sub(b))


def finite_decimal(x):
    x = F(x)
    d = x.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    if d != 1 or x.denominator == 1:
        return None
    s = format((Decimal(x.numerator) / Decimal(x.denominator)).normalize(), "f")
    return s


def num(prompt, val, explain, accept=()):
    q = {"format": "数字入力", "prompt": prompt, "answer": fa(val), "explain": explain}
    acc = []
    dec = finite_decimal(val)
    if dec:
        acc.append(dec)
    for a in accept:
        if a not in acc and a != q["answer"]:
            acc.append(a)
    if acc:
        q["accept"] = acc
    return q


def choice(rng, prompt, correct, wrongs, explain):
    opts = []
    for w in wrongs:
        if w != correct and w not in opts:
            opts.append(w)
    if len(opts) < 3:
        return None
    opts = opts[:3] + [correct]
    rng.shuffle(opts)
    return {"format": "4択", "prompt": prompt, "options": opts,
            "answer": opts.index(correct), "explain": explain}


def collect(rng, schedule):
    """schedule の各テンプレートから1問ずつ、重複のない問題を作る。"""
    out, seen = [], set()
    for tmpl in schedule:
        for _ in range(200):
            q = tmpl(rng)
            if q and q["prompt"] not in seen:
                seen.add(q["prompt"])
                out.append(q)
                break
        else:
            raise RuntimeError(f"{tmpl.__name__}: 問題を作れない")
    return out


def nz(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v:
            return v


def rad(n):
    """√n を簡約した表示。"""
    k, r = 1, n
    i = 2
    while i * i <= r:
        while r % (i * i) == 0:
            r //= i * i
            k *= i
        i += 1
    if r == 1:
        return str(k)
    return (f"{k}√{r}" if k > 1 else f"√{r}")


# ================================================================ 図形と方程式
TRIPLES = [(3, 4, 5), (4, 3, 5), (6, 8, 10), (8, 6, 10), (5, 12, 13), (12, 5, 13),
           (9, 12, 15), (12, 9, 15), (8, 15, 17), (15, 8, 17), (1, 0, 1)]


def ag_dist_int(rng):
    dx, dy, d = rng.choice(TRIPLES[:-1])
    dx *= rng.choice([1, -1])
    dy *= rng.choice([1, -1])
    x1, y1 = rng.randint(-5, 5), rng.randint(-5, 5)
    x2, y2 = x1 + dx, y1 + dy
    return num(f"2点 A{pt(x1, y1)}, B{pt(x2, y2)} 間の距離を求めなさい。", d,
               f"AB=√({abs(dx)}²+{abs(dy)}²)=√{d * d}={d}。")


def ag_dist_origin(rng):
    dx, dy, d = rng.choice(TRIPLES[:-1])
    x, y = dx * rng.choice([1, -1]), dy * rng.choice([1, -1])
    return num(f"原点Oと点A{pt(x, y)} の距離を求めなさい。", d,
               f"OA=√({abs(x)}²+{abs(y)}²)={d}。")


def ag_dist_root(rng):
    dx, dy = rng.randint(1, 6), rng.randint(1, 6)
    s = dx * dx + dy * dy
    if math.isqrt(s) ** 2 == s:
        return None
    dx *= rng.choice([1, -1])
    dy *= rng.choice([1, -1])
    x1, y1 = rng.randint(-4, 4), rng.randint(-4, 4)
    x2, y2 = x1 + dx, y1 + dy
    sx, sy = x1 + x2, y1 + y2
    wrongs = [str(s), rad(abs(dx) + abs(dy)), rad(sx * sx + sy * sy) if sx or sy else "0",
              rad(s + 2), rad(s * 2)]
    return choice(rng, f"2点 A{pt(x1, y1)}, B{pt(x2, y2)} 間の距離を求めなさい。", rad(s), wrongs,
                  f"AB=√({abs(dx)}²+{abs(dy)}²)=√{s}" + (f"={rad(s)}。" if rad(s) != f"√{s}" else "。"))


def _intpt(p):
    return all(F(c).denominator == 1 for c in p)


def _vec(rng):
    while True:
        u, v = rng.randint(-3, 3), rng.randint(-3, 3)
        if u and v:
            return u, v


def ag_internal(rng):
    a, b = rng.choice([(1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2), (3, 4), (1, 4)])
    u, v = _vec(rng)
    A = (rng.randint(-5, 5), rng.randint(-5, 5))
    B = (A[0] + (a + b) * u, A[1] + (a + b) * v)
    P = (A[0] + a * u, A[1] + a * v)
    cands = [
        (A[0] + b * u, A[1] + b * v),  # 比を逆に
        tuple(F(-b * A[i] + a * B[i], a - b) for i in range(2)),  # 外分と混同
        (P[0] + u, P[1] + v),
        (P[0] - u, P[1] - v),
        (P[1], P[0]),
    ]
    wrongs = [pt(*c) for c in cands if _intpt(c) and tuple(c) not in (A, B)]
    return choice(rng, f"2点 A{pt(*A)}, B{pt(*B)} を結ぶ線分ABを {a}:{b} に内分する点の座標を求めなさい。",
                  pt(*P), wrongs,
                  f"({b}×A+{a}×B)/({a}+{b}) を計算して {pt(*P)}。")


def ag_external(rng):
    a, b = rng.choice([(2, 1), (1, 2), (3, 1), (1, 3), (3, 2), (2, 3), (4, 1), (1, 4)])
    u, v = _vec(rng)
    A = (rng.randint(-5, 5), rng.randint(-5, 5))
    B = (A[0] + (a - b) * u, A[1] + (a - b) * v)
    P = (A[0] + a * u, A[1] + a * v)
    cands = [
        tuple(F(b * A[i] + a * B[i], a + b) for i in range(2)),  # 内分と混同
        tuple(F(-a * A[i] + b * B[i], b - a) for i in range(2)),  # 比を逆に
        tuple(F(b * A[i] - a * B[i], a - b) for i in range(2)),  # 符号ミス
        (P[0] + u, P[1] + v),
        (P[0] - u, P[1] - v),
    ]
    wrongs = [pt(*c) for c in cands if _intpt(c) and tuple(c) not in (A, B)]
    return choice(rng, f"2点 A{pt(*A)}, B{pt(*B)} を結ぶ線分ABを {a}:{b} に外分する点の座標を求めなさい。",
                  pt(*P), wrongs,
                  f"(−{b}×A+{a}×B)/({a}−{b}) を計算して {pt(*P)}。")


def ag_midpoint(rng):
    A = (rng.randint(-6, 8), rng.randint(-6, 8))
    B = (A[0] + 2 * nz(rng, -5, 5), A[1] + 2 * nz(rng, -5, 5))
    M = (F(A[0] + B[0], 2), F(A[1] + B[1], 2))
    cands = [(F(B[0] - A[0], 2), F(B[1] - A[1], 2)), (A[0] + B[0], A[1] + B[1]),
             (F(A[0] - B[0], 2), F(A[1] - B[1], 2)), (M[0] + 1, M[1] - 1), (M[1], M[0])]
    return choice(rng, f"2点 A{pt(*A)}, B{pt(*B)} を結ぶ線分ABの中点の座標を求めなさい。",
                  pt(*M), [pt(*c) for c in cands],
                  f"中点は ((x₁+x₂)/2, (y₁+y₂)/2) なので {pt(*M)}。")


def _shift(var, a):
    return var if a == 0 else var + ("−" if a > 0 else "+") + str(abs(a))


def _coef(k):
    return {1: "", -1: "−"}.get(k, fs(k))


def _line(mm, b):
    return "y=" + lin(mm, b, "x") if mm else f"y={fs(b)}"


def ag_line_ps(rng):
    mm = nz(rng, -4, 4)
    x1, y1 = nz(rng, -4, 4), rng.randint(-5, 5)
    b = y1 - mm * x1
    if b == 0:
        return None
    wrongs = [_line(mm, y1 + mm * x1), _line(-mm, b), _line(-mm, y1 + mm * x1), _line(mm, -b)]
    return choice(rng, f"点{pt(x1, y1)} を通り、傾き{fs(mm)} の直線の方程式を求めなさい。",
                  _line(mm, b), wrongs,
                  f"{_shift('y', y1)}={_coef(mm)}({_shift('x', x1)}) を整理して {_line(mm, b)}。")


def ag_line_2p(rng):
    mm = nz(rng, -4, 4)
    x1 = rng.randint(-4, 3)
    x2 = x1 + rng.randint(1, 3)
    b = rng.randint(-6, 6)
    if b == 0 or x1 == 0:
        return None
    y1, y2 = mm * x1 + b, mm * x2 + b
    wrongs = []
    if (x2 - x1) % (y2 - y1) == 0:
        r = F(x2 - x1, y2 - y1)
        wrongs.append(_line(r, y1 - r * x1))
    wrongs += [_line(mm, y1 + mm * x1), _line(-mm, y1 + mm * x1), _line(mm, -b), _line(-mm, b)]
    return choice(rng, f"2点{pt(x1, y1)}, {pt(x2, y2)} を通る直線の方程式を求めなさい。",
                  _line(mm, b), wrongs,
                  f"傾きは ({fs(y2)}−{paren(y1)})/({fs(x2)}−{paren(x1)})={fs(mm)}。点{pt(x1, y1)}を代入して {_line(mm, b)}。")


def _sq(var, a):
    return f"{var}²" if a == 0 else f"({var}{'−' if a > 0 else '+'}{abs(a)})²"


def circ(a, b, r2):
    return f"{_sq('x', a)}+{_sq('y', b)}={r2}"


def _center(rng):
    while True:
        a, b = rng.randint(-5, 5), rng.randint(-5, 5)
        if a and b:
            return a, b


def ag_circle_eq(rng):
    a, b = _center(rng)
    r = rng.randint(2, 7)
    wrongs = [circ(-a, -b, r * r), circ(a, b, r), circ(-a, -b, r), circ(a, -b, r * r)]
    return choice(rng, f"中心{pt(a, b)}、半径{r} の円の方程式を求めなさい。", circ(a, b, r * r), wrongs,
                  f"(x−a)²+(y−b)²=r² に代入して {circ(a, b, r * r)}。")


def ag_circle_through(rng):
    a, b = _center(rng)
    dx, dy = nz(rng, -4, 4), nz(rng, -4, 4)
    px, py = a + dx, b + dy
    r2 = dx * dx + dy * dy
    wrongs = [circ(-a, -b, r2), circ(px, py, r2), circ(a, b, abs(dx) + abs(dy)),
              circ(a, b, (abs(dx) + abs(dy)) ** 2)]
    return choice(rng, f"中心{pt(a, b)} で、点{pt(px, py)} を通る円の方程式を求めなさい。",
                  circ(a, b, r2), wrongs,
                  f"半径²={abs(dx)}²+{abs(dy)}²={r2} なので {circ(a, b, r2)}。")


def _cr(a, b, r):
    return f"中心{pt(a, b)}、半径{r}"


def ag_center_std(rng):
    a, b = _center(rng)
    r = rng.randint(2, 6)
    wrongs = [_cr(-a, -b, r), _cr(a, b, r * r), _cr(-a, -b, r * r)]
    return choice(rng, f"円 {circ(a, b, r * r)} の中心の座標と半径を求めなさい。", _cr(a, b, r), wrongs,
                  f"(x−a)²+(y−b)²=r² と比べて、中心{pt(a, b)}、半径√{r * r}={r}。")


def ag_center_gen(rng):
    a, b = _center(rng)
    r = rng.randint(2, 6)
    c = a * a + b * b - r * r
    if c == 0:
        return None
    eq = "x²+y²" + m(f"{-2 * a:+d}x{-2 * b:+d}y{c:+d}=0")
    wrongs = [_cr(-a, -b, r), _cr(a, b, r * r), _cr(2 * a, 2 * b, r), _cr(-2 * a, -2 * b, r)]
    return choice(rng, f"円 {eq} の中心の座標と半径を求めなさい。", _cr(a, b, r), wrongs,
                  f"平方完成して {circ(a, b, r * r)}。よって {_cr(a, b, r)}。")


PQ = [(3, 4, 5), (4, 3, 5), (3, -4, 5), (4, -3, 5), (5, 12, 13), (12, -5, 13)]


def _lineq(p, q, c):
    s = lin(p, 0, "x") + m(f"{q:+d}y".replace("+1y", "+y").replace("-1y", "-y"))
    if c:
        s += m(f"{c:+d}")
    return s + "=0"


def _circ0(a, b, r):
    return f"x²+y²={r * r}" if a == b == 0 else circ(a, b, r * r)


_REL = {2: "d<r なので異なる2点で交わる", 1: "d=r なので接する", 0: "d>r なので共有点はない"}


def ag_count_pq(rng, want=None):
    p, q, s = rng.choice(PQ)
    a, b = (0, 0) if rng.random() < 0.4 else _center(rng)
    r = rng.randint(2, 6)
    want = rng.choice([0, 1, 2]) if want is None else want
    d = {2: rng.randint(1, r - 1), 1: r, 0: rng.randint(r + 1, r + 3)}[want]
    c = rng.choice([1, -1]) * s * d - p * a - q * b
    got = abs(p * a + q * b + c)
    assert F(got, s) == d
    return num(f"円 {_circ0(a, b, r)} と直線 {_lineq(p, q, c)} の共有点の個数を求めなさい。", want,
               f"中心{pt(a, b)}と直線の距離 d={got}/{s}={d}、半径 r={r}。{_REL[want]}。")


def ag_count0(rng):
    return ag_count_pq(rng, 0)


def ag_count1(rng):
    return ag_count_pq(rng, 1)


def ag_count2(rng):
    return ag_count_pq(rng, 2)


def ag_count_slope(rng):
    mm = rng.choice([1, -1, 2, -2])
    r = rng.randint(2, 5)
    k = nz(rng, -9, 9)
    lhs, rhs = k * k, r * r * (mm * mm + 1)
    if lhs == rhs:
        return None
    want = 2 if lhs < rhs else 0
    return num(f"円 x²+y²={r * r} と直線 y={lin(mm, k)} の共有点の個数を求めなさい。", want,
               f"中心と直線の距離 d=|{fs(k)}|/√{mm * mm + 1} と半径{r}を比べる。{_REL[want]}。")


def ag_tangent_k(rng):
    mm = rng.choice([1, -1, 2, -2, 3, -3])
    r = rng.randint(1, 5)
    t = mm * mm + 1
    rr = "" if r == 1 else str(r)
    correct = f"k=±{rr}√{t}"
    wrongs = [f"k={rr}√{t}", f"k=±{r}", f"k=±{r * t}", f"k=±{r * r}√{t}"]
    return choice(rng, f"直線 y={lin(mm, 0)}+k が円 x²+y²={r * r} に接するとき、定数kの値を求めなさい。",
                  correct, wrongs,
                  f"中心(0, 0)と直線の距離 |k|/√{t} が半径{r}に等しいので |k|={rr}√{t}。")


def ag_pt_line(rng):
    p, q, s = rng.choice(PQ)
    x0, y0 = rng.randint(-4, 4), rng.randint(-4, 4)
    c = nz(rng, -12, 12)
    v = abs(p * x0 + q * y0 + c)
    if v == 0:
        return None
    return num(f"点{pt(x0, y0)} と直線 {_lineq(p, q, c)} の距離を求めなさい。", F(v, s),
               f"d=|{p}×{paren(x0)}+{paren(q)}×{paren(y0)}+{paren(c)}|/√({p}²+{paren(q)}²)={v}/{s}" + ("" if F(v, s).denominator == s else f"={fs(F(v, s))}") + "。")


# ================================================================ 指数・対数
POW_BASES = [2, 3, 5, 6, 10]


def el_sum_num(rng):
    b = rng.choice(POW_BASES)
    k = rng.randint(2, 4 if b <= 3 else 3)
    N = b ** k
    divs = [x for x in range(2, N) if N % x == 0 and x < N // x and x != b]
    if not divs:
        return None
    x = rng.choice(divs)
    y = N // x
    L = logb(b)
    return num(f"{L}{x} + {L}{y} を計算しなさい。", k,
               f"{L}({x}×{y})={L}{N}={k}。")


def el_diff_num(rng):
    b = rng.choice([2, 3, 5])
    y = rng.choice([t for t in [3, 5, 6, 7, 10, 12] if t % b])
    k = rng.randint(1, 3 if b < 5 else 2)
    x = y * b ** k
    L = logb(b)
    return num(f"{L}{x} − {L}{y} を計算しなさい。", k,
               f"{L}({x}/{y})={L}{b ** k}={k}。")


def el_coef_num(rng):
    b = rng.choice([2, 3, 5])
    t = rng.choice([u for u in [2, 3, 5, 7] if u != b])
    j = rng.randint(1, 2)
    x = b ** j * t
    y = t * t
    L = logb(b)
    return num(f"2{L}{x} − {L}{y} を計算しなさい。", 2 * j,
               f"{L}({x}²/{y})={L}{b ** (2 * j)}={2 * j}。")


def el_power(rng):
    b = rng.choice([2, 3, 5])
    j = rng.randint(2, 3)
    e = rng.randint(2, 4)
    L = logb(b)
    return num(f"{L}{b ** j}{sup(e)} を計算しなさい。", j * e,
               f"{L}{b ** j}{sup(e)}={e}×{L}{b ** j}={e}×{j}={j * e}。")


def el_root(rng):
    b = rng.choice([2, 3, 5])
    j = rng.choice([1, 3, 5] if b == 2 else [1, 3])
    L = logb(b)
    return num(f"{L}√{b ** j} を計算しなさい。", F(j, 2),
               f"√{b ** j}={b}^({j}/2) なので {fs(F(j, 2))}。")


def el_recip(rng):
    b = rng.choice([2, 3])
    j = rng.randint(2, 4)
    L = logb(b)
    return num(f"{L}(1/{b ** j}) を計算しなさい。", -j,
               f"1/{b ** j}={b}{sup(-j)} なので {fs(-j)}。")


def el_combine_sum(rng):
    b = rng.choice([2, 3, 5])
    x, y = rng.sample([3, 5, 6, 7, 10, 11], 2)
    L = logb(b)
    return choice(rng, f"{L}{x} + {L}{y} を1つの対数で表しなさい。", f"{L}{x * y}",
                  [f"{L}{x + y}", f"{logb(b * b)}{x * y}", f"{L}{x}×{L}{y}"],
                  f"logₐM+logₐN=logₐMN より {L}{x * y}。")


def el_combine_diff(rng):
    b = rng.choice([2, 3, 5, 7])
    y = rng.choice([2, 3, 4, 5])
    k = rng.choice([t for t in [3, 5, 6, 7, 11] if t != b])
    x = y * k
    L = logb(b)
    return choice(rng, f"{L}{x} − {L}{y} を1つの対数で表しなさい。", f"{L}{k}",
                  [f"{L}{x - y}", f"{L}{x * y}", f"{L}(1/{k})"],
                  f"logₐM−logₐN=logₐ(M/N) より {L}({x}/{y})={L}{k}。")


def el_combine_coef(rng):
    b = rng.choice([2, 3, 5])
    x, y = rng.sample([t for t in [2, 3, 5, 7] if t != b], 2)
    n = rng.choice([2, 3])
    L = logb(b)
    return choice(rng, f"{n}{L}{x} + {L}{y} を1つの対数で表しなさい。", f"{L}{x ** n * y}",
                  [f"{L}{n * x * y}", f"{L}{x ** n + y}", f"{L}{(x * y) ** n}"],
                  f"{n}{L}{x}={L}{x}{sup(n)}={L}{x ** n} なので {L}({x ** n}×{y})={L}{x ** n * y}。")


L2, L3 = Decimal("0.3010"), Decimal("0.4771")
GIVEN = "log₁₀2=0.3010, log₁₀3=0.4771 とする。"
# (表示, 分解, 2の係数, 3の係数, 10の指数)
COMMON = [("6", "2×3", 1, 1, 0), ("12", "2²×3", 2, 1, 0), ("18", "2×3²", 1, 2, 0),
          ("24", "2³×3", 3, 1, 0), ("36", "2²×3²", 2, 2, 0), ("72", "2³×3²", 3, 2, 0),
          ("5", "10/2", -1, 0, 1), ("15", "3×10/2", -1, 1, 1), ("45", "3²×10/2", -1, 2, 1),
          ("0.6", "2×3/10", 1, 1, -1), ("1.5", "3/2", -1, 1, 0), ("2.5", "10/2²", -2, 0, 1),
          ("0.12", "2²×3/10²", 2, 1, -2), ("54", "2×3³", 1, 3, 0), ("0.08", "2³/10²", 3, 0, -2)]


def _dec(x):
    s = format(x.normalize(), "f")
    return s


def el_common_value(rng):
    disp, fac, c2, c3, e = rng.choice(COMMON)
    val = c2 * L2 + c3 * L3 + e
    assert abs(float(val) - math.log10(float(disp))) < 1e-3
    ans = _dec(val)
    acc = [format(val.quantize(Decimal("0.0001")), "f")]
    q = {"format": "数字入力", "prompt": GIVEN + f"log₁₀{disp} の値を求めなさい。", "answer": ans,
         "explain": f"{disp}={fac} なので log₁₀{disp}={m(ans)}。"}
    if acc[0] != ans:
        q["accept"] = acc
    return q


def el_common_pure(rng):
    e = rng.choice([2, 3, 4, 5, -1, -2, -3])
    if e > 0:
        disp = str(10 ** e)
    else:
        disp = format(Decimal(1).scaleb(e), "f")
    if rng.random() < 0.3 and e > 0:
        return num(f"log₁₀√{disp} の値を求めなさい。", F(e, 2),
                   f"√{disp}=10^({e}/2) なので {fs(F(e, 2))}。")
    return num(f"log₁₀{disp} の値を求めなさい。", e, f"{disp}=10{sup(e)} なので {fs(e)}。")


DIG_BASES = [(2, "2", 1, 0, 0), (3, "3", 0, 1, 0), (6, "6", 1, 1, 0), (12, "12", 2, 1, 0),
             (18, "18", 1, 2, 0), (5, "5", -1, 0, 1)]


def el_digits(rng):
    base, disp, c2, c3, e = rng.choice(DIG_BASES)
    n = rng.randint(10, 60)
    lg = n * (c2 * L2 + c3 * L3 + e)
    fl = int(lg)  # 正なので切り捨て
    digits = fl + 1
    if digits != len(str(base ** n)):
        return None
    frac = lg - fl
    if frac < Decimal("0.01") or frac > Decimal("0.99"):
        return None
    return num(GIVEN + f"{disp}{sup(n)} は何桁の整数か求めなさい。", digits,
               f"log₁₀{disp}{sup(n)}={_dec(lg)} より 10{sup(fl)}≦{disp}{sup(n)}<10{sup(fl + 1)} なので {digits}桁。")


def el_first_decimal(rng):
    base, disp = rng.choice([(F(1, 2), "(1/2)"), (F(1, 3), "(1/3)"), (F(2, 3), "(2/3)")])
    lgb = {"(1/2)": -L2, "(1/3)": -L3, "(2/3)": L2 - L3}[disp]
    n = rng.randint(10, 40)
    lg = n * lgb
    k = -math.floor(lg)  # 小数第k位
    v = base ** n
    true_k = 0
    while v * 10 ** true_k < 1:
        true_k += 1
    if k != true_k:
        return None
    frac = lg - math.floor(lg)
    if frac < Decimal("0.01") or frac > Decimal("0.99"):
        return None
    return num(GIVEN + f"{disp}{sup(n)} を小数で表すと、小数第何位に初めて0でない数字が現れるか求めなさい。", k,
               f"log₁₀{disp}{sup(n)}={m(_dec(lg))} より 10{sup(-k)}≦{disp}{sup(n)}<10{sup(-k + 1)} なので小数第{k}位。")


def _pow_disp(t, v):
    """t^v を数として表示（v は負もあり）。"""
    return fs(F(t) ** v)


def el_exp_eq(rng):
    t = rng.choice([2, 3])
    u = rng.choice([1, 2, 3, -1]) if t == 2 else rng.choice([1, 2, -1])
    v = nz(rng, -4, 6 if t == 2 else 4)
    s = rng.choice([0, 0, 1, -1, 2])
    base = F(t) ** u
    if base.denominator != 1:
        bdisp = f"({fs(base)})"
    else:
        bdisp = fs(base)
    rhs = F(t) ** v
    if rhs > 1000 or u == v:
        return None
    x = F(v, u) - s
    ex = "x" if s == 0 else f"x{s:+d}"
    lhs_in = "x" if s == 0 else f"(x{m(f'{s:+d}')})"
    ex_l = lhs_in[1:-1] if u == 1 and s else ('' if u == 1 else ('−' if u == -1 else str(u))) + lhs_in
    return num(f"方程式 {bdisp}{sup(ex)}={fs(rhs)} を解きなさい。", x,
               f"{t}の累乗にそろえると {ex_l}={fs(v)} より x={fs(x)}。")


def el_log_eq1(rng):
    b = rng.choice([2, 3, 5])
    k = rng.randint(1, 3 if b < 5 else 2)
    s = rng.randint(-4, 4)
    x = b ** k - s
    arg = "x" if s == 0 else f"(x{m(f'{s:+d}')})"
    return num(f"方程式 {logb(b)}{arg}={k} を解きなさい。", x,
               f"{'x' if s == 0 else arg[1:-1]}={b}{sup(k)}={b ** k} より x={x}（真数条件を満たす）。")


LOG2 = [(b, r, c, k) for b in (2, 3) for r in range(2, 30) for c in range(1, r)
        for k in range(1, 7) if r * (r - c) == b ** k]


def el_log_eq2(rng):
    b, r, c, k = rng.choice(LOG2)
    L = logb(b)
    return num(f"方程式 {L}x+{L}(x−{c})={k} を解きなさい。", r,
               f"x(x−{c})={b ** k} より x={r}, −{r - c}。真数条件 x>{c} より x={r}。")


def el_log_eq3(rng):
    t = rng.choice([2, 3])
    u = rng.choice([2, 3]) if t == 2 else 2
    v = rng.choice([w for w in range(-3, 7) if w and w % u])
    k = F(v, u)
    x = F(t) ** v
    return num(f"方程式 log{sub(t ** u)}x={fs(k)} を解きなさい。", x,
               f"x={t ** u}^({fs(k)})={t}{sup(v)}={fs(x)}。")


FLIP = {"<": ">", ">": "<", "≦": "≧", "≧": "≦"}
BASES = [(F(2), "2"), (F(3), "3"), (F(1, 2), "(1/2)"), (F(1, 3), "(1/3)")]


def el_exp_ineq(rng):
    b, bd = rng.choice(BASES)
    k = nz(rng, -3, 3)
    s = rng.choice([0, 0, 1, -1, 2, -2])
    op = rng.choice(list(FLIP))
    rel = op if b > 1 else FLIP[op]
    ex = "x" if s == 0 else f"x{s:+d}"
    ans = k - s
    alt = k + s if s else -k
    correct = f"x{rel}{fs(ans)}"
    wrongs = [f"x{FLIP[rel]}{fs(ans)}", f"x{rel}{fs(alt)}", f"x{FLIP[rel]}{fs(alt)}",
              f"x{rel}{fs(ans + 1)}"]
    note = "底が1より大きいので不等号の向きはそのまま。" if b > 1 else "底が1より小さいので不等号の向きが逆になる。"
    return choice(rng, f"不等式 {bd}{sup(ex)}{op}{fs(b ** k)} を解きなさい。", correct, wrongs,
                  f"右辺={bd}{sup(k)}。{note}よって {correct}。")


def _lsol(rel, T, cond=True):
    if rel in ("<", "≦"):
        return f"0<x{rel}{fs(T)}" if cond else f"x{rel}{fs(T)}"
    return f"x{rel}{fs(T)}"


def el_log_ineq(rng):
    b, _ = rng.choice(BASES)
    k = nz(rng, -2, 3) if b > 1 else nz(rng, -3, 3)
    op = rng.choice(list(FLIP))
    rel = op if b > 1 else FLIP[op]
    T = b ** k
    correct = _lsol(rel, T)
    wrongs = [_lsol(rel, T, cond=False), _lsol(FLIP[rel], T), _lsol(rel, 1 / T),
              _lsol(FLIP[rel], 1 / T), _lsol(rel, abs(b * k))]
    note = "底>1 で向きはそのまま" if b > 1 else "底<1 で向きが逆"
    return choice(rng, f"不等式 {logb(b)}x{op}{fs(k)} を解きなさい。", correct, wrongs,
                  f"真数条件 x>0。{fs(k)}={logb(b)}{fs(T) if T.denominator == 1 else '(' + fs(T) + ')'} で、{note}なので {correct}。")


# ================================================================ 場合の数・確率
def P(n, r):
    return math.perm(n, r)


def C(n, r):
    return math.comb(n, r)


def nPr(n, r):
    return f"{sub(n)}P{sub(r)}"


def nCr(n, r):
    return f"{sub(n)}C{sub(r)}"


def prod_str(n, r):
    return "×".join(str(n - i) for i in range(r))


def cp_perm_calc(rng):
    n = rng.randint(5, 10)
    r = rng.randint(2, 4)
    return num(f"{nPr(n, r)} を計算しなさい。", P(n, r), f"{nPr(n, r)}={prod_str(n, r)}={P(n, r)}。")


def cp_perm_word(rng):
    kind = rng.randint(0, 3)
    n = rng.randint(5, 9)
    r = rng.randint(2, 4)
    if kind == 0:
        p = f"{n}人の中から{r}人を選んで1列に並べる方法は何通りあるか求めなさい。"
    elif kind == 1:
        r = 2
        p = f"{n}人の中から委員長と副委員長を1人ずつ選ぶ方法は何通りあるか求めなさい。"
    elif kind == 2:
        r = 3
        p = f"{n}人のリレー選手から第1〜第3走者を選ぶ方法は何通りあるか求めなさい。"
    else:
        p = f"1から{n}までの{n}枚のカードから{r}枚を並べてできる{r}桁の整数は何個あるか求めなさい。"
    return num(p, P(n, r), f"{nPr(n, r)}={prod_str(n, r)}={P(n, r)}。")


def cp_factorial(rng):
    n = rng.randint(4, 7)
    kind = rng.randint(0, 1)
    p = (f"{n}人が1列に並ぶ並び方は何通りあるか求めなさい。" if kind == 0 else
         f"異なる{n}冊の本を本棚に1列に並べる方法は何通りあるか求めなさい。")
    return num(p, math.factorial(n), f"{n}!={prod_str(n, n)}={math.factorial(n)}。")


def cp_zero_cards(rng):
    k = rng.randint(3, 6)
    r = rng.choice([3, 3, 4]) if k >= 4 else 3
    ans = k * P(k, r - 1)
    cards = ", ".join(str(i) for i in range(k + 1))
    return num(f"{cards} の{k + 1}枚のカードから{r}枚を並べてできる{r}桁の整数は何個あるか求めなさい。", ans,
               f"最高位は0以外の{k}通り、残りは{nPr(k, r - 1)}={P(k, r - 1)}通りで {k}×{P(k, r - 1)}={ans}。")


def cp_adjacent(rng):
    n = rng.randint(4, 7)
    ans = math.factorial(n - 1) * 2
    return num(f"{n}人が1列に並ぶとき、特定の2人A, Bが隣り合う並び方は何通りあるか求めなさい。", ans,
               f"A, Bをまとめて1人とみると{n - 1}!通り、A, Bの並びが2通りで {math.factorial(n - 1)}×2={ans}。")


def cp_comb_calc(rng):
    n = rng.randint(5, 12)
    r = rng.randint(2, n - 2)
    rr = min(r, n - r)
    if r > n - r:
        ex = f"{nCr(n, r)}={nCr(n, rr)}=({prod_str(n, rr)})/{rr}!={C(n, r)}。"
    else:
        ex = f"{nCr(n, r)}=({prod_str(n, r)})/{r}!={C(n, r)}。"
    if rr > 4:
        return None
    return num(f"{nCr(n, r)} を計算しなさい。", C(n, r), ex)


def cp_comb_word(rng):
    n = rng.randint(6, 12)
    r = rng.randint(2, 4)
    kind = rng.randint(0, 2)
    if kind == 0:
        p = f"{n}人の中から{r}人の委員を選ぶ方法は何通りあるか求めなさい。"
    elif kind == 1:
        p = f"異なる{n}個の果物から{r}個を選ぶ方法は何通りあるか求めなさい。"
    else:
        r = 2
        p = f"{n}チームが総当たり戦をするとき、試合数は全部で何試合か求めなさい。"
    return num(p, C(n, r), f"{nCr(n, r)}=({prod_str(n, r)})/{r}!={C(n, r)}。")


def cp_comb_mixed(rng):
    b, g = rng.randint(4, 7), rng.randint(3, 6)
    x, y = rng.randint(1, 3), rng.randint(1, 3)
    if x > b - 1 or y > g - 1:
        return None
    ans = C(b, x) * C(g, y)
    return num(f"男子{b}人、女子{g}人の中から男子{x}人、女子{y}人を選ぶ方法は何通りあるか求めなさい。", ans,
               f"{nCr(b, x)}×{nCr(g, y)}={C(b, x)}×{C(g, y)}={ans}。")


def cp_diagonals(rng):
    n = rng.randint(6, 15)
    ans = C(n, 2) - n
    return num(f"{n}角形の対角線の本数を求めなさい。", ans,
               f"2頂点を結ぶ線分 {nCr(n, 2)}={C(n, 2)} から辺の{n}本を引いて {ans}本。")


def cp_triangles(rng):
    n = rng.randint(5, 12)
    return num(f"正{n}角形の3つの頂点を結んでできる三角形の個数を求めなさい。", C(n, 3),
               f"{n}個の頂点から3つ選ぶので {nCr(n, 3)}={C(n, 3)}。")


def cp_atleast(rng):
    b, g = rng.randint(4, 7), rng.randint(3, 6)
    r = rng.randint(2, 3)
    ans = C(b + g, r) - C(b, r)
    return num(f"男子{b}人、女子{g}人の中から{r}人を選ぶとき、女子が少なくとも1人含まれる選び方は何通りか求めなさい。", ans,
               f"全体 {nCr(b + g, r)}={C(b + g, r)} から男子だけの {nCr(b, r)}={C(b, r)} を引いて {ans}。")


DIE_EV = [("偶数", {2, 4, 6}), ("奇数", {1, 3, 5}), ("3の倍数", {3, 6}), ("5以上", {5, 6}),
          ("4以下", {1, 2, 3, 4}), ("1", {1}), ("6", {6}), ("素数", {2, 3, 5})]


def _ev_phrase(name):
    return f"{name}の目"


def cp_coin_die(rng):
    name, ev = rng.choice(DIE_EV)
    face = rng.choice(["表", "裏"])
    pr = F(1, 2) * F(len(ev), 6)
    return num(f"硬貨1枚とさいころ1個を同時に投げるとき、硬貨は{face}、さいころは{_ev_phrase(name)}が出る確率を求めなさい。", pr,
               f"独立なので 1/2×{fs(F(len(ev), 6))}={fs(pr)}。")


def cp_two_dice(rng):
    (n1, e1), (n2, e2) = rng.sample(DIE_EV, 2)
    pr = F(len(e1), 6) * F(len(e2), 6)
    return num(f"さいころを2回投げるとき、1回目に{_ev_phrase(n1)}、2回目に{_ev_phrase(n2)}が出る確率を求めなさい。", pr,
               f"独立なので {fs(F(len(e1), 6))}×{fs(F(len(e2), 6))}={fs(pr)}。")


PROBS = [F(1, 2), F(1, 3), F(2, 3), F(1, 4), F(3, 4), F(2, 5), F(3, 5), F(4, 5), F(5, 6)]


def cp_archers(rng):
    p, q = rng.sample(PROBS, 2)
    if rng.random() < 0.5:
        pr = p * q
        return num(f"A, Bが的に当てる確率はそれぞれ{fs(p)}, {fs(q)}である。2人が1回ずつ射るとき、2人とも当てる確率を求めなさい。", pr,
                   f"独立なので {fs(p)}×{fs(q)}={fs(pr)}。")
    pr = 1 - (1 - p) * (1 - q)
    return num(f"A, Bが的に当てる確率はそれぞれ{fs(p)}, {fs(q)}である。2人が1回ずつ射るとき、少なくとも1人が当てる確率を求めなさい。", pr,
               f"1−(2人とも外す確率)=1−{fs(1 - p)}×{fs(1 - q)}={fs(pr)}。")


def cp_coin_rep(rng):
    n = rng.randint(3, 7)
    k = rng.randint(1, n - 1)
    pr = F(C(n, k), 2 ** n)
    return num(f"硬貨を{n}回投げるとき、表がちょうど{k}回出る確率を求めなさい。", pr,
               f"{nCr(n, k)}×(1/2){sup(k)}×(1/2){sup(n - k)}={C(n, k)}/{2 ** n}" + ("" if pr.denominator == 2 ** n else f"={fs(pr)}") + "。")


def cp_die_rep(rng):
    name, ev = rng.choice([("1", {1}), ("6", {6}), ("3の倍数", {3, 6}), ("5以上", {5, 6}), ("偶数", {2, 4, 6})])
    n = rng.randint(3, 5)
    k = rng.randint(1, n - 1)
    p = F(len(ev), 6)
    pr = C(n, k) * p ** k * (1 - p) ** (n - k)
    return num(f"さいころを{n}回投げるとき、{_ev_phrase(name)}がちょうど{k}回出る確率を求めなさい。", pr,
               f"{nCr(n, k)}×({fs(p)}){sup(k)}×({fs(1 - p)}){sup(n - k)}={fs(pr)}。")


def cp_atleast_once(rng):
    name, ev = rng.choice([("1", {1}), ("6", {6}), ("3の倍数", {3, 6})])
    n = rng.randint(2, 4)
    p = F(len(ev), 6)
    pr = 1 - (1 - p) ** n
    return num(f"さいころを{n}回投げるとき、{_ev_phrase(name)}が少なくとも1回出る確率を求めなさい。", pr,
               f"余事象を使って 1−({fs(1 - p)}){sup(n)}={fs(pr)}。")


def cp_cond_bag(rng):
    a, b = rng.randint(3, 7), rng.randint(2, 6)
    first = rng.choice(["赤", "白"])
    second = rng.choice(["赤", "白"])
    ra, wa = (a - 1, b) if first == "赤" else (a, b - 1)
    fav = ra if second == "赤" else wa
    pr = F(fav, ra + wa)
    if fav == 0:
        return None
    return num(f"赤玉{a}個、白玉{b}個の袋から1個ずつ2回、戻さずに取り出す。1個目が{first}玉であったとき、2個目が{second}玉である確率を求めなさい。", pr,
               f"1個目のあと袋には赤{ra}個・白{wa}個が残るので {fav}/{ra + wa}" + ("" if pr.denominator == ra + wa else f"={fs(pr)}") + "。")


DICE2 = [(i, j) for i in range(1, 7) for j in range(1, 7)]
DICE_COND = [
    ("目の和が{s}", lambda i, j, s: i + j == s),
]
DICE_EVENT = [
    ("少なくとも一方の目が{t}である", lambda i, j, t: t in (i, j)),
    ("2つの目が等しい", lambda i, j, t: i == j),
    ("大きいさいころの目が偶数である", lambda i, j, t: i % 2 == 0),
    ("大きいさいころの目が{t}である", lambda i, j, t: i == t),
]


def cp_cond_dice(rng):
    s = rng.randint(4, 10)
    en, ef = rng.choice(DICE_EVENT)
    t = rng.randint(1, 6)
    cond = [(i, j) for i, j in DICE2 if i + j == s]
    fav = [(i, j) for i, j in cond if ef(i, j, t)]
    if not fav or len(fav) == len(cond):
        return None
    pr = F(len(fav), len(cond))
    ev = en.format(t=t)
    return num(f"大小2個のさいころを投げる。目の和が{s}であったとき、{ev}確率を求めなさい。", pr,
               f"和が{s}の{len(cond)}通りのうち条件を満たすのは{len(fav)}通りで {fs(pr)}。")


CARD_SETS = [("偶数", lambda x: x % 2 == 0), ("奇数", lambda x: x % 2 == 1),
             ("3の倍数", lambda x: x % 3 == 0), ("4の倍数", lambda x: x % 4 == 0),
             ("5の倍数", lambda x: x % 5 == 0)]


def cp_cond_cards(rng):
    N = rng.choice([10, 12, 15, 20, 24, 30])
    (cn, cf), (en, ef) = rng.sample(CARD_SETS, 2)
    cond = [x for x in range(1, N + 1) if cf(x)]
    fav = [x for x in cond if ef(x)]
    if not fav or len(fav) == len(cond):
        return None
    pr = F(len(fav), len(cond))
    return num(f"1から{N}までの番号のカードから1枚引く。番号が{cn}であったとき、それが{en}である確率を求めなさい。", pr,
               f"{cn}は{len(cond)}枚、そのうち{en}は{len(fav)}枚で {fs(pr)}。")


def cp_cond_table(rng):
    b, g = rng.randint(12, 20), rng.randint(12, 20)
    x, y = rng.randint(2, b - 2), rng.randint(2, g - 2)
    if rng.random() < 0.5:
        who, idx = rng.choice([("男子", (x, b)), ("女子", (y, g))])
        pr = F(*idx)
        return num(f"男子{b}人、女子{g}人のクラスで、眼鏡をかけているのは男子{x}人、女子{y}人である。1人選ぶとき、{who}であったときに眼鏡をかけている確率を求めなさい。", pr,
                   f"{who}{idx[1]}人のうち眼鏡は{idx[0]}人で {fs(pr)}。")
    who, k = rng.choice([("男子", x), ("女子", y)])
    pr = F(k, x + y)
    return num(f"男子{b}人、女子{g}人のクラスで、眼鏡をかけているのは男子{x}人、女子{y}人である。1人選ぶとき、眼鏡をかけていたときに{who}である確率を求めなさい。", pr,
               f"眼鏡の{x + y}人のうち{who}は{k}人で {fs(pr)}。")


def cp_ev_lottery(rng):
    N = rng.choice([10, 20, 50, 100])
    p1, p2 = rng.choice([(1000, 100), (5000, 500), (1000, 200), (3000, 300), (10000, 1000)])
    n1 = rng.randint(1, max(1, N // 20))
    n2 = rng.randint(2, N // 5)
    ev = F(p1 * n1 + p2 * n2, N)
    if ev.denominator != 1:
        return None
    return num(f"{N}本のくじに、{p1}円の当たりが{n1}本、{p2}円の当たりが{n2}本ある。1本引くときの賞金の期待値を求めなさい。", ev,
               f"{p1}×{n1}/{N}+{p2}×{n2}/{N}={fs(ev)}円。")


def cp_ev_die_prize(rng):
    name, ev = rng.choice(DIE_EV[:6])
    a = rng.choice([100, 200, 300, 600, 1200])
    b = rng.choice([0, 0, 60, 120])
    e = F(a * len(ev) + b * (6 - len(ev)), 6)
    other = "何ももらえない" if b == 0 else f"{b}円もらえる"
    return num(f"さいころを1回投げて、{_ev_phrase(name)}が出たら{a}円、それ以外なら{other}。もらえる金額の期待値を求めなさい。", e,
               f"{a}×{fs(F(len(ev), 6))}+{b}×{fs(F(6 - len(ev), 6))}={fs(e)}円。")


def cp_ev_coins(rng):
    n = rng.randint(2, 5)
    pay = rng.choice([None, 10, 50, 100])
    e = F(n, 2) * (pay or 1)
    dist = " ".join(f"{k}枚:{C(n, k)}/{2 ** n}" for k in range(n + 1))
    if pay:
        return num(f"硬貨{n}枚を同時に投げ、表が出た枚数×{pay}円をもらう。もらえる金額の期待値を求めなさい。", e,
                   f"表の枚数の期待値は {n}×1/2={fs(F(n, 2))}枚、よって {fs(e)}円。")
    return num(f"硬貨{n}枚を同時に投げるとき、表が出る枚数の期待値を求めなさい。", e,
               f"Σ(枚数×確率) を計算して {fs(e)}（{dist}）。" if n <= 3 else f"各硬貨の表の期待値1/2を{n}枚分たして {fs(e)}。")


def cp_ev_balls(rng):
    a, b = rng.randint(2, 5), rng.randint(2, 5)
    k = 2
    tot = C(a + b, k)
    e = F(sum(r * C(a, r) * C(b, k - r) for r in range(k + 1)), tot)
    return num(f"赤玉{a}個、白玉{b}個の袋から同時に2個取り出すとき、取り出す赤玉の個数の期待値を求めなさい。", e,
               f"赤0,1,2個の確率は {C(b, 2)}/{tot}, {a * b}/{tot}, {C(a, 2)}/{tot}。1×{a * b}/{tot}+2×{C(a, 2)}/{tot}={fs(e)}。")


def cp_ev_die_face(rng):
    kind = rng.randint(0, 2)
    if kind == 0:
        k = rng.randint(2, 5)
        e = F(sum(k * x for x in range(1, 7)), 6)
        return num(f"さいころを1回投げ、出た目の{k}倍の点数を得る。得点の期待値を求めなさい。", e,
                   f"出た目の期待値は 21/6=7/2 なので {k}×7/2={fs(e)}点。")
    if kind == 1:
        z = rng.randint(1, 6)
        e = F(sum(x for x in range(1, 7) if x != z), 6)
        return num(f"さいころを1回投げ、出た目の数を得点とする。ただし{z}の目が出たら0点とする。得点の期待値を求めなさい。", e,
                   f"(21−{z})/6={fs(e)}点。")
    e = F(sum(max(i, j) for i, j in DICE2), 36)
    return num("さいころを2個投げるとき、大きい方の目（同じなら その目）の期待値を求めなさい。".replace("同じなら その目", "同じならその目"), e,
               f"最大値がkになる確率は (2k−1)/36。Σk(2k−1)/36=161/36。")


# ================================================================ 数列
def sq_ar_term(rng):
    a, d = rng.randint(-10, 12), nz(rng, -6, 8)
    n = rng.randint(8, 30)
    an = a + (n - 1) * d
    if rng.random() < 0.4:
        seq = ", ".join(fs(a + i * d) for i in range(3))
        p = f"等差数列 {seq}, … の第{n}項を求めなさい。"
    else:
        p = f"初項{fs(a)}、公差{fs(d)} の等差数列の第{n}項を求めなさい。"
    return num(p, an, f"a{sub(n)}={fs(a)}+({n}−1)×{paren(d)}={fs(an)}。")


def sq_ar_sum(rng):
    a, d = nz(rng, -5, 10), nz(rng, -4, 6)
    n = rng.randint(8, 25)
    l = a + (n - 1) * d
    S = F(n * (a + l), 2)
    return num(f"初項{fs(a)}、公差{fs(d)} の等差数列の初項から第{n}項までの和を求めなさい。", S,
               f"第{n}項は{fs(l)}。和={n}×({fs(a)}+{paren(l)})/2={fs(S)}。")


def _aterm(d, c):
    return "aₙ=" + lin(d, c, "n")


def sq_ar_general(rng):
    a, d = nz(rng, -8, 10), nz(rng, -5, 6)
    if a == d or abs(d) == 1 and a == -d:
        return None
    seq = ", ".join(fs(a + i * d) for i in range(4))
    wrongs = [_aterm(d, a), _aterm(a, d - a) if a != d else None, _aterm(d, d - a), _aterm(-d, a + d)]
    wrongs = [w for w in wrongs if w]
    return choice(rng, f"等差数列 {seq}, … の一般項を求めなさい。", _aterm(d, a - d), wrongs,
                  f"aₙ={fs(a)}+(n−1)×{paren(d)}={lin(d, a - d, 'n')}。")


def sq_ar_two(rng):
    a, d = rng.randint(-10, 10), nz(rng, -5, 6)
    p, q = sorted(rng.sample(range(2, 12), 2))
    ap, aq = a + (p - 1) * d, a + (q - 1) * d
    n = rng.randint(15, 30)
    an = a + (n - 1) * d
    return num(f"第{p}項が{fs(ap)}、第{q}項が{fs(aq)} である等差数列の第{n}項を求めなさい。", an,
               f"公差=({fs(aq)}−{paren(ap)})/({q}−{p})={fs(d)}、初項={fs(a)} なので a{sub(n)}={fs(an)}。")


def sq_ar_which(rng):
    a, d = rng.randint(-5, 10), rng.randint(2, 7)
    n = rng.randint(10, 40)
    an = a + (n - 1) * d
    return num(f"初項{fs(a)}、公差{d} の等差数列で、{fs(an)} は第何項か求めなさい。", n,
               f"{fs(a)}+(n−1)×{d}={fs(an)} を解いて n={n}。")


def sq_ge_term(rng):
    a = nz(rng, -5, 5)
    r = rng.choice([2, 3, -2, -3, 2, 3])
    n = rng.randint(4, 8)
    if abs(a * r ** (n - 1)) > 100000:
        return None
    an = a * r ** (n - 1)
    if rng.random() < 0.4:
        seq = ", ".join(fs(a * r ** i) for i in range(3))
        p = f"等比数列 {seq}, … の第{n}項を求めなさい。"
    else:
        p = f"初項{fs(a)}、公比{fs(r)} の等比数列の第{n}項を求めなさい。"
    return num(p, an, f"a{sub(n)}={fs(a)}×{paren(r)}{sup(n - 1)}={fs(an)}。")


def sq_ge_sum(rng):
    a = rng.randint(1, 5)
    r = rng.choice([2, 3, -2, F(1, 2)])
    n = rng.randint(4, 8)
    if r == F(1, 2):
        a = 2 ** rng.randint(4, 7)
    S = sum(a * F(r) ** i for i in range(n))
    return num(f"初項{fs(a)}、公比{fs(r)} の等比数列の初項から第{n}項までの和を求めなさい。", S,
               f"S={fs(a)}×(1−{paren(F(r))}{sup(n)})/(1−{paren(F(r))})={fs(S)}。")


def _gterm(c, r):
    rs = paren(r)
    if c == 1:
        return f"aₙ={rs}{sup('n-1')}"
    if c == -1:
        return f"aₙ=−{rs}{sup('n-1')}"
    return f"aₙ={fs(c)}·{rs}{sup('n-1')}"


def sq_ge_general(rng):
    a = rng.choice([2, 3, 4, 5, -2, -3])
    r = rng.choice([2, 3, -2, -3, 4])
    if abs(a) == abs(r):
        return None
    seq = ", ".join(fs(a * r ** i) for i in range(4))
    wrongs = [f"aₙ={fs(a)}·{paren(r)}{sup('n')}", _gterm(r, a), f"aₙ={paren(a * r)}{sup('n-1')}",
              _gterm(-a, r)]
    return choice(rng, f"等比数列 {seq}, … の一般項を求めなさい。", _gterm(a, r), wrongs,
                  f"初項{fs(a)}、公比{fs(r)} なので aₙ=arⁿ⁻¹ より {_gterm(a, r)}。")


def sq_ge_two(rng):
    a = rng.randint(1, 5)
    r = rng.choice([2, 3, -2])
    p = rng.randint(2, 3)
    q = p + rng.choice([2, 3])
    ap, aq = a * r ** (p - 1), a * r ** (q - 1)
    if (q - p) % 2 == 0 and r < 0:
        return None  # 公比が一意に決まらない
    n = q + rng.randint(1, 2)
    an = a * r ** (n - 1)
    return num(f"第{p}項が{fs(ap)}、第{q}項が{fs(aq)} である等比数列（公比は実数）の第{n}項を求めなさい。", an,
               f"r{sup(q - p)}={fs(aq)}/{paren(ap)}={fs(F(aq, ap))} より r={fs(r)}。a{sub(n)}={fs(an)}。")


def sq_ge_ratio(rng):
    a = rng.randint(1, 6)
    r = rng.choice([2, 3, 4, 5, -2, -3])
    k = 3 if r < 0 else rng.choice([3, 4])
    ak = a * r ** (k - 1)
    if (k - 1) % 2 == 0 and r < 0:
        return None
    return num(f"初項{a}、第{k}項が{fs(ak)} の等比数列の公比を求めなさい。ただし公比は正とする。" if (k - 1) % 2 == 0
               else f"初項{a}、第{k}項が{fs(ak)} の等比数列の公比を求めなさい。", r,
               f"{a}r{sup(k - 1)}={fs(ak)} より r{sup(k - 1)}={fs(F(ak, a))}、r={fs(r)}。")


SIG = "Σₖ₌₁"


def sq_sum_sq(rng):
    n = rng.randint(5, 20)
    S = sum(k * k for k in range(1, n + 1))
    p = (f"1²+2²+3²+⋯+{n}² を計算しなさい。" if rng.random() < 0.5 else f"{SIG}{sup(n)} k² を計算しなさい。")
    return num(p, S, f"n(n+1)(2n+1)/6 に n={n} を代入して {S}。")


def sq_sum_k(rng):
    n = rng.randint(10, 50)
    S = n * (n + 1) // 2
    return num(f"{SIG}{sup(n)} k を計算しなさい。", S, f"n(n+1)/2 に n={n} を代入して {S}。")


def sq_sum_cube(rng):
    n = rng.randint(4, 12)
    S = (n * (n + 1) // 2) ** 2
    p = (f"1³+2³+3³+⋯+{n}³ を計算しなさい。" if rng.random() < 0.5 else f"{SIG}{sup(n)} k³ を計算しなさい。")
    return num(p, S, f"{{n(n+1)/2}}² に n={n} を代入して {S}。")


def sq_sum_lin(rng):
    a, b = rng.randint(2, 5), nz(rng, -3, 3)
    n = rng.randint(8, 20)
    S = sum(a * k + b for k in range(1, n + 1))
    return num(f"{SIG}{sup(n)} ({lin(a, b, 'k')}) を計算しなさい。", S,
               f"{a}Σk{'+' if b > 0 else '−'}{abs(b)}×{n}={a}×{n * (n + 1) // 2}{'+' if b > 0 else '−'}{abs(b) * n}={S}。")


def sq_sum_kk1(rng):
    n = rng.randint(5, 12)
    S = sum(k * (k + 1) for k in range(1, n + 1))
    return num(f"1·2+2·3+3·4+⋯+{n}·{n + 1} を計算しなさい。", S,
               f"Σk(k+1)=Σk²+Σk={S}（=n(n+1)(n+2)/3）。")


def sq_tel1(rng):
    n = rng.randint(4, 20)
    S = sum(F(1, k * (k + 1)) for k in range(1, n + 1))
    return num(f"1/(1·2)+1/(2·3)+⋯+1/({n}·{n + 1}) を計算しなさい。", S,
               f"1/(k(k+1))=1/k−1/(k+1) で打ち消し合い、1−1/{n + 1}={fs(S)}。")


def sq_tel2(rng):
    n = rng.randint(3, 12)
    S = sum(F(1, (2 * k - 1) * (2 * k + 1)) for k in range(1, n + 1))
    return num(f"1/(1·3)+1/(3·5)+⋯+1/({2 * n - 1}·{2 * n + 1}) を計算しなさい。", S,
               f"1/((2k−1)(2k+1))=½(1/(2k−1)−1/(2k+1)) より ½(1−1/{2 * n + 1})={fs(S)}。")


def sq_tel3(rng):
    n = rng.randint(3, 10)
    S = sum(F(1, k * (k + 2)) for k in range(1, n + 1))
    return num(f"{SIG}{sup(n)} 1/(k(k+2)) を計算しなさい。", S,
               f"1/(k(k+2))=½(1/k−1/(k+2)) より ½(1+1/2−1/{n + 1}−1/{n + 2})={fs(S)}。")


def _rec_terms(a1, f, n):
    a = [None, a1]
    for i in range(1, n):
        a.append(f(a[i], i))
    return a


def _chain(a, n):
    return ", ".join(f"a{sub(i)}={fs(a[i])}" for i in range(2, n + 1))


def sq_rec_ar(rng):
    a1, d = rng.randint(-5, 8), nz(rng, -5, 6)
    n = rng.randint(4, 8)
    a = _rec_terms(a1, lambda x, i: x + d, n)
    rhs = "aₙ" + m(f"{d:+d}")
    ex = _chain(a, n) if n <= 5 else f"公差{fs(d)}の等差数列なので a{sub(n)}={fs(a1)}+{n - 1}×{paren(d)}={fs(a[n])}"
    return num(f"a₁={fs(a1)}, aₙ₊₁={rhs} のとき、a{sub(n)} を求めなさい。", a[n], ex + "。")


def sq_rec_ge(rng):
    a1, r = nz(rng, -4, 5), rng.choice([2, 3, -2, -3])
    n = rng.randint(4, 6)
    a = _rec_terms(a1, lambda x, i: r * x, n)
    return num(f"a₁={fs(a1)}, aₙ₊₁={fs(r)}aₙ のとき、a{sub(n)} を求めなさい。", a[n],
               f"公比{fs(r)}の等比数列なので a{sub(n)}={fs(a1)}×{paren(r)}{sup(n - 1)}={fs(a[n])}。")


def sq_rec_lin(rng):
    a1 = rng.randint(-3, 5)
    p = rng.choice([2, 3, -1, 2])
    q = nz(rng, -4, 5)
    n = rng.randint(3, 5)
    if F(q, 1 - p) == a1:
        return None
    a = _rec_terms(a1, lambda x, i: p * x + q, n)
    rhs = (f"{fs(p)}aₙ" if p != -1 else "−aₙ") + m(f"{q:+d}")
    return num(f"a₁={fs(a1)}, aₙ₊₁={rhs} のとき、a{sub(n)} を求めなさい。", a[n], "順に代入して " + _chain(a, n) + "。")


def sq_rec_diff(rng):
    a1 = rng.randint(1, 5)
    kind = rng.randint(0, 2)
    n = rng.randint(4, 8)
    if kind == 0:
        c = rng.choice([1, 2, 3])
        f = lambda x, i: x + c * i
        rhs = "aₙ+n" if c == 1 else f"aₙ+{c}n"
        ex = f"階差数列が{c}nなので a{sub(n)}={a1}+{c}×(1+2+⋯+{n - 1})"
    elif kind == 1:
        f = lambda x, i: x + 2 * i + 1
        rhs = "aₙ+2n+1"
        ex = f"a{sub(n)}={a1}+Σ(2k+1)（k=1〜{n - 1}）"
    else:
        n = rng.randint(4, 6)
        f = lambda x, i: x + 2 ** i
        rhs = "aₙ+2ⁿ"
        ex = f"a{sub(n)}={a1}+(2+2²+⋯+2{sup(n - 1)})"
    a = _rec_terms(a1, f, n)
    return num(f"a₁={a1}, aₙ₊₁={rhs} のとき、a{sub(n)} を求めなさい。", a[n], f"{ex}={fs(a[n])}。")


def _gen_fmt(c, p, e, k):
    """c·p^(n+e)+k の表示。"""
    ex = "n" if e == 0 else f"n{e:+d}"
    base = f"{p}{sup(ex)}"
    if c == 1:
        s = base
    elif c == -1:
        s = "−" + base
    else:
        s = f"{fs(c)}·{base}"
    if k:
        s += m(f"{k:+d}")
    return "aₙ=" + s


def _norm(c, p, e):
    # c が p の累乗なら指数に吸収
    while c % p == 0 and c != 0:
        c //= p
        e += 1
    return c, e


def sq_rec_general(rng):
    p = rng.choice([2, 3])
    alpha = rng.choice([1, 2, -1, -2, 3])
    q = alpha * (1 - p)  # 特性方程式の解 α
    a1 = rng.randint(-2, 6)
    c = a1 - alpha
    if c == 0 or q == 0:
        return None
    vals = lambda cc, ee, kk: tuple(cc * F(p) ** (n + ee) + kk for n in range(1, 6))
    truth = vals(c, -1, alpha)
    assert truth[:5] == tuple(_rec_terms(a1, lambda x, i: p * x + q, 5)[1:])
    cands = [(c, -1, alpha), (a1, -1, alpha), (c, 0, alpha), (a1 + alpha, -1, -alpha), (c, -1, -alpha)]
    shown = []
    for cc, ee, kk in cands:
        if cc == 0:
            continue
        v = vals(cc, ee, kk)
        if cands.index((cc, ee, kk)) and v == truth:
            continue
        c2, e2 = _norm(cc, p, ee)
        shown.append(_gen_fmt(c2, p, e2, kk))
    correct = shown[0]
    rhs = f"{p}aₙ" + m(f"{q:+d}")
    return choice(rng, f"a₁={fs(a1)}, aₙ₊₁={rhs} で定まる数列の一般項を求めなさい。", correct, shown[1:],
                  f"aₙ₊₁{m(f'{-alpha:+d}')}={p}(aₙ{m(f'{-alpha:+d}')}) と変形。aₙ{m(f'{-alpha:+d}')} は初項{fs(c)}、公比{p}の等比数列。")


# ================================================================ 登録
def _mk(schedule):
    return lambda rng: collect(rng, schedule)


GENERATORS = {
    "math-analytic-geometry-001": _mk([ag_dist_int] * 7 + [ag_dist_origin] * 3 + [ag_dist_root] * 5),
    "math-analytic-geometry-002": _mk([ag_internal] * 6 + [ag_midpoint] * 4 + [ag_external] * 5),
    "math-analytic-geometry-003": _mk([ag_line_ps] * 8 + [ag_line_2p] * 7),
    "math-analytic-geometry-005": _mk([ag_circle_eq] * 4 + [ag_circle_through] * 4
                                      + [ag_center_std] * 3 + [ag_center_gen] * 4),
    "math-analytic-geometry-006": _mk([ag_count0, ag_count1, ag_count2] * 2 + [ag_count2, ag_count_slope, ag_count_slope]
                                      + [ag_tangent_k] * 3 + [ag_pt_line] * 3),
    "math-exponential-logarithm-006": _mk([el_sum_num] * 3 + [el_diff_num] * 2 + [el_coef_num] * 2
                                          + [el_power] * 2 + [el_root] * 1 + [el_recip] * 1
                                          + [el_combine_sum] * 2 + [el_combine_diff, el_combine_coef]),
    "math-exponential-logarithm-009": _mk([el_common_value] * 5 + [el_common_pure] * 2
                                          + [el_digits] * 5 + [el_first_decimal] * 3),
    "math-exponential-logarithm-010": _mk([el_exp_eq] * 4 + [el_log_eq1] * 2 + [el_log_eq2] * 2 + [el_log_eq3]
                                          + [el_exp_ineq] * 3 + [el_log_ineq] * 3),
    "math-counting-probability-006": _mk([cp_perm_calc] * 4 + [cp_perm_word] * 4 + [cp_factorial] * 3
                                         + [cp_zero_cards] * 2 + [cp_adjacent] * 2),
    "math-counting-probability-007": _mk([cp_comb_calc] * 4 + [cp_comb_word] * 3 + [cp_comb_mixed] * 3
                                         + [cp_diagonals] * 2 + [cp_triangles] * 2 + [cp_atleast]),
    "math-counting-probability-010": _mk([cp_coin_die] * 3 + [cp_two_dice] * 2 + [cp_archers] * 2
                                         + [cp_coin_rep] * 3 + [cp_die_rep] * 3 + [cp_atleast_once] * 2),
    "math-counting-probability-011": _mk([cp_cond_bag] * 4 + [cp_cond_dice] * 4 + [cp_cond_cards] * 4
                                         + [cp_cond_table] * 3),
    "math-counting-probability-012": _mk([cp_ev_lottery] * 4 + [cp_ev_die_prize] * 4 + [cp_ev_coins] * 2
                                         + [cp_ev_balls] * 3 + [cp_ev_die_face] * 2),
    "math-sequences-002": _mk([sq_ar_term] * 4 + [sq_ar_sum] * 4 + [sq_ar_general] * 3
                              + [sq_ar_two] * 2 + [sq_ar_which] * 2),
    "math-sequences-003": _mk([sq_ge_term] * 4 + [sq_ge_sum] * 4 + [sq_ge_general] * 3
                              + [sq_ge_two] * 2 + [sq_ge_ratio] * 2),
    "math-sequences-005": _mk([sq_sum_sq] * 3 + [sq_sum_k] * 2 + [sq_sum_cube] * 2 + [sq_sum_lin] * 2
                              + [sq_sum_kk1] + [sq_tel1] * 2 + [sq_tel2] * 2 + [sq_tel3]),
    "math-sequences-006": _mk([sq_rec_ar] * 3 + [sq_rec_ge] * 3 + [sq_rec_lin] * 3 + [sq_rec_diff] * 3
                              + [sq_rec_general] * 3),
}
