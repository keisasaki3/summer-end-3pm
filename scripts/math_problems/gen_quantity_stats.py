"""量・比・割合 / データ・統計 の計算問題ジェネレータ。

GENERATORS = {topic_id: fn(rng) -> list[dict]}（build.py が読み込む）。
答えはすべてコードで計算する（Fraction / 整数演算）。
"""
from fractions import Fraction
from math import isqrt

N_PER_TOPIC = 15


# ---------------------------------------------------------------- 共通ヘルパ

def fmt(x):
    """Fraction/int を正規形の文字列に（整数・有限小数・既約分数）。"""
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    d = x.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    if d != 1:
        return f"{x.numerator}/{x.denominator}"
    sign = "-" if x < 0 else ""
    x = abs(x)
    whole = x.numerator // x.denominator
    rem = x - whole
    digits = ""
    while rem:
        rem *= 10
        digit = rem.numerator // rem.denominator
        digits += str(digit)
        rem -= digit
    return f"{sign}{whole}.{digits}"


def frac_str(x):
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def num(prompt, ans, explain, accept=()):
    q = {"format": "数字入力", "prompt": prompt, "answer": fmt(ans), "explain": explain}
    acc = []
    for a in list(accept) + [frac_str(ans)]:
        if a != q["answer"] and a not in acc:
            acc.append(a)
    if acc:
        q["accept"] = acc
    return q


def choice(rng, prompt, correct, wrongs, explain):
    opts = [correct]
    for w in wrongs:
        if w not in opts:
            opts.append(w)
    if len(opts) < 4:
        return None
    opts = opts[:4]
    rng.shuffle(opts)
    return {"format": "4択", "prompt": prompt, "options": opts,
            "answer": opts.index(correct), "explain": explain}


def collect(rng, makers, n=N_PER_TOPIC):
    """makers を順番に回して重複なしで n 問集める。"""
    out, seen, i, tries = [], set(), 0, 0
    while len(out) < n:
        tries += 1
        if tries > 5000:
            raise RuntimeError("問題が集まらない")
        q = makers[i % len(makers)](rng)
        if q is None or q["prompt"] in seen:
            continue
        seen.add(q["prompt"])
        out.append(q)
        i += 1
    return out


def lst(xs):
    return ", ".join(fmt(x) for x in xs)


