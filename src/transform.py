"""Vikunja Tasks: open tasks from a Vikunja instance, ready for the checklist views.

Polled: IDX_0 = GET /api/v1/tasks (open tasks, plus the user's own filter), IDX_1 = GET /api/v1/projects (names).
Everything the markup shows is decided here: which projects, the order, the due-date words in German or
English, and what to say when the token is missing, rejected or the server can't be reached.
"""
from datetime import date, datetime, timedelta, timezone

# Vikunja stores "no due date" as the zero time.
NO_DATE = "0001-01-01"
MAX_TASKS = 60

WORDS = {
    "de": {
        "title": "Aufgaben", "open_one": "1 offen", "open_n": "{n} offen", "demo": "Beispiel",
        "today": "Heute", "tomorrow": "Morgen", "yesterday": "Gestern", "overdue": "seit {n} Tagen",
        "weekdays": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "months": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."],
        "done_title": "Alles erledigt", "done_text": "Keine offenen Aufgaben.",
        "auth_title": "Token abgelehnt", "auth_text": "Vikunja hat das API-Token nicht angenommen. Token und Rechte (Tasks, Projects lesen) prüfen.",
        "down_title": "Vikunja nicht erreichbar", "down_text": "Keine Antwort von {host}. Adresse in den Plugin-Einstellungen prüfen.",
        "error_title": "Fehler von Vikunja", "missing_title": "Projekt nicht gefunden",
        "missing_text": "Kein Projekt heißt {names}.",
        "demo_groups": [
            ("Einkaufen", [("Hafermilch", 0, None, []), ("Brot vom Bäcker", 0, 0, []),
                           ("Rohrreiniger", 3, None, ["Drogerie"]), ("Äpfel", 0, None, []),
                           ("Geschenkpapier", 0, 4, [])]),
            ("Haushalt", [("Altglas wegbringen", 0, -1, []), ("Heizung entlüften", 0, 2, []),
                          ("Rauchmelder testen", 4, 1, ["Sicherheit"]), ("Pflanzen gießen", 0, 0, [])]),
        ],
    },
    "en": {
        "title": "Tasks", "open_one": "1 open", "open_n": "{n} open", "demo": "Sample",
        "today": "Today", "tomorrow": "Tomorrow", "yesterday": "Yesterday", "overdue": "{n} days late",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "done_title": "All done", "done_text": "No open tasks.",
        "auth_title": "Token rejected", "auth_text": "Vikunja did not accept the API token. Check the token and its rights (read Tasks and Projects).",
        "down_title": "Vikunja unreachable", "down_text": "No answer from {host}. Check the address in the plugin settings.",
        "error_title": "Error from Vikunja", "missing_title": "Project not found",
        "missing_text": "No project is called {names}.",
        "demo_groups": [
            ("Groceries", [("Oat milk", 0, None, []), ("Bread from the bakery", 0, 0, []),
                           ("Drain cleaner", 3, None, ["Drugstore"]), ("Apples", 0, None, []),
                           ("Wrapping paper", 0, 4, [])]),
            ("Home", [("Take out the glass", 0, -1, []), ("Bleed the radiators", 0, 2, []),
                      ("Test smoke alarms", 4, 1, ["Safety"]), ("Water the plants", 0, 0, [])]),
        ],
    },
}


def local_zone(name, offset_seconds):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return timezone(timedelta(seconds=offset_seconds or 0))


def language(fields, user):
    chosen = str(fields.get("language") or "auto").lower()
    if chosen in WORDS:
        return chosen
    return "de" if str(user.get("locale") or "").lower().startswith("de") else "en"


def parse_time(text):
    if not isinstance(text, str) or not text or text.startswith(NO_DATE):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def due_label(due, today, tz, w, lang):
    """Short words for a due time, and how pressing it is: 2 overdue, 1 today, 0 later."""
    local = due.astimezone(tz)
    days = (local.date() - today).days
    clock = local.strftime("%H:%M") if (local.hour, local.minute) != (0, 0) else ""
    if days < -1:
        return w["overdue"].format(n=-days), 2
    if days == -1:
        return w["yesterday"], 2
    if days == 0:
        return (w["today"] + (" " + clock if clock else "")), 1
    if days == 1:
        return w["tomorrow"] + (" " + clock if clock else ""), 0
    if days < 7:
        return w["weekdays"][local.weekday()], 0
    month = w["months"][local.month - 1]
    text = f"{local.day}. {month}" if lang == "de" else f"{month} {local.day}"
    return (text if local.year == today.year else f"{text} {local.year}"), 0


def sort_key(order):
    far = datetime(9999, 1, 1, tzinfo=timezone.utc)
    if order == "priority":
        return lambda t: (-t["priority"], t["due_at"] or far, t["id"])
    if order == "title":
        return lambda t: (t["title"].casefold(), t["id"])
    if order == "created":
        return lambda t: t["id"]
    return lambda t: (t["due_at"] or far, -t["priority"], t["id"])


