"""数と計算・整数の性質の計算問題ジェネレータ。

GENERATORS = {topic_id: fn(rng) -> list[dict]}（各15問）。答えはすべてコードで計算する。
"""
import math
from fractions import Fraction as F

N = 15
M = "−"  # 表示用マイナス


# ---------------------------------------------------------------- helpers
def num(prompt, ans, explain, accept=None):
    q = {"format": "数字入力", "prompt": prompt, "answer": ans, "explain": explain}
    acc = [a for a in (accept or []) if a != ans]
    if acc:
        q["accept"] = list(dict.fromkeys(acc))
    return q


def choice(rng, prompt, correct, wrongs, explain):
    opts = []
    for w in wrongs:
        if w != correct and w not in opts:
            opts.append(w)
    if len(opts) < 3:
        return None
    opts = opts[:3]
    idx = rng.randrange(4)
    opts.insert(idx, correct)
    return {"format": "4択", "prompt": prompt, "options": opts, "answer": idx, "explain": explain}


def build(rng, makers, n=N):
    """makers を順番に回して n 問作る。問題文の重複は作り直す。"""
    out, seen = [], set()
    i = 0
    while len(out) < n:
        mk = makers[i % len(makers)]
        for _ in range(500):
            try:
                q = mk(rng)
            except ValueError:  # 空の範囲など → 作り直し
                q = None
            if q and q["prompt"] not in seen:
                break
        else:
            raise RuntimeError(f"unique problem not found: {mk.__name__}")
        seen.add(q["prompt"])
        out.append(q)
        i += 1
    return out


def s(n):
    """整数の表示（負は −）。"""
    return f"{M}{-n}" if n < 0 else str(n)


def sp(n):
    """かっこ付き表示: 負なら (−5)。"""
    return f"({M}{-n})" if n < 0 else str(n)


def ans_int(n):
    return str(n)


def frac_str(x):
    x = F(x)
    if x.denominator == 1:
        return str(x.numerator)
    return f"{x.numerator}/{x.denominator}"


def frac_disp(x):
    x = F(x)
    sign = M if x < 0 else ""
    x = abs(x)
    if x.denominator == 1:
        return f"{sign}{x.numerator}"
    return f"{sign}{x.numerator}/{x.denominator}"


def dec_str(x, minus="-"):
    """有限小数を文字列に（末尾の0は消す）。"""
    x = F(x)
    sign = minus if x < 0 else ""
    x = abs(x)
    k = 0
    while (x * 10 ** k).denominator != 1:
        k += 1
        if k > 8:
            raise ValueError("not finite decimal")
    n = int(x * 10 ** k)
    if k == 0:
        return f"{sign}{n}"
    st = str(n).rjust(k + 1, "0")
    return f"{sign}{st[:-k]}.{st[-k:]}"


def dec_accept(x):
    """分数 x が小数第3位までの有限小数なら小数表記を返す。"""
    x = F(x)
    d = x.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d != 1 or x.denominator == 1:
        return []
    st = dec_str(x)
    if len(st.split(".")[1]) <= 3:
        return [st]
    return []


SQUAREFREE = [2, 3, 5, 6, 7, 10, 11]


def rad(c, m):
    """c√m の表示（c は整数、m は平方因数なし）。m==1 なら整数。"""
    if m == 1:
        return s(c)
    if c == 1:
        return f"√{m}"
    if c == -1:
        return f"{M}√{m}"
    return f"{s(c)}√{m}"


def simplify_sqrt(n):
    a, b = 1, n
    k = 2
    while k * k <= b:
        while b % (k * k) == 0:
            b //= k * k
            a *= k
        k += 1
    return a, b


def expr(p, c, m):
    """p + c√m の表示。"""
    if c == 0:
        return s(p)
    if p == 0:
        return rad(c, m)
    r = rad(abs(c), m)
    return f"{s(p)}{'+' if c > 0 else M}{r}"


def val(p, c, m):
    return p + c * math.sqrt(m)


def distinct_by_value(correct_v, cands):
    """(表示, 値) の候補から、正解と値が違うものだけを返す。"""
    out = []
    for txt, v in cands:
        if abs(v - correct_v) > 1e-9:
            out.append(txt)
    return out