def median(s):
    s = sorted(s)
    n = len(s)
    if n % 2:
        return Fraction(s[n // 2])
    return Fraction(s[n // 2 - 1] + s[n // 2], 2)


def mean(xs):
    return Fraction(sum(xs), len(xs))


def variance(xs):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def frac_sqrt(x):
    """x が有理数の平方なら平方根、そうでなければ None。"""
    x = Fraction(x)
    if x < 0:
        return None
    a, b = isqrt(x.numerator), isqrt(x.denominator)
    if a * a == x.numerator and b * b == x.denominator:
        return Fraction(a, b)
    return None


def short_decimal(x, places=2):
    """小数第 places 位までで表せるか。"""
    return (Fraction(x) * 10 ** places).denominator == 1


PI314 = Fraction(314, 100)


# ---------------------------------------------------------------- 量・比・割合

def t_rect_area(rng):
    def rect(r):
        a, b = r.randint(3, 15), r.randint(3, 20)
        if a == b:
            return None
        return num(f"たて{a}cm、よこ{b}cmの長方形の面積を求めなさい。(cm²)", a * b,
                   f"{a}×{b}＝{a * b}(cm²)。")

    def rect_m(r):
        a, b = r.randint(2, 12), r.randint(5, 30)
        if a == b:
            return None
        return num(f"たて{a}m、よこ{b}mの長方形の花だんの面積を求めなさい。(m²)", a * b,
                   f"{a}×{b}＝{a * b}(m²)。")

    def square(r):
        a = r.randint(3, 20)
        return num(f"1辺{a}cmの正方形の面積を求めなさい。(cm²)", a * a, f"{a}×{a}＝{a * a}(cm²)。")

    def square_perim(r):
        a = r.randint(3, 15)
        return num(f"まわりの長さが{4 * a}cmの正方形の面積を求めなさい。(cm²)", a * a,
                   f"1辺は{4 * a}÷4＝{a}cm。{a}×{a}＝{a * a}(cm²)。")

    def rect_side(r):
        a, b = r.randint(3, 12), r.randint(4, 15)
        if a == b:
            return None
        return num(f"面積が{a * b}cm²で、たてが{a}cmの長方形のよこの長さを求めなさい。(cm)", b,
                   f"{a * b}÷{a}＝{b}(cm)。")

    return collect(rng, [rect, square, rect_m, square_perim, rect, square, rect_side])


def t_tri_quad_area(rng):
    def tri(r):
        a, h = r.randint(3, 16), r.randint(3, 14)
        if a * h % 2:
            return None
        return num(f"底辺{a}cm、高さ{h}cmの三角形の面積を求めなさい。(cm²)", Fraction(a * h, 2),
                   f"{a}×{h}÷2＝{a * h // 2}(cm²)。")

    def para(r):
        a, h = r.randint(3, 16), r.randint(3, 14)
        return num(f"底辺{a}cm、高さ{h}cmの平行四辺形の面積を求めなさい。(cm²)", a * h,
                   f"{a}×{h}＝{a * h}(cm²)。")

    def tri_h(r):
        a, h = r.randint(4, 14), r.randint(3, 12)
        if a * h % 2:
            return None
        s = a * h // 2
        return num(f"面積が{s}cm²、底辺が{a}cmの三角形の高さを求めなさい。(cm)", h,
                   f"{s}×2÷{a}＝{h}(cm)。")

    def trap(r):
        a, b, h = r.randint(2, 10), r.randint(4, 14), r.randint(3, 10)
        if a >= b or (a + b) * h % 2:
            return None
        return num(f"上底{a}cm、下底{b}cm、高さ{h}cmの台形の面積を求めなさい。(cm²)",
                   Fraction((a + b) * h, 2), f"({a}＋{b})×{h}÷2＝{(a + b) * h // 2}(cm²)。")

    def para_h(r):
        a, h = r.randint(3, 12), r.randint(3, 12)
        return num(f"面積が{a * h}cm²、底辺が{a}cmの平行四辺形の高さを求めなさい。(cm)", h,
                   f"{a * h}÷{a}＝{h}(cm)。")

    return collect(rng, [tri, para, tri, para, trap, tri_h, para_h])


def t_circle_area(rng):
    note = "円周率は3.14とする。"

    def radius(r):
        k = r.randint(1, 12)
        s = PI314 * k * k
        return num(f"半径{k}cmの円の面積を求めなさい。{note}(cm²)", s,
                   f"{k}×{k}×3.14＝{fmt(s)}(cm²)。")

    def diameter(r):
        k = r.randint(1, 10)
        d = 2 * k
        s = PI314 * k * k
        return num(f"直径{d}cmの円の面積を求めなさい。{note}(cm²)", s,
                   f"半径は{k}cm。{k}×{k}×3.14＝{fmt(s)}(cm²)。")

    def half(r):
        k = r.randint(2, 10)
        s = PI314 * k * k / 2
        return num(f"半径{k}cmの半円の面積を求めなさい。{note}(cm²)", s,
                   f"{k}×{k}×3.14÷2＝{fmt(s)}(cm²)。")

    def quarter(r):
        k = r.choice([2, 4, 6, 8, 10, 12])
        s = PI314 * k * k / 4
        return num(f"半径{k}cmのおうぎ形(中心角90°)の面積を求めなさい。{note}(cm²)", s,
                   f"{k}×{k}×3.14÷4＝{fmt(s)}(cm²)。")

    return collect(rng, [radius, diameter, radius, half, diameter, radius, quarter])


def t_box_volume(rng):
    def box(r):
        a, b, c = r.randint(2, 10), r.randint(2, 12), r.randint(2, 10)
        if len({a, b, c}) < 3:
            return None
        return num(f"たて{a}cm、よこ{b}cm、高さ{c}cmの直方体の体積を求めなさい。(cm³)", a * b * c,
                   f"{a}×{b}×{c}＝{a * b * c}(cm³)。")

    def cube(r):
        a = r.randint(2, 12)
        return num(f"1辺{a}cmの立方体の体積を求めなさい。(cm³)", a ** 3,
                   f"{a}×{a}×{a}＝{a ** 3}(cm³)。")

    def box_h(r):
        a, b, c = r.randint(2, 8), r.randint(3, 10), r.randint(2, 9)
        if len({a, b, c}) < 3:
            return None
        v = a * b * c
        return num(f"体積が{v}cm³、たて{a}cm、よこ{b}cmの直方体の高さを求めなさい。(cm)", c,
                   f"{v}÷({a}×{b})＝{c}(cm)。")

    def box_m(r):
        a, b, c = r.randint(2, 6), r.randint(2, 8), r.randint(1, 5)
        if len({a, b, c}) < 3:
            return None
        return num(f"たて{a}m、よこ{b}m、深さ{c}mの直方体の水そうの容積を求めなさい。(m³)", a * b * c,
                   f"{a}×{b}×{c}＝{a * b * c}(m³)。")

    return collect(rng, [box, cube, box, cube, box_h, box, cube, box_m])


def t_prism_volume(rng):
    note = "円周率は3.14とする。"

    def prism(r):
        s, h = r.randint(6, 40), r.randint(3, 15)
        return num(f"底面積{s}cm²、高さ{h}cmの角柱の体積を求めなさい。(cm³)", s * h,
                   f"{s}×{h}＝{s * h}(cm³)。")

    def tri_prism(r):
        a, b, h = r.randint(3, 10), r.randint(3, 10), r.randint(4, 12)
        if a * b % 2:
            return None
        s = a * b // 2
        return num(f"底面が底辺{a}cm、高さ{b}cmの三角形で、高さが{h}cmの三角柱の体積を求めなさい。(cm³)",
                   s * h, f"底面積は{a}×{b}÷2＝{s}cm²。{s}×{h}＝{s * h}(cm³)。")

    def cyl(r):
        k, h = r.randint(1, 8), r.randint(2, 12)
        v = PI314 * k * k * h
        return num(f"底面の半径{k}cm、高さ{h}cmの円柱の体積を求めなさい。{note}(cm³)", v,
                   f"{k}×{k}×3.14×{h}＝{fmt(v)}(cm³)。")

    def cyl_d(r):
        k, h = r.randint(1, 6), r.randint(2, 10)
        v = PI314 * k * k * h
        return num(f"底面の直径{2 * k}cm、高さ{h}cmの円柱の体積を求めなさい。{note}(cm³)", v,
                   f"半径は{k}cm。{k}×{k}×3.14×{h}＝{fmt(v)}(cm³)。")

    return collect(rng, [prism, cyl, tri_prism, cyl, prism, cyl_d])


def t_speed(rng):
    def speed_kmh(r):
        v, t = r.randint(4, 80), r.randint(2, 6)
        return num(f"{v * t}kmを{t}時間で進んだ。速さは時速何kmか求めなさい。", v,
                   f"{v * t}÷{t}＝{v}(km/時)。")

    def speed_mmin(r):
        v, t = r.choice(range(40, 100, 5)), r.choice([5, 10, 12, 15, 20, 25, 30])
        return num(f"{v * t}mを{t}分で歩いた。速さは分速何mか求めなさい。", v,
                   f"{v * t}÷{t}＝{v}(m/分)。")

    def dist(r):
        v, t = r.randint(4, 90), r.randint(2, 7)
        return num(f"時速{v}kmで{t}時間進んだ。進んだ道のりを求めなさい。(km)", v * t,
                   f"{v}×{t}＝{v * t}(km)。")

    def dist_min(r):
        v, m = r.choice([12, 24, 36, 40, 48, 60, 72, 80]), r.choice([15, 30, 45, 20, 40])
        d = Fraction(v * m, 60)
        if d.denominator != 1:
            return None
        return num(f"時速{v}kmで{m}分進んだ。進んだ道のりを求めなさい。(km)", d,
                   f"{m}分＝{frac_str(Fraction(m, 60))}時間。{v}×{frac_str(Fraction(m, 60))}＝{fmt(d)}(km)。")

    def time_h(r):
        v, t = r.randint(4, 80), r.randint(2, 6)
        return num(f"{v * t}kmの道のりを時速{v}kmで進むと、何時間かかるか求めなさい。", t,
                   f"{v * t}÷{v}＝{t}(時間)。")

    def time_min(r):
        v, t = r.choice(range(40, 100, 10)), r.randint(10, 60)
        d = v * t
        if d % 100:
            return None
        return num(f"{fmt(Fraction(d, 1000))}kmの道のりを分速{v}mで歩くと、何分かかるか求めなさい。", t,
                   f"{fmt(Fraction(d, 1000))}km＝{d}m。{d}÷{v}＝{t}(分)。")

    return collect(rng, [speed_kmh, dist, time_h, speed_mmin, dist_min, time_min])


def t_percent(rng):
    def ratio_pct(r):
        n = r.choice([20, 25, 40, 50, 80, 120, 200, 250])
        p = r.randint(10, 19) * 5
        k = Fraction(n * p, 100)
        if k.denominator != 1:
            return None
        k = int(k)
        return num(f"定員{n}人のうち{k}人が出席した。出席した人の割合は何%か求めなさい。", p,
                   f"{k}÷{n}＝{fmt(Fraction(k, n))} → {p}%。")

    def ratio_pct2(r):
        n = r.choice([40, 50, 80, 200, 300, 400, 500])
        p = r.randint(1, 6) * 5
        k = n * p
        if k % 100:
            return None
        k //= 100
        return num(f"{n}本のくじのうち、当たりは{k}本ある。当たりの割合は何%か求めなさい。", p,
                   f"{k}÷{n}＝{fmt(Fraction(k, n))} → {p}%。")

    def discount(r):
        price = r.choice(range(200, 3001, 100))
        p = r.choice([10, 15, 20, 25, 30, 40, 50])
        d = Fraction(price * p, 100)
        if d.denominator != 1:
            return None
        return num(f"定価{price}円の品物を{p}%引きで買うと、何円安くなるか求めなさい。", d,
                   f"{price}×{fmt(Fraction(p, 100))}＝{fmt(d)}(円)。")

    def after_discount(r):
        price = r.choice(range(400, 5001, 100))
        p = r.choice([10, 20, 25, 30, 40])
        pay = Fraction(price * (100 - p), 100)
        if pay.denominator != 1:
            return None
        return num(f"定価{price}円の品物を{p}%引きで買った。代金は何円か求めなさい。", pay,
                   f"{price}×(1－{fmt(Fraction(p, 100))})＝{fmt(pay)}(円)。")

    def part(r):
        base = r.choice([200, 300, 400, 500, 600, 800, 1200])
        p = r.choice([5, 12, 15, 25, 30, 35, 45, 60, 75])
        k = Fraction(base * p, 100)
        if k.denominator != 1:
            return None
        return num(f"{base}gの{p}%は何gか求めなさい。", k,
                   f"{base}×{fmt(Fraction(p, 100))}＝{fmt(k)}(g)。")

    return collect(rng, [ratio_pct, discount, ratio_pct2, part, after_discount])


PAIRS = [("Aさん", "Bさん"), ("ゆうと", "さくら"), ("はると", "みお"), ("そうた", "ゆい")]
RATIOS = [(2, 3), (3, 2), (3, 4), (4, 3), (2, 5), (5, 3), (3, 5), (4, 5), (5, 4), (1, 3), (3, 1), (5, 2), (2, 7), (7, 3), (4, 7)]


def t_ratio_split(rng):
    def split_money(r):
        a, b = r.choice(RATIOS)
        unit = r.choice([50, 100, 150, 200, 300])
        tot = (a + b) * unit
        x, y = r.choice(PAIRS)
        big = x if a > b else y
        ans = max(a, b) * unit
        return num(f"{tot}円を{x}と{y}で{a}:{b}に分ける。{big}の分は何円か求めなさい。", ans,
                   f"{tot}×{max(a, b)}/{a + b}＝{ans}(円)。")

    def split_small(r):
        a, b = r.choice(RATIOS)
        unit = r.randint(2, 12)
        tot = (a + b) * unit
        ans = min(a, b) * unit
        return num(f"{tot}cmのリボンを長さの比が{a}:{b}になるように2本に切る。短い方は何cmか求めなさい。", ans,
                   f"{tot}×{min(a, b)}/{a + b}＝{ans}(cm)。")

    def split3(r):
        a, b, c = r.randint(1, 5), r.randint(1, 5), r.randint(1, 5)
        if len({a, b, c}) < 3:
            return None
        unit = r.choice([3, 4, 5, 6, 8, 10])
        tot = (a + b + c) * unit
        return num(f"{tot}個のあめをA、B、Cの3人で{a}:{b}:{c}に分ける。Cの分は何個か求めなさい。", c * unit,
                   f"{tot}×{c}/{a + b + c}＝{c * unit}(個)。")

    def ratio_use(r):
        a, b = r.randint(2, 7), r.randint(2, 9)
        if a >= b or Fraction(a, b).denominator != b:
            return None
        k = r.randint(2, 6)
        return num(f"たてとよこの長さの比が{a}:{b}の長方形がある。たてが{a * k}cmのとき、よこは何cmか求めなさい。",
                   b * k, f"{a * k}÷{a}＝{k}なので、よこは{b}×{k}＝{b * k}(cm)。")

    def ratio_use2(r):
        a, b = r.randint(1, 5), r.randint(2, 8)
        if a == b or Fraction(a, b).denominator != b:
            return None
        k = r.choice([20, 30, 40, 50, 60])
        return num(f"酢とサラダ油を{a}:{b}の比で混ぜてドレッシングを作る。サラダ油を{b * k}mL使うとき、酢は何mLか求めなさい。",
                   a * k, f"{b * k}÷{b}＝{k}なので、酢は{a}×{k}＝{a * k}(mL)。")

    return collect(rng, [split_money, split_small, split3, split_money, ratio_use, ratio_use2])


# ---------------------------------------------------------------- データ・統計

def t_mean(rng):
    def plain(r):
        n = r.randint(4, 7)
        xs = [r.randint(2, 30) for _ in range(n)]
        if sum(xs) % n:
            return None
        m = mean(xs)
        return num(f"{lst(xs)} の平均値を求めなさい。", m, f"合計{sum(xs)}÷{n}＝{fmt(m)}。")

    def scores(r):
        n = r.randint(4, 6)
        xs = [r.randint(50, 100) for _ in range(n)]
        if sum(xs) % n:
            return None
        m = mean(xs)
        return num(f"{n}回のテストの点数が {lst(xs)} (点)のとき、平均点を求めなさい。(点)", m,
                   f"合計{sum(xs)}÷{n}＝{fmt(m)}(点)。")

    def total(r):
        n, m = r.randint(3, 8), r.randint(55, 90)
        return num(f"{n}人のテストの平均点が{m}点のとき、{n}人の合計点を求めなさい。(点)", n * m,
                   f"{m}×{n}＝{n * m}(点)。")

    def next_score(r):
        n, m = r.randint(3, 5), r.randint(60, 85)
        target = m + r.randint(1, 4)
        need = target * (n + 1) - m * n
        if need > 100:
            return None
        return num(f"{n}回のテストの平均点は{m}点だった。{n + 1}回目で何点をとれば、{n + 1}回の平均点が{target}点になるか求めなさい。(点)",
                   need, f"{target}×{n + 1}－{m}×{n}＝{need}(点)。")

    def half(r):
        n = r.choice([4, 6])
        xs = [r.randint(1, 20) for _ in range(n)]
        m = mean(xs)
        if m.denominator != 2:
            return None
        return num(f"{lst(xs)} の平均値を求めなさい。", m, f"合計{sum(xs)}÷{n}＝{fmt(m)}。")

    return collect(rng, [plain, total, scores, next_score, plain, half])


def t_rel_freq(rng):
    def rel(r):
        n = r.choice([20, 25, 40, 50, 80, 100, 200])
        k = r.randint(1, n // 2)
        f = Fraction(k, n)
        if not short_decimal(f):
            return None
        return num(f"全体{n}人のうち、ある階級の度数が{k}人である。この階級の相対度数を求めなさい。", f,
                   f"{k}÷{n}＝{fmt(f)}。")

    def rel_count(r):
        n = r.choice([20, 25, 40, 50, 80])
        k = r.randint(1, n // 2)
        f = Fraction(k, n)
        if not short_decimal(f):
            return None
        return num(f"相対度数が{fmt(f)}の階級がある。度数の合計が{n}のとき、この階級の度数を求めなさい。", k,
                   f"{n}×{fmt(f)}＝{k}。")

    def rel_total(r):
        n = r.choice([20, 25, 40, 50, 80, 100])
        k = r.randint(2, n // 2)
        f = Fraction(k, n)
        if not short_decimal(f):
            return None
        return num(f"ある階級の度数が{k}、相対度数が{fmt(f)}である。度数の合計を求めなさい。", n,
                   f"{k}÷{fmt(f)}＝{n}。")

    return collect(rng, [rel, rel, rel_count, rel, rel_total])


def t_median_mode_range(rng):
    def med_odd(r):
        n = r.choice([5, 7])
        xs = [r.randint(1, 40) for _ in range(n)]
        m = median(xs)
        return num(f"{lst(xs)} の中央値を求めなさい。", m,
                   f"小さい順に {lst(sorted(xs))}。真ん中の値は{fmt(m)}。")

    def med_even(r):
        n = r.choice([6, 8])
        xs = [r.randint(1, 30) for _ in range(n)]
        s = sorted(xs)
        m = median(xs)
        a, b = s[n // 2 - 1], s[n // 2]
        return num(f"{lst(xs)} の中央値を求めなさい。", m,
                   f"小さい順に並べると真ん中の2つは{a}と{b}。({a}＋{b})÷2＝{fmt(m)}。")

    def rng_(r):
        n = r.randint(5, 7)
        xs = [r.randint(1, 60) for _ in range(n)]
        lo, hi = min(xs), max(xs)
        return num(f"{lst(xs)} の範囲を求めなさい。", hi - lo, f"最大値{hi}－最小値{lo}＝{hi - lo}。")

    def mode(r):
        n = r.randint(7, 8)
        xs = [r.randint(1, 10) for _ in range(n)]
        cnt = {x: xs.count(x) for x in xs}
        top = max(cnt.values())
        modes = [x for x, c in cnt.items() if c == top]
        if top < 2 or len(modes) != 1:
            return None
        return num(f"{lst(xs)} の最頻値を求めなさい。", modes[0],
                   f"{modes[0]}が{top}回で最も多いので、最頻値は{modes[0]}。")

    return collect(rng, [med_odd, rng_, mode, med_even])


def quartiles(xs):
    s = sorted(xs)
    n = len(s)
    lower, upper = s[: n // 2], s[(n + 1) // 2:]
    return median(lower), median(s), median(upper)


def t_quartile(rng):
    def data(r):
        n = r.randint(7, 8) if r.random() < 0.8 else r.choice([6, 9])
        return sorted(r.randint(1, 30) for _ in range(n))

    def pair(r):
        s = data(r)
        q1, q2, q3 = quartiles(s)
        n = len(s)
        alt1, alt3 = median(s[: (n + 1) // 2]), median(s[n // 2:])
        c = f"Q1={fmt(q1)}、Q3={fmt(q3)}"
        wrongs = [f"Q1={fmt(alt1)}、Q3={fmt(alt3)}", f"Q1={fmt(q1)}、Q3={fmt(q2)}",
                  f"Q1={fmt(q2)}、Q3={fmt(q3)}", f"Q1={s[0]}、Q3={s[-1]}"]
        wrongs = [w for w in dict.fromkeys(wrongs) if w != c]
        return choice(r, f"データ {lst(s)} の第1四分位数Q1と第3四分位数Q3を求めなさい。", c, wrongs,
                      f"中央値は{fmt(q2)}。前半の中央値がQ1＝{fmt(q1)}、後半の中央値がQ3＝{fmt(q3)}。")

    def q1(r):
        s = data(r)
        a, m, _ = quartiles(s)
        return num(f"データ {lst(s)} の第1四分位数を求めなさい。", a,
                   f"中央値{fmt(m)}より小さい側(前半) {lst(s[: len(s) // 2])} の中央値で{fmt(a)}。")

    def q3(r):
        s = data(r)
        _, m, c = quartiles(s)
        return num(f"データ {lst(s)} の第3四分位数を求めなさい。", c,
                   f"中央値{fmt(m)}より大きい側(後半) {lst(s[(len(s) + 1) // 2:])} の中央値で{fmt(c)}。")

    def iqr_data(r):
        s = data(r)
        a, _, c = quartiles(s)
        if a == c:
            return None
        return num(f"データ {lst(s)} の四分位範囲を求めなさい。", c - a,
                   f"Q1＝{fmt(a)}、Q3＝{fmt(c)}。{fmt(c)}－{fmt(a)}＝{fmt(c - a)}。")

    def iqr_given(r):
        a = r.randint(2, 40)
        c = a + r.randint(3, 30)
        return num(f"第1四分位数が{a}、第3四分位数が{c}のとき、四分位範囲を求めなさい。", c - a,
                   f"{c}－{a}＝{c - a}。")

    return collect(rng, [pair, q1, iqr_given, q3, iqr_data, pair])


def pick_data(r, n_choices, lo, hi, cond):
    for _ in range(20000):
        n = r.choice(n_choices)
        xs = [r.randint(lo, hi) for _ in range(n)]
        if len(set(xs)) >= 3 and mean(xs).denominator == 1 and cond(xs):
            return xs
    return None


def var_explain(xs):
    m = mean(xs)
    ss = sum((x - m) ** 2 for x in xs)
    return f"平均{fmt(m)}、偏差の2乗の和{fmt(ss)}。{fmt(ss)}÷{len(xs)}＝{fmt(ss / len(xs))}。"


def t_variance(rng):
    def data_var(r):
        xs = pick_data(r, [4, 5, 5, 6], 1, 15, lambda xs: short_decimal(variance(xs), 1))
        if xs is None:
            return None
        return num(f"データ {lst(xs)} の分散を求めなさい。", variance(xs), var_explain(xs))

    def from_sq_mean(r):
        m, v = r.randint(2, 12), r.randint(1, 16)
        sq = m * m + v
        return num(f"あるデータの平均値が{m}、データの2乗の平均値が{sq}のとき、分散を求めなさい。", v,
                   f"分散＝(2乗の平均)－(平均)²＝{sq}－{m * m}＝{v}。")

    def from_sd(r):
        s = r.randint(2, 15)
        return num(f"標準偏差が{s}であるデータの分散を求めなさい。", s * s, f"分散＝(標準偏差)²＝{s}²＝{s * s}。")

    return collect(rng, [data_var, data_var, from_sq_mean, data_var, from_sd])


def t_stdev(rng):
    def from_var(r):
        s = r.randint(2, 15)
        return num(f"分散が{s * s}であるデータの標準偏差を求めなさい。", s, f"√{s * s}＝{s}。")

    def from_var_dec(r):
        s = Fraction(r.randint(11, 49), 10)
        if s.denominator == 1:
            return None
        return num(f"分散が{fmt(s * s)}であるデータの標準偏差を求めなさい。", s,
                   f"{fmt(s)}²＝{fmt(s * s)}なので、√{fmt(s * s)}＝{fmt(s)}。")

    def data_sd(r):
        xs = pick_data(r, [4, 5, 6], 1, 20,
                       lambda xs: (sd := frac_sqrt(variance(xs))) is not None and sd > 0 and short_decimal(sd, 1))
        if xs is None:
            return None
        v = variance(xs)
        sd = frac_sqrt(v)
        m = mean(xs)
        ss = sum((x - m) ** 2 for x in xs)
        return num(f"データ {lst(xs)} の標準偏差を求めなさい。", sd,
                   f"平均{fmt(m)}、分散は{fmt(ss)}÷{len(xs)}＝{fmt(v)}。√{fmt(v)}＝{fmt(sd)}。")

    return collect(rng, [data_sd, from_var, data_sd, from_var_dec, data_sd])


CORR_LABELS = ["強い正の相関がある", "弱い正の相関がある", "ほとんど相関がない", "弱い負の相関がある", "強い負の相関がある"]


def t_correlation(rng):
    def judge(r):
        r_ = r.choice([0.8, 0.85, 0.9, 0.95, -0.8, -0.85, -0.9, -0.95, 0.3, -0.3, 0.25, -0.25,
                       0.35, -0.35, 0.02, -0.03, 0.05, -0.05])
        a = abs(r_)
        idx = 2 if a < 0.1 else (1 if a < 0.4 else 0)
        if idx != 2 and r_ < 0:
            idx = 4 - idx
        correct = CORR_LABELS[idx]
        wrongs = [x for x in CORR_LABELS if x != correct]
        r.shuffle(wrongs)
        # 符号を取り違えたものは必ず入れる
        mirror = CORR_LABELS[4 - idx]
        if mirror != correct:
            wrongs.remove(mirror)
            wrongs.insert(0, mirror)
        return choice(r, f"2つの数量x、yの相関係数が{r_}であるとき、xとyの関係として最も適切なものを選びなさい。",
                      correct, wrongs,
                      (f"0に近いので、ほとんど相関がない。" if idx == 2 else
                       f"符号が{'正' if r_ > 0 else '負'}で、絶対値{a}は{'1に近いので強い相関' if idx in (0, 4) else '0.2〜0.4程度なので弱い相関'}。"))

    def from_cov(r):
        sx, sy = r.randint(2, 9), r.randint(2, 9)
        rv = Fraction(r.choice([-9, -8, -7, -6, -5, -4, -3, 3, 4, 5, 6, 7, 8, 9]), 10)
        cov = rv * sx * sy
        if cov.denominator != 1:
            return None
        return num(f"xの標準偏差が{sx}、yの標準偏差が{sy}、xとyの共分散が{fmt(cov)}のとき、相関係数を求めなさい。",
                   rv, f"{fmt(cov)}÷({sx}×{sy})＝{fmt(rv)}。")

    def from_data(r):
        for _ in range(20000):
            xs = [r.randint(1, 9) for _ in range(5)]
            ys = [r.randint(1, 9) for _ in range(5)]
            if len(set(xs)) < 4 or len(set(ys)) < 4:
                continue
            mx, my = mean(xs), mean(ys)
            if mx.denominator != 1 or my.denominator != 1:
                continue
            sxx = sum((x - mx) ** 2 for x in xs)
            syy = sum((y - my) ** 2 for y in ys)
            sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            root = frac_sqrt(sxx * syy)
            if root is None or root == 0:
                continue
            rv = sxy / root
            if abs(rv) < Fraction(3, 10) or abs(rv) == 1 or not short_decimal(rv, 1):
                continue
            return num(f"次の5組のデータの相関係数を求めなさい。\nx: {lst(xs)}\ny: {lst(ys)}", rv,
                       f"偏差の積の和{fmt(sxy)}、xの偏差の2乗の和{fmt(sxx)}、yは{fmt(syy)}。"
                       f"{fmt(sxy)}÷√({fmt(sxx)}×{fmt(syy)})＝{fmt(rv)}。")
        return None

    return collect(rng, [judge, from_cov, judge, from_data, judge])


GENERATORS = {
    "math-quantity-ratio-percent-003": t_rect_area,
    "math-quantity-ratio-percent-004": t_tri_quad_area,
    "math-quantity-ratio-percent-005": t_circle_area,
    "math-quantity-ratio-percent-007": t_box_volume,
    "math-quantity-ratio-percent-008": t_prism_volume,
    "math-quantity-ratio-percent-010": t_speed,
    "math-quantity-ratio-percent-011": t_percent,
    "math-quantity-ratio-percent-013": t_ratio_split,
    "math-data-statistics-005": t_mean,
    "math-data-statistics-009": t_rel_freq,
    "math-data-statistics-010": t_median_mode_range,
    "math-data-statistics-011": t_quartile,
    "math-data-statistics-014": t_variance,
    "math-data-statistics-015": t_stdev,
    "math-data-statistics-017": t_correlation,
}
