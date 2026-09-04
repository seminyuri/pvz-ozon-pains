#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генерирует ТОЛЬКО фрагменты с данными. Проза страниц написана руками.

  python3 gen.py <pvz_full.json> <seller_year.json> <ideas.json> <fragments_dir>

На выходе — набор .html-кусков и stats.json с числами, которые подставляются в
рукописный текст. Разделение намеренное: машина считает и рисует, человек пишет.
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from products import ЛИНИИ, линии_темы  # noqa: E402

МЕСЯЦЫ = {"01": "янв", "02": "фев", "03": "мар", "04": "апр", "05": "май",
          "06": "июн", "07": "июл", "08": "авг", "09": "сен", "10": "окт",
          "11": "ноя", "12": "дек"}
_ЧИСЛА = re.compile(r"\d{7,}")


def мес(ym):
    г, м = ym.split("-")
    return f"{МЕСЯЦЫ[м]} {г[2:]}"


def esc(s):
    return html.escape(str(s), quote=True)


def цитата(s):
    """Номера претензий и отправлений маскируем — сайт публичный."""
    return esc(_ЧИСЛА.sub(lambda m: m.group(0)[:2] + "·" * 4 + m.group(0)[-2:], str(s)))


def тыс(n):
    return f"{n:,}".replace(",", " ")


def автор(имя):
    """На публичном сайте фамилию сокращаем до буквы.

    Цитаты нужны ради текстуры живой речи, а не ради указания на человека. Имя
    оставляем — без него реплика теряет голос, — а всё, что идёт после первого
    слова, сжимаем до инициала. Ники и односложные имена не трогаем.
    """
    части = str(имя).split()
    if len(части) < 2:
        return имя
    хвост = [ч[0].upper() + "." for ч in части[1:] if ч and ч[0].isalpha()]
    return " ".join([части[0]] + хвост[:1]) if хвост else части[0]


def спарк(ряд, ширина=132, высота=30):
    if not ряд or len(ряд) < 2 or max(ряд) == 0:
        return ""
    мx = max(ряд)
    шаг = ширина / (len(ряд) - 1)
    xy = [(i * шаг, высота - (v / мx) * (высота - 5) - 2.5) for i, v in enumerate(ряд)]
    линия = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    return (f'<svg class="spark" viewBox="0 0 {ширина} {высота}" '
            f'preserveAspectRatio="none" aria-hidden="true">'
            f'<polygon points="0,{высота} {линия} {ширина},{высота}" class="spark-fill"/>'
            f'<polyline points="{линия}" class="spark-line"/>'
            f'<circle cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="2.4" class="spark-dot"/>'
            f'</svg>')


def столбцы(пары, ширина=1000, высота=232):
    мx = max(v for _, v in пары) or 1
    w = ширина / len(пары)
    ч = []
    for i, (подпись, v) in enumerate(пары):
        h = (v / мx) * (высота - 46)
        x, bw = i * w + w * 0.17, w * 0.66
        y = высота - 26 - h
        ч.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" class="bar"/>')
        ч.append(f'<text x="{x + bw / 2:.1f}" y="{высота - 9}" text-anchor="middle" class="lbl">{esc(подпись)}</text>')
        ч.append(f'<text x="{x + bw / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" class="val">{тыс(v)}</text>')
    return (f'<svg viewBox="0 0 {ширина} {высота}" class="chart" role="img" '
            f'aria-label="сообщений в месяц">{"".join(ч)}</svg>')


def факт(число, подпись, сноска=""):
    доп = f"<small>{сноска}</small>" if сноска else ""
    return (f'<div class="fact"><div class="fact-n">{число}</div>'
            f'<div class="fact-l">{подпись}{доп}</div></div>')


def тренд(ряд_отн):
    """Куда тема поехала: первый месяц против последнего ПОЛНОГО.

    Ряд сюда приходит уже без обрезанного границей выгрузки месяца — иначе
    процент и нарисованная линия рассказывали бы разные истории.
    """
    if len(ряд_отн) < 3 or ряд_отн[0] < 0.3:
        return ""
    было, стало = ряд_отн[0], ряд_отн[-1]
    д = (стало - было) / было * 100
    сл, кл = ("растёт", "up") if д > 15 else (("угасает", "down") if д < -15 else ("ровно", "flat"))
    return f'<span class="trend {кл}">{сл} {д:+.0f}%</span>'