# ---------------------------------------------------------------- 003 加法と減法
def g003(rng):
    def a(r):
        x = r.randint(1, 7) * 10 + r.randint(1, 8)
        y = r.randint(1, 8 - x // 10) * 10 + r.randint(0, 9 - x % 10)
        if (x + y) % 10 == 0 or y < 10:
            return None
        return num(f"{x}+{y} を計算しなさい。", ans_int(x + y),
                   f"一の位 {x%10}+{y%10}＝{x%10+y%10}、十の位 {x//10}+{y//10}＝{x//10+y//10}。答えは {x+y}。")

    def b(r):
        x = r.randint(1, 7) * 10 + r.randint(2, 9)
        y = r.randint(1, 8 - x // 10) * 10 + r.randint(10 - x % 10, 9)
        if x + y >= 100 or y < 10:
            return None
        return num(f"{x}+{y} を計算しなさい。", ans_int(x + y),
                   f"一の位 {x%10}+{y%10}＝{x%10+y%10} で十の位へ1繰り上がる。{x}+{y}＝{x+y}。")

    def c(r):
        x = r.randint(3, 9) * 10 + r.randint(2, 9)
        y = r.randint(1, x // 10 - 1) * 10 + r.randint(1, x % 10)
        return num(f"{x}{M}{y} を計算しなさい。", ans_int(x - y),
                   f"一の位 {x%10}{M}{y%10}＝{x%10-y%10}、十の位 {x//10}{M}{y//10}＝{x//10-y//10}。答えは {x-y}。")

    def d(r):
        x = r.randint(3, 9) * 10 + r.randint(0, 7)
        y = r.randint(1, x // 10 - 1) * 10 + r.randint(x % 10 + 1, 9)
        return num(f"{x}{M}{y} を計算しなさい。", ans_int(x - y),
                   f"一の位は {x%10}{M}{y%10} ができないので十の位から1借りて {10+x%10}{M}{y%10}＝{10+x%10-y%10}。答えは {x-y}。")

    return build(rng, [a, b, c, d])


# ---------------------------------------------------------------- 004 筆算
def g004(rng):
    def add(r):
        digits = r.choice([3, 3, 4])
        lo, hi = 10 ** (digits - 1), 10 ** digits - 1
        x, y = r.randint(lo, hi), r.randint(lo if digits == 3 else 100, hi)
        carries = sum(1 for k in range(digits) if (x // 10 ** k) % 10 + (y // 10 ** k) % 10 >= 10)
        if carries < 1 or x + y > 9999:
            return None
        return num(f"{x}+{y} を筆算で計算しなさい。", ans_int(x + y),
                   f"一の位からそろえて足し、10をこえたら上の位へ繰り上げる。{x}+{y}＝{x+y}。")

    def sub(r):
        digits = r.choice([3, 3, 4])
        lo, hi = 10 ** (digits - 1), 10 ** digits - 1
        x = r.randint(lo * 2, hi)
        y = r.randint(100, x - 50)
        borrows = sum(1 for k in range(digits) if (x // 10 ** k) % 10 < (y // 10 ** k) % 10)
        if borrows < 1:
            return None
        return num(f"{x}{M}{y} を筆算で計算しなさい。", ans_int(x - y),
                   f"一の位からそろえて引き、引けない位は上の位から1繰り下げる。{x}{M}{y}＝{x-y}。")

    return build(rng, [add, sub])


# ---------------------------------------------------------------- 005 九九
def g005(rng):
    def kuku(r):
        a, b = r.randint(2, 9), r.randint(2, 9)
        return num(f"{a}×{b} を計算しなさい。", ans_int(a * b),
                   f"{a}の段の九九で {a}×{b}＝{a*b}。")

    def meaning(r):
        a, b = r.randint(2, 9), r.randint(3, 9)
        if a == b:
            return None
        return choice(r, f"{a}×{b} は、どの数を{b}回たした数と同じですか。", str(a),
                      [str(b), str(a + b), str(a * b), str(a - 1)],
                      f"{a}×{b} は {a} を {b} 回たした数（{'+'.join([str(a)]*b)}＝{a*b}）。")

    def step(r):
        a, b = r.randint(2, 9), r.randint(3, 9)
        return num(f"{a}×{b} の答えは、{a}×{b-1} の答えよりいくつ大きいですか。", str(a),
                   f"かける数が1ふえると答えはかけられる数だけふえる。{a*b}{M}{a*(b-1)}＝{a}。")

    return build(rng, [kuku, meaning, kuku, step, kuku])


# ---------------------------------------------------------------- 006 乗法の筆算
def g006(rng):
    def a(r):
        x, y = r.randint(12, 98), r.randint(3, 9)
        if x % 10 == 0 or x % 10 * y < 10:
            return None
        return num(f"{x}×{y} を筆算で計算しなさい。", ans_int(x * y),
                   f"{x%10}×{y}＝{x%10*y}、{x//10*10}×{y}＝{x//10*10*y}。合わせて {x*y}。")

    def b(r):
        x = r.choice([r.randint(23, 98), r.randint(102, 489)])
        y = r.randint(12, 68)
        if x % 10 == 0 or y % 10 == 0 or y % 11 == 0:
            return None
        return num(f"{x}×{y} を筆算で計算しなさい。", ans_int(x * y),
                   f"{x}×{y%10}＝{x*(y%10)}、{x}×{y//10*10}＝{x*(y//10*10)}。合わせて {x*y}。")

    return build(rng, [a, b])


# ---------------------------------------------------------------- 余りの割り算 共通
def rem_choice(r, n, d, prompt):
    q, rr = divmod(n, d)
    correct = f"{q} あまり {rr}"
    wrongs = []
    if q >= 2:
        wrongs.append(f"{q-1} あまり {rr+d}")
    wrongs += [f"{q+1} あまり {rr}", f"{q} あまり {rr+1}" if rr + 1 < d else f"{q} あまり {rr-1}",
               f"{q} あまり {d-rr}" if d - rr != rr else f"{q-1} あまり {rr}", f"{q+1} あまり {d-rr}"]
    return choice(r, prompt, correct, wrongs,
                  f"{d}×{q}＝{d*q}、{n}{M}{d*q}＝{rr}。{rr} は {d} より小さいので {q} あまり {rr}。")


# ---------------------------------------------------------------- 007 除法の意味と余り
def g007(rng):
    def a(r):
        d, q = r.randint(3, 9), r.randint(2, 9)
        return num(f"{d*q}÷{d} を計算しなさい。", str(q),
                   f"{d}×□＝{d*q} となる□を九九で考える。{d}×{q}＝{d*q} だから {q}。")

    def b(r):
        d, q = r.randint(3, 9), r.randint(2, 9)
        rr = r.randint(1, d - 1)
        n = d * q + rr
        return rem_choice(r, n, d, f"{n}÷{d} の商と余りを求めなさい。")

    def b2(r):
        d, q = r.randint(3, 9), r.randint(2, 9)
        rr = r.randint(1, d - 1)
        n = d * q + rr
        return num(f"{n}÷{d} の余りを求めなさい。", str(rr),
                   f"{d}×{q}＝{d*q}、{n}{M}{d*q}＝{rr}。余りは {rr}。")

    return build(rng, [a, b, a, b2, b])


# ---------------------------------------------------------------- 008 除法の筆算
def g008(rng):
    def a(r):
        d = r.randint(2, 9)
        q = r.randint(11, 99 // d)
        if q % 10 == 0:
            return None
        n = d * q
        return num(f"{n}÷{d} を筆算で計算しなさい。", str(q),
                   (f"十の位から: {n//10}÷{d}＝{n//10//d} あまり {n//10%d}、一の位をおろして {n//10%d*10+n%10}÷{d}＝{q%10}。答えは {q}。"
                    if n // 10 % d else
                    f"十の位 {n//10}÷{d}＝{n//10//d}、一の位 {n%10}÷{d}＝{q%10}。答えは {q}。"))

    def b(r):
        d = r.randint(3, 9)
        q = r.randint(100 // d + 1, 999 // d)
        rr = r.randint(1, d - 1)
        n = d * q + rr
        if n > 999:
            return None
        return rem_choice(r, n, d, f"{n}÷{d} の商と余りを求めなさい。")

    def b2(r):
        d = r.randint(3, 9)
        q = r.randint(100 // d + 1, 999 // d)
        rr = r.randint(1, d - 1)
        n = d * q + rr
        if n > 999:
            return None
        return num(f"{n}÷{d} を計算したときの商を求めなさい（余りは答えない）。", str(q),
                   f"{d}×{q}＝{d*q}、{n}{M}{d*q}＝{rr}。商は {q}、余り {rr}。")

    return build(rng, [a, b, b2, a, b])


# ---------------------------------------------------------------- 009 四則演算
def g009(rng):
    def a1(r):
        a, b, c, d = r.randint(2, 20), r.randint(2, 9), r.randint(2, 9), r.randint(1, 9)
        v = a + b * c - d
        if v <= 0:
            return None
        return num(f"{a}+{b}×{c}{M}{d} を計算しなさい。", str(v),
                   f"かけ算を先に: {b}×{c}＝{b*c}。{a}+{b*c}{M}{d}＝{v}。")

    def a2(r):
        a, b, c, d = r.randint(3, 9), r.randint(3, 9), r.randint(2, 9), r.randint(2, 6)
        v = a * b - c * d
        if v <= 0:
            return None
        return num(f"{a}×{b}{M}{c}×{d} を計算しなさい。", str(v),
                   f"かけ算を先に: {a*b}{M}{c*d}＝{v}。")

    def a3(r):
        c, k = r.randint(2, 9), r.randint(2, 9)
        a, d = r.randint(k + 1, 30), r.randint(2, 15)
        b = c * k
        v = a - k + d
        return num(f"{a}{M}{b}÷{c}+{d} を計算しなさい。", str(v),
                   f"わり算を先に: {b}÷{c}＝{k}。{a}{M}{k}+{d}＝{v}。")

    def a4(r):
        a, b = r.randint(2, 9), r.randint(2, 9)
        c, k = r.randint(2, 9), r.randint(2, 9)
        v = a * b + k
        return num(f"{a}×{b}+{c*k}÷{c} を計算しなさい。", str(v),
                   f"{a}×{b}＝{a*b}、{c*k}÷{c}＝{k}。{a*b}+{k}＝{v}。")

    def b1(r):
        a, b, c, d = r.randint(2, 9), r.randint(2, 9), r.randint(2, 9), r.randint(1, 9)
        v = (a + b) * c - d
        return num(f"({a}+{b})×{c}{M}{d} を計算しなさい。", str(v),
                   f"かっこの中を先に: {a}+{b}＝{a+b}。{a+b}×{c}{M}{d}＝{v}。")

    def b2(r):
        a, b, c, d = r.randint(2, 9), r.randint(5, 15), r.randint(1, 9), r.randint(1, 9)
        if b - c < 2:
            return None
        v = a * (b - c) + d
        return num(f"{a}×({b}{M}{c})+{d} を計算しなさい。", str(v),
                   f"かっこの中を先に: {b}{M}{c}＝{b-c}。{a}×{b-c}+{d}＝{v}。")

    def b3(r):
        c = r.randint(2, 9)
        a = r.randint(2, 30)
        b = r.randint(2, 30)
        d = r.randint(2, 9)
        if (a + b) % c:
            return None
        v = (a + b) // c * d
        return num(f"({a}+{b})÷{c}×{d} を計算しなさい。", str(v),
                   f"かっこの中を先に: {a+b}。左から順に {a+b}÷{c}＝{(a+b)//c}、×{d}＝{v}。")

    def b4(r):
        a, b, c, d = r.randint(8, 20), r.randint(2, 7), r.randint(2, 9), r.randint(2, 9)
        if a - b < 2:
            return None
        v = (a - b) * (c + d)
        return num(f"({a}{M}{b})×({c}+{d}) を計算しなさい。", str(v),
                   f"かっこの中を先に: {a-b}×{c+d}＝{v}。")

    return build(rng, [a1, b1, a2, b2, a3, b3, a4, b4])


# ---------------------------------------------------------------- 013 小数の加減
def g013(rng):
    def a(r):
        x, y = F(r.randint(11, 89), 10), F(r.randint(11, 89), 10)
        if (x * 10) % 10 == 0 or (y * 10) % 10 == 0 or (x * 10 % 10 + y * 10 % 10) < 10:
            return None
        v = x + y
        return num(f"{dec_str(x)}+{dec_str(y)} を計算しなさい。", dec_str(v),
                   f"小数点をそろえて計算。{dec_str(x)}+{dec_str(y)}＝{dec_str(v)}。",
                   accept=[dec_str(v) + ".0"] if v.denominator == 1 else None)

    def b(r):
        x, y = F(r.randint(21, 99), 10), F(r.randint(11, 89), 10)
        if x <= y + F(1, 10) or (x * 10) % 10 == 0 or (y * 10) % 10 == 0:
            return None
        v = x - y
        return num(f"{dec_str(x)}{M}{dec_str(y)} を計算しなさい。", dec_str(v),
                   f"小数点をそろえて計算。{dec_str(x)}{M}{dec_str(y)}＝{dec_str(v)}。",
                   accept=[dec_str(v) + ".0"] if v.denominator == 1 else None)

    def c(r):
        x = F(r.randint(101, 899), 100)
        y = F(r.randint(1, 9), 10) + r.randint(0, 3)
        if (x * 100) % 10 == 0:
            return None
        if r.random() < 0.5:
            v = x + y
            return num(f"{dec_str(x)}+{dec_str(y)} を計算しなさい。", dec_str(v),
                       f"小数点の位置をそろえて（{dec_str(y)}＝{dec_str(y)}0 と考える）計算。答えは {dec_str(v)}。")
        if x <= y:
            x, y = x + 3, y
        v = x - y
        return num(f"{dec_str(x)}{M}{dec_str(y)} を計算しなさい。", dec_str(v),
                   f"小数点の位置をそろえて（{dec_str(y)}＝{dec_str(y)}0 と考える）計算。答えは {dec_str(v)}。")

    return build(rng, [a, b, c])


# ---------------------------------------------------------------- 014 小数の乗除
def g014(rng):
    def a(r):
        if r.random() < 0.7:
            x = F(r.randint(11, 99), 10)
        else:
            x = F(r.randint(11, 99), 100)
        n = r.randint(3, 9)
        if (x * 10).denominator == 1 and (x * 10) % 10 == 0:
            return None
        if (x * 100) % 10 == 0 and x.denominator == 100:
            return None
        v = x * n
        k = 10 if (x * 10).denominator == 1 else 100
        return num(f"{dec_str(x)}×{n} を計算しなさい。", dec_str(v),
                   f"{int(x*k)}×{n}＝{int(x*k*n)} を計算し、小数点を左へ{1 if k == 10 else 2}けた移す。答えは {dec_str(v)}。",
                   accept=[dec_str(v) + ".0"] if v.denominator == 1 else None)

    def b(r):
        n = r.randint(2, 9)
        q = F(r.randint(11, 99), 10) if r.random() < 0.7 else F(r.randint(11, 99), 100)
        x = q * n
        if (q * 10).denominator == 1 and (q * 10) % 10 == 0:
            return None
        if x.denominator == 1:
            return None
        return num(f"{dec_str(x)}÷{n} を計算しなさい。", dec_str(q),
                   f"整数のわり算と同じように計算し、商の小数点はわられる数の小数点にそろえる。{dec_str(x)}÷{n}＝{dec_str(q)}。")

    return build(rng, [a, b])


# ---------------------------------------------------------------- 016 約分・通分
def g016(rng):
    def red(r):
        q = r.randint(2, 12)
        p = r.randint(1, q - 1)
        if math.gcd(p, q) != 1:
            return None
        k = r.randint(2, 9)
        if q * k > 99:
            return None
        return num(f"{p*k}/{q*k} を約分しなさい。", f"{p}/{q}",
                   f"分母と分子を最大公約数 {k} でわる。{p*k}÷{k}＝{p}、{q*k}÷{k}＝{q}。", accept=dec_accept(F(p, q)))

    def lcd(r):
        a, b = r.randint(2, 15), r.randint(2, 15)
        if a == b or a % b == 0 or b % a == 0 or math.gcd(a, b) == 1 and r.random() < 0.5:
            return None
        p1, p2 = r.randint(1, a - 1), r.randint(1, b - 1)
        if math.gcd(p1, a) != 1 or math.gcd(p2, b) != 1:
            return None
        l = a * b // math.gcd(a, b)
        return num(f"{p1}/{a} と {p2}/{b} を通分するとき、いちばん小さい共通の分母を求めなさい。", str(l),
                   f"分母 {a} と {b} の最小公倍数が共通の分母。{a} と {b} の最小公倍数は {l}。")

    def numer(r):
        a, b = r.randint(2, 12), r.randint(2, 12)
        if a == b or a % b == 0 or b % a == 0:
            return None
        p1, p2 = r.randint(1, a - 1), r.randint(1, b - 1)
        if math.gcd(p1, a) != 1 or math.gcd(p2, b) != 1:
            return None
        l = a * b // math.gcd(a, b)
        return num(f"{p1}/{a} と {p2}/{b} を分母 {l} で通分したとき、{p1}/{a} の分子を求めなさい。", str(p1 * l // a),
                   f"分母を {a}→{l} と {l//a} 倍するので分子も {l//a} 倍。{p1}×{l//a}＝{p1*l//a}。")

    return build(rng, [red, lcd, red, numer, red])


# ---------------------------------------------------------------- 018 分数の乗除
def rand_frac(r, maxd=9):
    d = r.randint(2, maxd)
    n = r.randint(1, 2 * d)
    f = F(n, d)
    if f.denominator == 1 or f.denominator != d:
        return None
    return f


def g018(rng):
    def mul(r):
        x, y = rand_frac(r), rand_frac(r)
        if not x or not y:
            return None
        v = x * y
        if v == 1 or math.gcd(x.numerator, y.denominator) == 1 and math.gcd(y.numerator, x.denominator) == 1 and r.random() < 0.6:
            return None
        return num(f"{frac_str(x)}×{frac_str(y)} を計算しなさい。", frac_str(v),
                   f"分子どうし・分母どうしをかけ、約分する。({x.numerator}×{y.numerator})/({x.denominator}×{y.denominator})＝{frac_str(v)}。",
                   accept=dec_accept(v))

    def div(r):
        x, y = rand_frac(r), rand_frac(r)
        if not x or not y:
            return None
        v = x / y
        if v == 1:
            return None
        return num(f"{frac_str(x)}÷{frac_str(y)} を計算しなさい。", frac_str(v),
                   f"わる数の逆数をかける。{frac_str(x)}×{y.denominator}/{y.numerator}＝{frac_str(v)}。",
                   accept=dec_accept(v))

    return build(rng, [mul, div])


# ---------------------------------------------------------------- 019 概数・見積り
def round_half_up(n, unit):
    return (n + unit // 2) // unit * unit


def g019(rng):
    units = {10: "十", 100: "百", 1000: "千", 10000: "一万"}

    def r1(r):
        unit = r.choice([100, 1000, 10000])
        n = r.randint(unit * 2, unit * 100 - 1)
        if n % unit == 0 or n % (unit // 10) == 0:
            return None
        v = round_half_up(n, unit)
        dig = n // (unit // 10) % 10
        return num(f"{n} を四捨五入して{units[unit]}の位までの概数にしなさい。", str(v),
                   f"{units[unit]}の位の1つ下の位の数字は {dig}。{'切り上げ' if dig >= 5 else '切り捨て'}て {v}。")

    def r2(r):
        unit = r.choice([100, 1000])
        n = r.randint(unit * 10 + 1, unit * 100 - 1)
        lower = unit // 10
        if n % lower == 0:
            return None
        v = round_half_up(n, unit)
        dig = n // lower % 10
        return num(f"{n} を{units[lower]}の位で四捨五入しなさい。", str(v),
                   f"{units[lower]}の位の数字は {dig}。{'切り上げ' if dig >= 5 else '切り捨て'}て {v}。")

    def r3(r):
        n = r.randint(1001, 99999)
        k = len(str(n))
        unit = 10 ** (k - 2)
        v = round_half_up(n, unit)
        dig = n // (unit // 10) % 10
        if n % unit == 0:
            return None
        return num(f"{n} を四捨五入して上から2けたの概数にしなさい。", str(v),
                   f"上から3けため（{dig}）を四捨五入して {v}。")

    def r4(r):
        x = F(r.randint(1001, 9999), 1000)
        if (x * 1000) % 10 == 0:
            return None
        v = F(round_half_up(int(x * 1000), 100), 1000)
        dig = int(x * 100) % 10
        ans = dec_str(v)
        if "." not in ans:
            ans_disp = ans + ".0"
        else:
            ans_disp = ans
        return num(f"{dec_str(x)} を四捨五入して小数第1位までの概数にしなさい。", ans_disp,
                   f"小数第2位の数字 {dig} を{'切り上げ' if dig >= 5 else '切り捨て'}て {ans_disp}。",
                   accept=[ans])

    def est_mul(r):
        a = r.randint(12, 98) * 10 + r.randint(0, 9)  # 3けた
        b = r.randint(11, 98)
        ra = round_half_up(a, 100)
        rb = round_half_up(b, 10)
        if a % 100 in (0, 50) or b % 10 in (0, 5):
            return None
        v = ra * rb
        tr = (a // 100 * 100) * (b // 10 * 10)
        wrongs = [str(tr), str(v * 10), str(v // 10), str((ra + 100) * rb), str(ra * (rb + 10))]
        return choice(r, f"{a}×{b} を、{a} は上から1けた、{b} も上から1けたの概数にして見積もりなさい。",
                      str(v), wrongs,
                      f"{a}→{ra}、{b}→{rb} として {ra}×{rb}＝{v}。")

    def est_add(r):
        a, b = r.randint(1100, 8999), r.randint(1100, 8999)
        if a % 100 // 10 == 5 or b % 100 // 10 == 5:
            return None
        ra, rb = round_half_up(a, 100), round_half_up(b, 100)
        op = r.choice(["+", "-"])
        if op == "-" and a < b:
            a, b, ra, rb = b, a, rb, ra
        v = ra + rb if op == "+" else ra - rb
        tr = (a // 100 * 100 + b // 100 * 100) if op == "+" else (a // 100 * 100 - b // 100 * 100)
        r1000 = (round_half_up(a, 1000) + round_half_up(b, 1000)) if op == "+" else (round_half_up(a, 1000) - round_half_up(b, 1000))
        wrongs = [str(tr), str(r1000), str(v + 100), str(v - 100)]
        disp = "+" if op == "+" else M
        return choice(r, f"{a}{disp}{b} を、それぞれ百の位までの概数にして見積もりなさい。",
                      str(v), wrongs,
                      f"{a}→{ra}、{b}→{rb}。{ra}{disp}{rb}＝{v}。")

    return build(rng, [r1, est_mul, r2, est_add, r3, r4])


# ---------------------------------------------------------------- 021 正負の数
def nz(r, lo, hi):
    while True:
        v = r.randint(lo, hi)
        if v:
            return v


def g021(rng):
    def add(r):
        a, b = nz(r, -15, 15), nz(r, -15, 15)
        if a > 0 and b > 0 or a + b == 0:
            return None
        v = a + b
        return num(f"{sp(a)}+{sp(b)} を計算しなさい。", str(v),
                   f"{'符号が同じなので絶対値の和に共通の符号' if a*b>0 else '符号が違うので絶対値の差に、絶対値の大きい方の符号'}をつける。答えは {s(v)}。")

    def sub(r):
        a, b = nz(r, -15, 15), nz(r, -15, 15)
        if b > 0 and a > 0 or a - b == 0:
            return None
        v = a - b
        return num(f"{sp(a)}{M}{sp(b)} を計算しなさい。", str(v),
                   f"ひき算はひく数の符号を変えたたし算に: {sp(a)}+{sp(-b)}＝{s(v)}。")

    def three(r):
        a, b, c = nz(r, -12, 12), r.randint(2, 15), r.randint(2, 15)
        v = a + b - c
        if v == 0:
            return None
        return num(f"{s(a)}+{b}{M}{c} を計算しなさい。", str(v),
                   f"正の項 {'+'.join(str(t) for t in (a, b) if t > 0)}、負の項 {M}{c}{f'、{M}{-a}' if a<0 else ''} をまとめる。答えは {s(v)}。")

    def mul(r):
        a, b = nz(r, -12, 12), nz(r, -9, 9)
        if a > 0 and b > 0 or abs(a) == 1 or abs(b) == 1:
            return None
        v = a * b
        return num(f"{sp(a)}×{sp(b)} を計算しなさい。", str(v),
                   f"{'負の数が1つなので符号は −' if v<0 else '同符号どうしなので符号は +'}。{abs(a)}×{abs(b)}＝{abs(v)} で答えは {s(v)}。")

    def div(r):
        q, b = nz(r, -12, 12), nz(r, -9, 9)
        a = q * b
        if a > 0 and b > 0 or abs(b) == 1 or abs(q) == 1:
            return None
        return num(f"{sp(a)}÷{sp(b)} を計算しなさい。", str(q),
                   f"{'異符号なので符号は −' if q<0 else '同符号なので符号は +'}。{abs(a)}÷{abs(b)}＝{abs(q)} で答えは {s(q)}。")

    def mul3(r):
        a, b, c = nz(r, -6, 6), nz(r, -6, 6), nz(r, -6, 6)
        if sum(1 for t in (a, b, c) if t < 0) < 2 or 1 in (abs(a), abs(b), abs(c)):
            return None
        v = a * b * c
        negs = sum(1 for t in (a, b, c) if t < 0)
        return num(f"{sp(a)}×{sp(b)}×{sp(c)} を計算しなさい。", str(v),
                   f"負の数が{negs}個なので符号は{'−' if negs % 2 else '+'}。{abs(a)}×{abs(b)}×{abs(c)}＝{abs(v)} で答えは {s(v)}。")

    return build(rng, [add, mul, sub, div, three, mul3])


# ---------------------------------------------------------------- 023 根号を含む式
def g023(rng):
    def rad_wrongs(c, m, pairs):
        """(係数, 根号の中) の候補から、c√m と値が異なるものを表示にして返す。"""
        out = []
        for cc, mm in pairs:
            if cc == 0 or mm <= 0:
                continue
            t = rad(cc, mm) if mm != 1 else s(cc)
            if abs(cc * math.sqrt(mm) - c * math.sqrt(m)) > 1e-9 and t not in out:
                out.append(t)
        return out

    def simp(r):
        a, b = r.randint(2, 6), r.choice([2, 3, 5, 6, 7])
        n = a * a * b
        if n > 200:
            return None
        cor = rad(a, b)
        wr = rad_wrongs(a, b, [(a * a, b), (b, a), (a + 1, b), (a - 1, b), (a, 2 * b), (2 * a, b)])
        return choice(r, f"√{n} を a√b の形に簡単にしなさい。", cor, wr,
                      f"{n}＝{a}²×{b} だから √{n}＝{cor}。")

    def addsub(r):
        b = r.choice([2, 3, 5, 6, 7])
        p, q = r.randint(2, 7), r.randint(1, 6)
        op = r.choice(["+", "-"])
        c = p + q if op == "+" else p - q
        if c == 0:
            return None
        cor = rad(c, b)
        disp = "+" if op == "+" else M
        other = p - q if op == "+" else p + q
        pairs = [(p + q, 2 * b) if op == "+" else (p - q, 1), (other, b), (p * q, b), (c + 1, b), (-c, b)]
        wr = rad_wrongs(c, b, pairs)
        return choice(r, f"{rad(p, b)}{disp}{rad(q, b)} を計算しなさい。", cor, wr,
                      f"√{b} を1つの文字のように考えて係数を計算: {p}{disp}{q}＝{s(c)}。答えは {cor}。")

    def mul_int(r):
        b = r.choice([2, 3, 5, 6, 7])
        x, y = r.randint(1, 4), r.randint(1, 5)
        if x == y:
            return None
        m1, m2 = b * x * x, b * y * y
        v = b * x * y
        return num(f"√{m1}×√{m2} を計算しなさい。", str(v),
                   f"√{m1}×√{m2}＝√{m1*m2}＝√{v}²＝{v}。")

    def mul_rad(r):
        m1, m2 = r.randint(2, 15), r.randint(2, 15)
        if simplify_sqrt(m1)[0] != 1 or simplify_sqrt(m2)[0] != 1 or m1 >= m2:
            return None
        a, b = simplify_sqrt(m1 * m2)
        if a == 1 or b == 1:
            return None
        cor = rad(a, b)
        wr = [f"√{m1*m2}"] + rad_wrongs(a, b, [(b, a), (a * a, b), (a + 1, b), (a, m1 + m2), (2 * a, b)])
        return choice(r, f"√{m1}×√{m2} を計算し、a√b の形で答えなさい。", cor, wr,
                      f"√{m1}×√{m2}＝√{m1*m2}＝√({a}²×{b})＝{cor}。")

    return build(rng, [simp, addsub, mul_int, simp, addsub, mul_rad])


def parse_rad(t):
    """'3√2' / '√5' / '−2√3' / '7' を (0, c, m) に。"""
    t = t.replace(M, "-")
    if "√" not in t:
        return (int(t), 0, 1)
    c, m = t.split("√")
    c = {"": 1, "-": -1}.get(c, None) if c in ("", "-") else int(c)
    return (0, c, int(m))


# ---------------------------------------------------------------- 025 無理数の四則
def g025(rng):
    def addsimp(r):
        b = r.choice([2, 3, 5, 6])
        terms = []
        k = r.choice([2, 3])
        total = 0
        for i in range(k):
            a = r.randint(1, 4)
            coef = r.randint(1, 3)
            sign = 1 if i == 0 or r.random() < 0.6 else -1
            terms.append((sign, coef, a))
            total += sign * coef * a
        if total == 0 or len({a for _, _, a in terms}) < len(terms) or all(a == 1 for _, _, a in terms):
            return None
        parts = []
        for i, (sg, coef, a) in enumerate(terms):
            n = a * a * b
            tx = f"√{n}" if coef == 1 else f"{coef}√{n}"
            parts.append((("" if i == 0 else "+") if sg > 0 else M) + tx)
        prompt_e = "".join(parts)
        if len(prompt_e) > 18:
            return None
        cor = rad(total, b)
        steps = "".join(((("" if i == 0 else "+") if sg > 0 else M) + rad(coef * a, b)) for i, (sg, coef, a) in enumerate(terms))
        naive_ok = len(terms) == 2 and all(sg > 0 and coef == 1 for sg, coef, _ in terms)
        cands = [(f"√{sum(a * a * b for *_, a in terms)}" if naive_ok else rad(total + 1, b), 0),
                 (rad(total + (1 if total > 0 else -1), b), 0),
                 (rad(sum(coef * a for _, coef, a in terms), b), 0),
                 (rad(total, 2 * b) if simplify_sqrt(2 * b)[0] == 1 else rad(total * 2, b), 0),
                 (rad(-total, b), 0)]
        wr = []
        for t, _ in cands:
            if "√0" in t or t.endswith("√1"):
                continue
            try:
                v = val(*parse_rad(t))
            except ValueError:
                continue
            if abs(v - total * math.sqrt(b)) > 1e-9 and t not in wr:
                wr.append(t)
        return choice(r, f"{prompt_e} を計算しなさい。", cor, wr,
                      f"それぞれ簡単にすると {steps}。まとめて {cor}。")

    def conj(r):
        # (√a+b)(√a−b) or (√a+√b)(√a−√b)
        a = r.choice([2, 3, 5, 6, 7, 10, 11])
        if r.random() < 0.5:
            b = r.randint(1, 4)
            v = a - b * b
            bd = str(b)
            bsq = str(b * b)
            wrong_sq = a + b * b
        else:
            b = r.choice([2, 3, 5, 6, 7])
            if b == a:
                return None
            v = a - b
            bd = f"√{b}"
            bsq = str(b)
            wrong_sq = a + b
        if v == 0:
            return None
        return num(f"(√{a}+{bd})(√{a}{M}{bd}) を計算しなさい。", str(v),
                   f"(x+y)(x{M}y)＝x²{M}y² を使う。{a}{M}{bsq}＝{s(v)}。")

    def square(r):
        a = r.choice([2, 3, 5, 6, 7])
        b = r.randint(1, 4)
        sg = r.choice([1, -1])
        p, c = a + b * b, sg * 2 * b
        cor = expr(p, c, a)
        cands = [(expr(a + b * b, 0, a), a + b * b), (expr(a + b * b, sg * b, a), val(a + b * b, sg * b, a)),
                 (expr(a - b * b, c, a) if a != b * b else expr(p, 2 * c, a), 0),
                 (expr(p, -c, a), val(p, -c, a)), (expr(a * a + b * b, c, a), val(a * a + b * b, c, a))]
        wr = []
        for t, v in cands:
            if t not in wr and t != cor:
                wr.append(t)
        bd = str(b)
        return choice(r, f"(√{a}{'+' if sg > 0 else M}{bd})² を計算しなさい。", cor, wr,
                      f"(x{'+' if sg>0 else M}y)²＝x²{'+' if sg>0 else M}2xy+y²。{a}{'+' if sg>0 else M}{2*b}√{a}+{b*b}＝{cor}。")

    def dist(r):
        a = r.choice([2, 3, 5, 6])
        k = r.randint(1, 5)
        b = r.choice([2, 3, 5, 6, 7])
        if b == a:
            return None
        ra, rb = simplify_sqrt(a * b)
        if ra == 1:
            return None
        # √a(√b + k√a) = √(ab) + k·a
        p = k * a
        cor = f"{p}+{rad(ra, rb)}"
        wr = [f"{p}+√{a+b}", f"{k}+{rad(ra, rb)}",
              f"{p}+{rad(ra, rb * 2)}" if simplify_sqrt(rb * 2)[0] == 1 else f"{p+1}+{rad(ra, rb)}",
              f"{p+a}+{rad(ra, rb)}"]
        kd = "" if k == 1 else str(k)
        return choice(r, f"√{a}(√{b}+{kd}√{a}) を計算しなさい。", cor, wr,
                      f"分配法則で √{a}×√{b}+{kd}√{a}×√{a}＝√{a*b}+{p}＝{rad(ra, rb)}+{p}。")

    return build(rng, [addsimp, conj, addsimp, square, addsimp, dist])


# ---------------------------------------------------------------- 整数003 GCD/LCM
def gi003(rng):
    def gcd2(r):
        g = r.randint(2, 18)
        a, b = r.randint(2, 9), r.randint(2, 9)
        if a == b or math.gcd(a, b) != 1 or g * max(a, b) > 150:
            return None
        x, y = sorted((g * a, g * b))
        return num(f"{x} と {y} の最大公約数を求めなさい。", str(g),
                   f"{x}＝{g}×{x//g}、{y}＝{g}×{y//g} で {x//g} と {y//g} に共通の約数はない。最大公約数は {g}。")

    def gcd3(r):
        g = r.randint(2, 12)
        a, b, c = sorted(r.sample(range(2, 10), 3))
        if math.gcd(math.gcd(a, b), c) != 1 or g * c > 120:
            return None
        return num(f"{g*a}、{g*b}、{g*c} の最大公約数を求めなさい。", str(g),
                   f"3つとも {g} でわり切れ、{a}、{b}、{c} に共通の約数はない。最大公約数は {g}。")

    def lcm2(r):
        x, y = sorted(r.sample(range(4, 40), 2))
        g = math.gcd(x, y)
        if g == 1 and r.random() < 0.7 or y % x == 0:
            return None
        l = x * y // g
        if l > 400:
            return None
        return num(f"{x} と {y} の最小公倍数を求めなさい。", str(l),
                   f"最大公約数は {g}。最小公倍数＝{x}×{y}÷{g}＝{l}。")

    def lcm3(r):
        a, b, c = sorted(r.sample(range(2, 16), 3))
        l = math.lcm(a, b, c)
        if l > 240 or l in (a * b * c,) or c % a == 0 and c % b == 0:
            return None
        return num(f"{a}、{b}、{c} の最小公倍数を求めなさい。", str(l),
                   f"素因数分解して、それぞれの素因数の最大の個数をかけ合わせる。最小公倍数は {l}。")

    return build(rng, [gcd2, lcm2, gcd2, lcm2, gcd3, lcm3])


# ---------------------------------------------------------------- 整数005 除法と余り
def gi005(rng):
    def pos(r):
        d = r.randint(3, 13)
        q = r.randint(3, 20)
        rr = r.randint(1, d - 1)
        n = d * q + rr
        return rem_choice(r, n, d, f"{n} を {d} で割った商と余りを求めなさい。")

    def neg_choice(r):
        d = r.randint(3, 9)
        n = -r.randint(d + 1, 60)
        if n % d == 0:
            return None
        q, rr = divmod(n, d)
        tq = -((-n) // d)
        tr = n - d * tq  # 切り捨て（負の余り）
        cor = f"商 {s(q)}、余り {rr}"
        cands = [(tq, tr), (tq, -tr), (q, -rr), (q + 1, rr), (tq, rr)]
        wr = []
        for cq, cr in cands:
            if not (n == d * cq + cr and 0 <= cr < d):
                wr.append(f"商 {s(cq)}、余り {s(cr)}")
        return choice(r, f"{s(n)} を {d} で割った商と余りを求めなさい。ただし余りは0以上{d}未満とする。", cor, wr,
                      f"{s(n)}＝{d}×({s(q)})+{rr} で 0≦{rr}<{d}。商 {s(q)}、余り {rr}。")

    def neg_rem(r):
        d = r.randint(3, 11)
        n = -r.randint(d + 1, 80)
        if n % d == 0:
            return None
        q, rr = divmod(n, d)
        return num(f"{s(n)} を {d} で割った余りを求めなさい。ただし余りは0以上{d}未満とする。", str(rr),
                   f"{s(n)}＝{d}×({s(q)})+{rr}。余りは {rr}。")

    def pos_rem(r):
        d = r.randint(6, 15)
        n = r.randint(100, 500)
        if n % d == 0:
            return None
        q, rr = divmod(n, d)
        return num(f"{n} を {d} で割った余りを求めなさい。", str(rr),
                   f"{n}＝{d}×{q}+{rr}。余りは {rr}。")

    return build(rng, [pos, neg_choice, pos_rem, neg_rem])


# ---------------------------------------------------------------- 整数007 n進法
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def to_base(n, b):
    ds = []
    while n:
        ds.append(str(n % b))
        n //= b
    return "".join(reversed(ds)) or "0"


def gi007(rng):
    def to_dec(r):
        b = r.choice([2, 2, 3, 4, 5, 8])
        hi = {2: 63, 3: 80, 4: 120, 5: 124, 8: 300}[b]
        n = r.randint(b + 2, hi)
        t = to_base(n, b)
        if len(t) < 3:
            return None
        terms = "+".join(f"{d}×{b}{''.join('⁰¹²³⁴⁵⁶⁷⁸⁹'[int(c)] for c in str(len(t)-1-i))}" for i, d in enumerate(t) if d != "0")
        return num(f"{b}進法で表された数 {t}₍{str(b).translate(SUB)}₎ を10進法で表しなさい。", str(n),
                   f"{terms}＝{n}。")

    def from_dec(r):
        b = r.choice([2, 2, 3, 4, 5])
        hi = {2: 60, 3: 80, 4: 100, 5: 120}[b]
        n = r.randint(b * b, hi)
        t = to_base(n, b)
        return num(f"10進法の {n} を{b}進法で表しなさい。", t,
                   f"{n} を {b} で割り続け、余りを下から並べる。{n}＝{t}₍{str(b).translate(SUB)}₎。")

    return build(rng, [to_dec, from_dec])


GENERATORS = {
    "math-number-calculation-003": g003,
    "math-number-calculation-004": g004,
    "math-number-calculation-005": g005,
    "math-number-calculation-006": g006,
    "math-number-calculation-007": g007,
    "math-number-calculation-008": g008,
    "math-number-calculation-009": g009,
    "math-number-calculation-013": g013,
    "math-number-calculation-014": g014,
    "math-number-calculation-016": g016,
    "math-number-calculation-018": g018,
    "math-number-calculation-019": g019,
    "math-number-calculation-021": g021,
    "math-number-calculation-023": g023,
    "math-number-calculation-025": g025,
    "math-integer-properties-003": gi003,
    "math-integer-properties-005": gi005,
    "math-integer-properties-007": gi007,
}