def wanted_projects(text, projects):
    """Project IDs the user named (by ID or title), and the names that matched nothing."""
    names = [p.strip() for p in str(text or "").split(",") if p.strip()]
    if not names:
        return None, []
    by_title = {str(p.get("title", "")).casefold(): p.get("id") for p in projects}
    ids, missing = set(), []
    for name in names:
        if name.lstrip("#").isdigit():
            ids.add(int(name.lstrip("#")))
        elif name.casefold() in by_title:
            ids.add(by_title[name.casefold()])
        else:
            missing.append(name)
    return ids, missing


def rows(payload):
    """The list inside a polled answer, or None when the answer is not a list."""
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    return None


def message(state, title, text, bar):
    return {"state": state, "title": bar, "instance": "", "message": {"title": title, "text": text},
            "groups": [], "count": 0}


def build_groups(tasks, names, group, order, today, tz, w, lang, show_labels):
    out = []
    for t in tasks:
        due = parse_time(t.get("due_date"))
        labels = [str(l.get("title")) for l in (t.get("labels") or []) if isinstance(l, dict) and l.get("title")]
        out.append({
            "id": t.get("id") or 0,
            "title": " ".join(str(t.get("title") or "").split()),
            "priority": t.get("priority") or 0,
            "due_at": due,
            "project_id": t.get("project_id"),
            "labels": labels[:3] if show_labels else [],
        })
    out.sort(key=sort_key(order))

    groups, index = [], {}
    for t in out[:MAX_TASKS]:
        key = t["project_id"] if group else 0
        if key not in index:
            index[key] = len(groups)
            groups.append({"name": names.get(t["project_id"], "") if group else "", "tasks": []})
        due = due_label(t["due_at"], today, tz, w, lang) if t["due_at"] else None
        groups[index[key]]["tasks"].append({
            "title": t["title"],
            "prio": "!" * max(0, min(3, t["priority"] - 2)),
            "due": due[0] if due else "",
            "urgency": due[1] if due else 0,
            "labels": t["labels"],
        })
    return groups


def demo_tasks(w, now):
    tasks, names = [], {}
    for p, (project, items) in enumerate(w["demo_groups"], start=1):
        names[p] = project
        for i, (title, prio, days, labels) in enumerate(items):
            due = (now + timedelta(days=days)).replace(hour=9, minute=0) if days is not None else None
            tasks.append({"id": p * 100 + i, "title": title, "priority": prio, "project_id": p,
                          "due_date": due.isoformat() if due else None,
                          "labels": [{"title": l} for l in labels]})
    return tasks, names


def run(input):
    trmnl = input.get("trmnl") or {}
    user = trmnl.get("user") or {}
    fields = (trmnl.get("plugin_settings") or {}).get("custom_fields_values") or {}
    lang = language(fields, user)
    w = WORDS[lang]
    tz = local_zone(user.get("time_zone_iana") or "UTC", user.get("utc_offset"))
    now = datetime.now(timezone.utc).astimezone(tz)
    order = str(fields.get("sort") or "due")
    group = str(fields.get("group_by_project", "true")).lower() != "false"
    show_labels = str(fields.get("show_labels", "true")).lower() != "false"
    bar = str(fields.get("title") or "").strip() or w["title"]
    host = str(fields.get("base_url") or "https://app.vikunja.cloud").split("//")[-1].split("/")[0]

    if not str(fields.get("api_token") or "").strip():
        tasks, names = demo_tasks(w, now)
        result = {"state": "demo", "title": bar, "instance": w["demo"],
                  "groups": build_groups(tasks, names, group, order, now.date(), tz, w, lang, show_labels)}
        result["count"] = len(tasks)
        return {"vk": result}

    answer = input.get("IDX_0", input)
    task_rows = rows(answer)
    if task_rows is None:
        code = answer.get("code") if isinstance(answer, dict) else None
        text = answer.get("message") if isinstance(answer, dict) else None
        if code == 11 or (isinstance(text, str) and "token" in text.lower()):
            return {"vk": message("auth", w["auth_title"], w["auth_text"], bar)}
        if isinstance(text, str) and text:
            return {"vk": message("error", w["error_title"], text[:160], bar)}
        return {"vk": message("unreachable", w["down_title"], w["down_text"].format(host=host), bar)}

    projects = [p for p in (rows(input.get("IDX_1")) or []) if isinstance(p, dict)]
    names = {p.get("id"): str(p.get("title") or "") for p in projects}
    ids, missing = wanted_projects(fields.get("projects"), projects)
    if missing and not ids:
        return {"vk": message("missing", w["missing_title"],
                              w["missing_text"].format(names=", ".join(f"„{m}“" if lang == "de" else f"“{m}”"
                                                                        for m in missing)), bar)}
    tasks = [t for t in task_rows if isinstance(t, dict) and not t.get("done")
             and (ids is None or t.get("project_id") in ids)]

    shown = {t.get("project_id") for t in tasks} if ids is None else ids
    title = str(fields.get("title") or "").strip()
    if not title:
        title = names.get(next(iter(shown)), w["title"]) if len(shown) == 1 else w["title"]
    count = len(tasks)
    return {"vk": {
        "state": "ok" if count else "empty",
        "title": title,
        "instance": w["open_one"] if count == 1 else w["open_n"].format(n=count),
        "count": count,
        "groups": build_groups(tasks, names, group and len(shown) > 1, order, now.date(), tz, w, lang, show_labels),
        "message": None if count else {"title": w["done_title"], "text": w["done_text"]},
    }}