def main():
    pvz = json.load(open(sys.argv[1], encoding="utf-8"))
    seller = json.load(open(sys.argv[2], encoding="utf-8"))
    ideas = json.load(open(sys.argv[3], encoding="utf-8"))
    out = sys.argv[4]
    os.makedirs(out, exist_ok=True)

    def пиши(имя, текст):
        open(os.path.join(out, имя), "w", encoding="utf-8").write(текст)

    темы = [t for t in pvz["темы"] if t["msgs"] > 0]
    максимум = темы[0]["msgs"]
    помесячно = pvz["помесячно_всего"]
    # Последний месяц обрезан датой выгрузки: в нём всего несколько дней.
    # Выкидываем его из всех рядов, иначе спарклайн падает на ровном месте,
    # а процент изменения считается по огрызку.
    ключи = list(помесячно)[:-1]

    # ── плитки чисел ──────────────────────────────────────────────────────
    пиши("facts_main.html", "".join([
        факт(тыс(pvz["всего_сообщений"]), "сообщений выгружено"),
        факт(тыс(pvz["содержательных"]), "содержательных"),
        факт(тыс(pvz["авторов"]), "разных авторов"),
        факт(тыс(pvz["дней"]), "дней подряд"),
        факт(тыс(pvz["вопросов"]), "из них вопросы"),
        факт(тыс(len(темы)), "выделено тем"),
    ]))

    # ── пульс ─────────────────────────────────────────────────────────────
    пиши("chart_pulse.html",
         '<div class="chartwrap">'
         + столбцы([(мес(k), v) for k, v in помесячно.items()][1:-1])
         + "</div>")

    # ── зонты ─────────────────────────────────────────────────────────────
    зонты = pvz.get("зонты", [])
    мz = max((z["msgs"] for z in зонты), default=1)
    пиши("umbrellas.html", '<div class="umbrellas">' + "".join(
        f'<div class="umb">'
        f'<div class="umb-name">{esc(z["имя"])}<small>{esc(z["раздел"])} · '
        f'{z["тем_внутри"]} подробных тем</small></div>'
        f'<span class="track"><span class="fill" style="width:{z["msgs"] / мz * 100:.0f}%"></span></span>'
        f'<span class="n">{тыс(z["msgs"])}<small>сообщений</small></span>'
        f'<span class="n">{тыс(z["authors"])}<small>человек</small></span>'
        f'<span class="n">{z["доля_боли"] * 100:.0f}%<small>боль</small></span>'
        f'</div>' for z in зонты) + "</div>")

    # ── топ-15 ────────────────────────────────────────────────────────────
    пиши("top15.html", '<ol class="top15">' + "".join(
        f'<li><span class="t">{esc(t["тема"])}</span>'
        f'<span class="track"><span class="fill" style="width:{t["msgs"] / максимум * 100:.0f}%"></span></span>'
        f'<span class="n">{тыс(t["msgs"])}</span>'
        f'<span class="n dim">{тыс(t["authors"])} чел.</span></li>'
        for t in темы[:15]) + "</ol>")

    # ── что разгорается, а что прошло ─────────────────────────────────────
    # Считаем по НОРМИРОВАННОЙ доле: в штуках падает всё, потому что чат за
    # период сжался вдвое. Сравниваем первый месяц с предпоследним — последний
    # обрезан границей выгрузки.
    движение = []
    for t in темы:
        if t["msgs"] < 80:
            continue
        r = [1000 * t["помесячно"].get(k, 0) / помесячно[k] if помесячно[k] else 0
             for k in ключи]
        if len(r) < 3 or r[0] < 0.3:
            continue
        движение.append(((r[-1] - r[0]) / r[0] * 100, t, r))
    движение.sort(key=lambda x: -x[0])

    def плитка_движения(д, t, r):
        знак = "up" if д > 0 else "down"
        return (f'<li><span class="t">{esc(t["тема"])}'
                f'<span class="sect">{esc(t.get("раздел", ""))}</span></span>'
                f'<span class="sparkwrap">{спарк(r)}</span>'
                f'<span class="trend {знак}">{д:+.0f}%</span>'
                f'<span class="n dim">{тыс(t["authors"])} чел.</span></li>')

    пиши("trends.html",
         '<div class="two-cols">'
         '<div><h3 class="colh">Разгорается</h3><ol class="movers">'
         + "".join(плитка_движения(*x) for x in движение[:10])
         + '</ol></div><div><h3 class="colh">Уже прошло</h3><ol class="movers">'
         + "".join(плитка_движения(*x) for x in движение[-10:][::-1])
         + "</ol></div></div>")

    # ── все темы ──────────────────────────────────────────────────────────
    разделы = []
    for t in темы:
        if t.get("раздел") and t["раздел"] not in разделы:
            разделы.append(t["раздел"])
    пиши("filters.html", '<div class="filters">'
         '<button type="button" data-filter="" class="on">все разделы</button>'
         + "".join(f'<button type="button" data-filter="{esc(r)}">{esc(r)}</button>'
                   for r in разделы) + "</div>")

    строки = []
    for i, t in enumerate(темы, 1):
        ряд = [1000 * t["помесячно"].get(k, 0) / помесячно[k] if помесячно[k] else 0
               for k in ключи]
        линии = [k for k in линии_темы(t["тема"], t.get("раздел", "")) if k in ЛИНИИ]
        чипы = "".join(f'<a class="chip" href="money.html#{k}">{esc(ЛИНИИ[k]["имя"])}</a>'
                       for k in линии)
        цитаты = "".join(
            f'<blockquote><p>{цитата(q["t"])}</p>'
            f'<cite>{esc(автор(q["a"]))} · {esc(q["d"])}</cite></blockquote>'
            for q in t["цитаты"][:4])
        доля_авт = t["authors"] / pvz["авторов"] * 100
        строки.append(f"""
<details class="row" id="t-{i}" data-section="{esc(t.get('раздел', ''))}">
  <summary>
    <span class="rank">{i:03d}</span>
    <span class="name">{esc(t['тема'])}<span class="sect">{esc(t.get('раздел', ''))}</span></span>
    <span class="track"><span class="fill" style="width:{t['msgs'] / максимум * 100:.1f}%"></span></span>
    <span class="num">{тыс(t['msgs'])}</span>
    <span class="num dim">{тыс(t['authors'])}</span>
    <span class="num dim">{t['доля_боли'] * 100:.0f}%</span>
    <span class="sparkwrap">{спарк(ряд)}</span>
  </summary>
  <div class="detail">
    <div class="metrics">
      {факт(тыс(t['msgs']), 'упоминаний')}
      {факт(тыс(t['authors']), 'разных людей', f'{доля_авт:.0f}% активных')}
      {факт(f"{t['доля_боли'] * 100:.0f}%", 'доля боли', f"{тыс(t['pain'])} сообщений")}
      {факт(тыс(t['деньги']), 'рядом с потерей денег')}
    </div>
    <div class="lines"><span class="lines-l">закрывается</span>{чипы}{тренд(ряд)}</div>
    {цитаты or '<p class="note">Живых цитат по этой теме не нашлось: тема редкая, и все подходящие реплики ушли в более крупные темы.</p>'}
  </div>
</details>""")
    пиши("rows.html", '<div id="rows">' + "".join(строки) + "</div>")

    # ── линии продуктов ───────────────────────────────────────────────────
    по_линиям = {}
    for t in темы:
        for k in линии_темы(t["тема"], t.get("раздел", "")):
            по_линиям.setdefault(k, []).append((t["тема"], t["msgs"]))
    карточки = []
    for k, л in sorted(ЛИНИИ.items(),
                       key=lambda kv: -sum(m for _, m in по_линиям.get(kv[0], []))):
        внутри = sorted(по_линиям.get(k, []), key=lambda x: -x[1])
        вес = sum(m for _, m in внутри)
        звёзды = "".join("<i" + (" class=on" if j < л["рычаг"] else "") + "></i>"
                         for j in range(5))
        карточки.append(f"""
<article class="line" id="{k}">
  <header>
    <h3>{esc(л['имя'])}</h3>
    <div class="line-meta">
      <span class="sc-l">рычаг</span><span class="sc-bar">{звёзды}</span>
      <span class="sc-l">первые деньги</span><b>{esc(л['скорость'])}</b>
    </div>
  </header>
  <p class="pitch">{esc(л['суть'])}</p>
  <dl class="kv">
    <div><dt>кто платит</dt><dd>{esc(л['платит'])}</dd></div>
    <div><dt>модель</dt><dd>{esc(л['модель'])}</dd></div>
    <div><dt>вес закрываемых болей</dt><dd>{тыс(вес)} упоминаний в {len(внутри)} темах</dd></div>
  </dl>
  <div class="covers"><span class="lines-l">закрывает боли</span>
    <ul>{''.join(f'<li>{esc(n)}<b>{тыс(m)}</b></li>' for n, m in внутри[:10])}</ul></div>
</article>""")
    пиши("lines.html", '<div class="lines-grid">' + "".join(карточки) + "</div>")

    # ── сигналы рынка ─────────────────────────────────────────────────────
    пиши("signals.html", '<div class="signals">' + "".join(
        f'<div class="signal"><div class="sig-head">'
        f'<span class="sig-n">{тыс(r["msgs"])}</span>'
        f'<span class="sig-a">{тыс(r["authors"])} чел.</span></div>'
        f'<h4>{esc(r["сигнал"])}</h4>'
        + "".join(f'<p class="q">{цитата(q["t"][:230])}</p>' for q in r["примеры"][:2])
        + "</div>" for r in pvz["рынок"]) + "</div>")

    # ── идеи ──────────────────────────────────────────────────────────────
    пиши("ideas.html", '<div class="ideas">' + "".join(f"""
<article class="idea">
  <header><span class="letter">{esc(x['метка'])}</span>
    <div><h3>{esc(x['имя'])}</h3><p class="pitch">{esc(x['суть'])}</p></div>
  </header>
  <div class="scores">
    {''.join(f'<div class="sc"><span class="sc-l">{esc(k)}</span><span class="sc-bar">'
             + "".join("<i" + (" class=on" if j < v else "") + "></i>" for j in range(5))
             + "</span></div>" for k, v in x['оценки'].items())}
    <div class="sc"><span class="sc-l">итог</span><b>{sum(x['оценки'].values())}/25</b></div>
  </div>
  <dl class="kv">
    <div><dt>кто платит</dt><dd>{esc(x['платит'])}</dd></div>
    <div><dt>за что</dt><dd>{esc(x['за_что'])}</dd></div>
    <div><dt>технологично</dt><dd>{esc(x['технология'])}</dd></div>
    <div><dt>первые деньги</dt><dd>{esc(x['первые_деньги'])}</dd></div>
    <div><dt>риск</dt><dd>{esc(x['риск'])}</dd></div>
  </dl>
  <div class="basis"><span class="lines-l">основание в корпусе</span>
    <p>{esc(x['основание'])}</p></div>
</article>""" for x in ideas["идеи"]) + "</div>")

    # ── селлеры ───────────────────────────────────────────────────────────
    пиши("sellers_facts.html", "".join([
        факт(тыс(seller["всего_сообщений"]), "сообщений"),
        факт(тыс(seller["содержательных"]), "содержательных"),
        факт(тыс(seller["авторов"]), "авторов"),
        факт(тыс(seller["дней"]), "дней"),
        факт(тыс(seller["вопросов"]), "вопросов"),
    ]))
    пиши("sellers_table.html", '<div class="tablewrap"><table>'
         '<thead><tr><th>тема</th><th class="n">упом.</th><th class="n">людей</th>'
         '<th class="n">доля боли</th></tr></thead><tbody>' + "".join(
             f'<tr><td>{esc(t["тема"])}</td><td class="n">{тыс(t["msgs"])}</td>'
             f'<td class="n">{тыс(t["authors"])}</td>'
             f'<td class="n">{t["доля_боли"] * 100:.0f}%</td></tr>'
             for t in seller["темы"]) + "</tbody></table></div>")

    # ── числа для рукописного текста ──────────────────────────────────────
    имена = {t["тема"]: t for t in темы}
    json.dump({
        "всего": тыс(pvz["всего_сообщений"]),
        "содержательных": тыс(pvz["содержательных"]),
        "авторов": тыс(pvz["авторов"]),
        "дней": тыс(pvz["дней"]),
        "вопросов": тыс(pvz["вопросов"]),
        "тем": тыс(len(темы)),
        "с": pvz["период"][0], "по": pvz["период"][1],
        "селлеры_всего": тыс(seller["всего_сообщений"]),
        "селлеры_авторов": тыс(seller["авторов"]),
        "селлеры_дней": тыс(seller["дней"]),
        "селлеры_с": seller["период"][0], "селлеры_по": seller["период"][1],
        "селлеры_тем": тыс(len(seller["темы"])),
        "линий": тыс(len(ЛИНИИ)),
        "зонты": {z["раздел"]: {"msgs": тыс(z["msgs"]), "чел": тыс(z["authors"]),
                                "боль": f'{z["доля_боли"] * 100:.0f}%'}
                  for z in зонты},
        "темы": {n: {"msgs": тыс(t["msgs"]), "чел": тыс(t["authors"]),
                     "боль": f'{t["доля_боли"] * 100:.0f}%'}
                 for n, t in имена.items()},
    }, open(os.path.join(out, "stats.json"), "w", encoding="utf-8"),
        ensure_ascii=False, indent=1)

    print("фрагменты:", ", ".join(sorted(os.listdir(out))))


main()
