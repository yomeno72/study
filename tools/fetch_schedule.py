"""Скачивает расписание группы ТулГУ и сохраняет компактный JSON для мини-приложения.

Пример: python tools/fetch_schedule.py 121561 [папка]
Файл перезаписывается, только если пары изменились, — чтобы автообновление не коммитило впустую.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

API = "https://tulsu.ru/schedule/queries/GetSchedule.php"
DEFAULT_OUT_DIR = Path(__file__).parent.parent / "webapp" / "schedule"

KINDS = {"Лекции": "Лекция", "Практические занятия": "Практика", "Лабораторные занятия": "Лабораторная"}


def short_name(full):
    parts = full.split()
    if len(parts) < 2:
        return full
    return parts[0] + " " + " ".join(p[0] + "." for p in parts[1:])


def kind(kow):
    for long, short in KINDS.items():
        if kow.startswith(long):
            return short + kow[len(long):]
    return kow


def main(group, out_dir):
    r = httpx.get(API, params={"search_field": "GROUP_P", "search_value": group}, timeout=60)
    r.raise_for_status()
    lessons = []
    for item in r.json():
        start, _, end = item["TIME_Z"].partition(" - ")
        note = " ".join(g["PRIM"] for g in item.get("GROUPS", []) if g.get("GROUP_P") == group and g.get("PRIM"))
        lessons.append({
            "d": datetime.strptime(item["DATE_Z"], "%d.%m.%Y").date().isoformat(),
            "t": start.strip(), "e": end.strip(),
            "s": item["DISCIP"], "k": kind(item["KOW"]), "c": item.get("CLASS", ""),
            "a": "" if item["AUD"] == "Без аудитории" else item["AUD"],
            "p": short_name(item.get("PREP", "")), "n": note,
        })
    if not lessons:
        raise SystemExit("ТулГУ вернул пустое расписание — файл не трогаю")
    lessons.sort(key=lambda l: (l["d"], l["t"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{group}.json"
    if out.exists() and json.loads(out.read_text(encoding="utf-8"))["lessons"] == lessons:
        print(f"{out}: без изменений ({len(lessons)} пар)")
        return
    out.write_text(json.dumps({"group": group, "updated": datetime.now().date().isoformat(), "lessons": lessons},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{out}: {len(lessons)} пар, {lessons[0]['d']} … {lessons[-1]['d']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "121561",
         Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT_DIR)
