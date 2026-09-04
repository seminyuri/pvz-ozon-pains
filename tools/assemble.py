#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собрать сайт: рукописные страницы + фрагменты с данными.

  python3 assemble.py <pages_dir> <fragments_dir> <out_dir>

Страница в pages/ — это тело, написанное руками, с двумя видами подстановок:
  {{имя}}      — вставить фрагмент fragments/имя.html
  [[путь]]     — подставить число из fragments/stats.json (например [[авторов]]
                 или [[зонты.претензии.msgs]])
Первая строка файла — метаданные в JSON внутри комментария.
"""
import json
import os
import re
import shutil
import sys

НАВ = [("index.html", "Обзор"), ("pains.html", "Все боли"),
       ("money.html", "Где деньги"), ("sellers.html", "Селлеры"),
       ("method.html", "Методика")]

ОБОЛОЧКА = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{титул}</title>
<meta name="description" content="{описание}">
<meta property="og:title" content="{титул}">
<meta property="og:description" content="{описание}">
<meta property="og:type" content="article">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="assets/site.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.92em%22 font-size=%2292%22>📦</text></svg>">
<script>
  /* Тему ставим до отрисовки, иначе тёмная страница мигнёт белым. */
  (function () {{
    try {{ var t = localStorage.getItem('theme');
           if (t) document.documentElement.setAttribute('data-theme', t); }} catch (e) {{}}
  }})();
</script>
</head>
<body>
<header class="top">
  <a class="brand" href="index.html"><span class="mark">ПВЗ</span>исследование болей</a>
  <nav>{нав}</nav>
  <button id="theme" type="button" aria-label="Переключить тему">☾</button>
</header>
<main class="wrap">
<div class="pagehead">
  <h1>{заголовок}</h1>
  <p class="sub">{подзаголовок}</p>
</div>
{тело}
</main>
<footer class="foot">
  <p>Исследование построено на сплошной выгрузке открытого Telegram-форума
  владельцев ПВЗ Ozon. Цитаты приведены дословно, номера претензий и отправлений
  замаскированы. Метод и оговорки — на странице <a href="method.html">Методика</a>.
  Сентябрь 2026.</p>
</footer>
<script src="assets/site.js"></script>
</body>
</html>
"""


def достать(данные, путь):
    узел = данные
    for ключ in путь.split("."):
        узел = узел[ключ]
    return узел


def main():
    pages, frags, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(os.path.join(out, "assets"), exist_ok=True)
    здесь = os.path.dirname(os.path.abspath(__file__))
    for f in ("site.css", "site.js"):
        shutil.copy(os.path.join(здесь, "assets", f), os.path.join(out, "assets", f))
    open(os.path.join(out, ".nojekyll"), "w").close()

    stats = json.load(open(os.path.join(frags, "stats.json"), encoding="utf-8"))
    куски = {}
    for имя in os.listdir(frags):
        if имя.endswith(".html"):
            куски[имя[:-5]] = open(os.path.join(frags, имя), encoding="utf-8").read()

    for файл, _ in НАВ:
        путь = os.path.join(pages, файл)
        сырое = open(путь, encoding="utf-8").read()
        первая, тело = сырое.split("\n", 1)
        мета = json.loads(re.sub(r"^<!--META\s*|\s*-->$", "", первая.strip()))

        не_нашлось = []

        def фрагмент(m):
            имя = m.group(1)
            if имя not in куски:
                не_нашлось.append(имя)
                return ""
            return куски[имя]

        def число(m):
            try:
                return достать(stats, m.group(1))
            except (KeyError, TypeError):
                не_нашлось.append(m.group(1))
                return "??"

        тело = re.sub(r"\{\{([\w.]+)\}\}", фрагмент, тело)
        тело = re.sub(r"\[\[([\w.А-Яа-яЁё ]+)\]\]", число, тело)
        мета["титул"] = мета.get("титул", мета["заголовок"])
        for поле in ("заголовок", "подзаголовок", "титул", "описание"):
            мета[поле] = re.sub(r"\[\[([\w.А-Яа-яЁё ]+)\]\]", число, мета[поле])
        if не_нашлось:
            print(f"  ⚠ {файл}: не подставлено — {', '.join(sorted(set(не_нашлось)))}")

        нав = "".join(
            f'<a href="{h}"{" class=here" if h == файл else ""}>{n}</a>'
            for h, n in НАВ)
        open(os.path.join(out, файл), "w", encoding="utf-8").write(
            ОБОЛОЧКА.format(нав=нав, тело=тело, **мета))
        print(f"  {файл} — {len(тело)} знаков")

    print("сайт собран в", out)


main()
