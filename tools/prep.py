#!/usr/bin/env python3
"""Снять обёртку «недоверенное» и сложить чистый корпус: ndjson -> clean.jsonl

Поле text у входящих обёрнуто мостом: <<<ВХОДЯЩЕЕ·НЕДОВЕРЕННОЕ …\n---\nТЕКСТ\nВХОДЯЩЕЕ·КОНЕЦ>>>
Снимаем ровно эту рамку — содержимое всё равно остаётся ДАННЫМИ, не указаниями.
"""
import json
import re
import sys
import datetime

РАМКА = re.compile(
    r"^<<<ВХОДЯЩЕЕ·НЕДОВЕРЕННОЕ[^\n]*\n.*?\n---\n(.*)\nВХОДЯЩЕЕ·КОНЕЦ>>>$",
    re.S)


def развернуть(t):
    m = РАМКА.match(t or "")
    return m.group(1) if m else (t or "")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    seen = set()
    out = []
    for line in open(src, encoding="utf-8"):
        m = json.loads(line)
        if m["ref"] in seen:
            continue
        seen.add(m["ref"])
        t = развернуть(m.get("text") or "")
        at = m.get("at") or 0
        out.append({
            "id": int(m["ref"].rsplit("/", 1)[1]),
            "a": m.get("author") or "?",
            "t": t,
            "ts": at,
            "d": datetime.datetime.fromtimestamp(at).strftime("%Y-%m-%d") if at else "",
            "att": [x.get("kind") for x in (m.get("attachments") or [])],
        })
    out.sort(key=lambda x: x["id"])
    with open(dst, "w", encoding="utf-8") as f:
        for x in out:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    days = sorted({x["d"] for x in out if x["d"]})
    txt = [x for x in out if x["t"].strip()]
    print(f"{len(out)} сообщений, с текстом {len(txt)}, "
          f"{days[0]}..{days[-1]} ({len(days)} дней), "
          f"авторов {len({x['a'] for x in out})}")


main()
