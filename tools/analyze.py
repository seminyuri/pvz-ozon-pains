#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор корпуса: частота тем, авторы, помесячная динамика, цитаты.

  python3 analyze.py clean.jsonl [--since 2025-09-04] [--out отчёт.json]
"""
import argparse
import collections
import json
import re
import sys

import importlib, os
МОД = importlib.import_module(os.environ.get("THEMES", "themes"))
ТЕМЫ, БОЛЬ = МОД.ТЕМЫ, МОД.БОЛЬ
ДЕНЬГИ = getattr(МОД, "ДЕНЬГИ", [])

СЛУЖЕБНОЕ = re.compile(
    r"^(https?://\S+\s*)+$|^[\s\W\d]*$", re.I)


def собрать(patterns):
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I | re.U)


# Тема описывается парой (имя, регулярки) либо тройкой (имя, раздел, регулярки).
def _разобрать(t):
    return (t[0], t[1], t[2]) if len(t) == 3 else (t[0], "", t[1])


ТЕМА_RE = [(имя, раздел, собрать(ps)) for имя, раздел, ps in map(_разобрать, ТЕМЫ)]
БОЛЬ_RE = собрать(БОЛЬ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--since", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quotes", type=int, default=12)
    ap.add_argument("--min-len", type=int, default=12)
    a = ap.parse_args()

    msgs = []
    for line in open(a.src, encoding="utf-8"):
        m = json.loads(line)
        if a.since and m["d"] < a.since:
            continue
        msgs.append(m)

    содержательные = [m for m in msgs
                      if len(m["t"].strip()) >= a.min_len
                      and not СЛУЖЕБНОЕ.match(m["t"].strip())]

    # ── кто вещает, а кто разговаривает ───────────────────────────────────
    # Админы и каналы льют в чат длинные новости. В счёт темы они идут (это
    # тоже повестка), а в ЦИТАТЫ — нет: цитата должна быть голосом владельца
    # ПВЗ, а не пресс-релизом. Признак вещателя выводим из данных, а не из
    # списка имён: медианная длина сообщения выше 500 знаков.
    по_авторам = collections.defaultdict(list)
    for m in содержательные:
        по_авторам[m["a"]].append(len(m["t"]))
    # Аккаунты-рупоры: канал чата, боты, модерация. Их реплики — не голос
    # владельца ПВЗ, а вещание, и в цитаты они попадать не должны.
    # Пишем узко: имя владельца ПВЗ вполне может содержать «Озон», и вычёркивать
    # такого человека нельзя — вычёркиваем только явные служебные аккаунты.
    РУПОР = re.compile(r"^\W*(клуб партн|uma\b|.*\buma$|модератор|moderator|"
                       r"admin|админ|daysandbox|.*bot$|.*бот$)", re.I)
    вещатели = {a for a in по_авторам if РУПОР.search(a)}
    for автор, длины in по_авторам.items():
        if len(длины) < 4:
            continue
        доля_лонгридов = sum(1 for x in длины if x > 400) / len(длины)
        if доля_лонгридов >= 0.5:
            вещатели.add(автор)

    def годна_в_цитату(m):
        return (m["a"] not in вещатели and 60 <= len(m["t"]) <= 700
                and not re.search(r"https?://\S+.*https?://", m["t"]))

    занято = set()  # реплика, ушедшая в одну тему, во вторую не попадёт

    def отобрать(пул, сколько, rx=None):
        """Характерные для темы реплики: тема — предмет сообщения, а не помарка.

        Длина в отборе не главное. Длинное сообщение задевает десяток тем сразу
        и в цитатах выглядит одинаково везде — поэтому сортируем по плотности
        попаданий и держим размер около короткого живого вопроса.
        """
        кандидаты = [x for x in пул if годна_в_цитату(x) and x["id"] not in занято]

        def вес(m):
            попаданий = len(rx.findall(m["t"])) if rx else 1
            штраф_длины = abs(len(m["t"]) - 190) / 260
            рано = 1.0 if (rx and rx.search(m["t"][:140])) else 0.0
            return попаданий * 1.6 + рано - штраф_длины

        видели, отбор = set(), []
        for m in sorted(кандидаты, key=вес, reverse=True):
            if m["a"] in видели:
                continue
            видели.add(m["a"])
            занято.add(m["id"])
            отбор.append({"d": m["d"], "a": m["a"], "t": m["t"]})
            if len(отбор) >= сколько:
                break
        return отбор

    итог = []
    боль_по_теме = {}
    for имя, раздел, rx in ТЕМА_RE:
        hits = [m for m in содержательные if rx.search(m["t"])]
        pain = [m for m in hits if БОЛЬ_RE.search(m["t"])]
        помесячно = collections.Counter(m["d"][:7] for m in hits)
        авторы = collections.Counter(m["a"] for m in hits)
        боль_по_теме[имя] = (pain, rx)
        отбор = []
        итог.append({
            "тема": имя,
            "раздел": раздел,
            "msgs": len(hits),
            "authors": len(авторы),
            "pain": len(pain),
            "доля_боли": round(len(pain) / len(hits), 3) if hits else 0,
            "помесячно": dict(sorted(помесячно.items())),
            "топ_авторов": авторы.most_common(5),
            "цитаты": отбор,
        })

    итог.sort(key=lambda x: -x["msgs"])

    # Цитаты выбираем ПОСЛЕ сортировки: крупная тема забирает свои реплики
    # первой, мелкой достаются уже её собственные, а не общие «многотемные».
    for t in итог:
        pain, rx = боль_по_теме[t["тема"]]
        t["цитаты"] = отобрать(pain, a.quotes, rx)

    # ── сколько тема стоит: рядом ли с потерей денег ───────────────────────
    # Ключевых слов самих тем здесь быть НЕ должно: иначе тема «штрафы» считает
    # сама себя и колонка показывает 100% по построению, а не по факту.
    ДЕНЬГИ_RE = собрать([r"удержал", r"списал\w* деньг", r"вычл", r"компенсац",
                         r"убыт", r"\d[\d ]*\s?(руб|₽|тыс|т\.р\b)",
                         r"\d+\s?к\b(?!\w)", r"не заплат", r"потер\w+ деньг"])
    for t in итог:
        rx = {и: r for и, _, r in ТЕМА_RE}[t["тема"]]
        t["деньги"] = sum(1 for m in содержательные
                          if rx.search(m["t"]) and ДЕНЬГИ_RE.search(m["t"]))

    # ── где уже ходят деньги ──────────────────────────────────────────────
    рынок = []
    for имя, ps in ДЕНЬГИ:
        rx = собрать(ps)
        hits = [m for m in содержательные if rx.search(m["t"])]
        прим = отобрать(hits, 15)
        рынок.append({"сигнал": имя, "msgs": len(hits),
                      "authors": len({m["a"] for m in hits}), "примеры": прим})

    # ── вопросы: что спрашивают чаще всего ────────────────────────────────
    вопросы = [m for m in содержательные
               if "?" in m["t"] or re.search(r"подскажите|помогите|кто знает|кто сталкивал",
                                             m["t"], re.I)]

    дни = sorted({m["d"] for m in msgs if m["d"]})
    сводка = {
        "всего_сообщений": len(msgs),
        "содержательных": len(содержательные),
        "период": [дни[0], дни[-1]] if дни else [],
        "дней": len(дни),
        "авторов": len({m["a"] for m in msgs}),
        "помесячно_всего": dict(sorted(collections.Counter(
            m["d"][:7] for m in msgs if m["d"]).items())),
        "вопросов": len(вопросы),
        "темы": итог,
        "рынок": рынок,
    }
    if a.out:
        json.dump(сводка, open(a.out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    print(f"{сводка['всего_сообщений']} сообщений "
          f"({сводка['содержательных']} содержательных), "
          f"{сводка['период'][0]}..{сводка['период'][-1]}, "
          f"{сводка['дней']} дней, {сводка['авторов']} авторов")
    print(f"вопросов (с '?' или «подскажите»): {len(вопросы)}")
    print(f"{'#':>4} {'тема':<56} {'раздел':<14} {'msgs':>6} {'авт':>5} {'%боли':>6} {'₽':>5}")
    for i, t in enumerate(итог, 1):
        print(f"{i:>4} {t['тема'][:54]:<56} {t.get('раздел', ''):<14} {t['msgs']:>6} "
              f"{t['authors']:>5} {t['доля_боли'] * 100:>5.0f}% {t['деньги']:>5}")
    print("\nГДЕ УЖЕ ХОДЯТ ДЕНЬГИ")
    for r in рынок:
        print(f"  {r['сигнал']:<40} {r['msgs']:>6} сообщ. / {r['authors']:>4} авторов")


main()
