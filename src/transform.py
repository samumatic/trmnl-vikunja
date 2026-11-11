"""Vikunja Tasks: tasks from a Vikunja instance, ready for the checklist views.

Polled: IDX_0 = GET /api/v1/tasks (open tasks, plus the user's own filter; in focus mode only those due by
tomorrow), IDX_1 = GET /api/v1/projects (names), IDX_2 = GET /api/v1/tasks done since midnight (only when
"done today" is on). Everything the markup shows is decided here: which projects, the order, the due-date words
in German or English, who a task is assigned to, and what to say when the token is missing, rejected or the
server can't be reached.
"""
from datetime import datetime, timedelta, timezone

# Vikunja stores "no due date" as the zero time.
NO_DATE = "0001-01-01"
MAX_TASKS = 60

WORDS = {
    "de": {
        "title": "Aufgaben", "open_n": "{n} offen", "done_n": "{n} erledigt", "demo": "Beispiel",
        "today": "Heute", "tomorrow": "Morgen", "yesterday": "Gestern", "overdue": "seit {n} Tagen",
        "weekdays": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "months": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."],
        "done_group": "Heute erledigt",
        "done_title": "Alles erledigt", "done_text": "Keine offenen Aufgaben.",
        "focus_text": "Nichts fällig bis morgen.",
        "auth_title": "Token abgelehnt", "auth_text": "Vikunja hat das API-Token nicht angenommen. Token und Rechte (Tasks, Projects lesen) prüfen.",
        "down_title": "Vikunja nicht erreichbar", "down_text": "Keine Antwort von {host}. Adresse in den Plugin-Einstellungen prüfen.",
        "error_title": "Fehler von Vikunja", "missing_title": "Projekt nicht gefunden",
        "missing_text": "Kein Projekt heißt {names}.",
        # (title, priority, due in days or None, labels, assignee, done)
        "demo_groups": [
            ("Einkaufen", [("Hafermilch", 0, None, [], "", False), ("Brot vom Bäcker", 0, 0, [], "Mia", False),
                           ("Rohrreiniger", 3, None, ["Drogerie"], "", False), ("Äpfel", 0, None, [], "", False),
                           ("Geschenkpapier", 0, 4, [], "Jonas", False), ("Kaffee", 0, None, [], "", True)]),
            ("Haushalt", [("Altglas wegbringen", 0, -1, [], "Jonas", False), ("Heizung entlüften", 0, 2, [], "", False),
                          ("Rauchmelder testen", 4, 1, ["Sicherheit"], "Mia", False),
                          ("Pflanzen gießen", 0, 0, [], "", False), ("Spülmaschine ausräumen", 0, 0, [], "Mia", True)]),
        ],
    },
    "en": {
        "title": "Tasks", "open_n": "{n} open", "done_n": "{n} done", "demo": "Sample",
        "today": "Today", "tomorrow": "Tomorrow", "yesterday": "Yesterday", "overdue": "{n} days late",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "done_group": "Done today",
        "done_title": "All done", "done_text": "No open tasks.",
        "focus_text": "Nothing due by tomorrow.",
        "auth_title": "Token rejected", "auth_text": "Vikunja did not accept the API token. Check the token and its rights (read Tasks and Projects).",
        "down_title": "Vikunja unreachable", "down_text": "No answer from {host}. Check the address in the plugin settings.",
        "error_title": "Error from Vikunja", "missing_title": "Project not found",
        "missing_text": "No project is called {names}.",
        "demo_groups": [
            ("Groceries", [("Oat milk", 0, None, [], "", False), ("Bread from the bakery", 0, 0, [], "Mia", False),
                           ("Drain cleaner", 3, None, ["Drugstore"], "", False), ("Apples", 0, None, [], "", False),
                           ("Wrapping paper", 0, 4, [], "Jonas", False), ("Coffee", 0, None, [], "", True)]),
            ("Home", [("Take out the glass", 0, -1, [], "Jonas", False), ("Bleed the radiators", 0, 2, [], "", False),
                      ("Test smoke alarms", 4, 1, ["Safety"], "Mia", False),
                      ("Water the plants", 0, 0, [], "", False), ("Empty the dishwasher", 0, 0, [], "Mia", True)]),
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


def switch(fields, key):
    """A boolean field: on unless saved as "false" (TRMNL stores them as strings)."""
    return str(fields.get(key, "true")).lower() != "false"


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


def person(user):
    """First name if Vikunja has a display name, else the username."""
    if not isinstance(user, dict):
        return ""
    name = str(user.get("name") or "").strip()
    return name.split()[0] if name else str(user.get("username") or "")


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
            "groups": [], "open": 0, "done": 0}


def simplify(t, opts):
    labels = [str(l.get("title")) for l in (t.get("labels") or []) if isinstance(l, dict) and l.get("title")]
    people = [p for p in (person(u) for u in (t.get("assignees") or [])) if p]
    return {
        "id": t.get("id") or 0,
        "title": " ".join(str(t.get("title") or "").split()),
        "priority": t.get("priority") or 0,
        "due_at": parse_time(t.get("due_date")),
        "done_at": parse_time(t.get("done_at")),
        "project_id": t.get("project_id"),
        "labels": labels[:3] if opts["labels"] else [],
        "people": people[:3] if opts["assignees"] else [],
    }


def row(t, done, today, opts):
    due = None if done or not t["due_at"] else due_label(t["due_at"], today, opts["tz"], opts["w"], opts["lang"])
    return {
        "title": t["title"],
        "done": done,
        "prio": "" if done else "!" * max(0, min(3, t["priority"] - 2)),
        "due": due[0] if due else "",
        "urgency": due[1] if due else 0,
        "labels": [] if done else t["labels"],
        "people": t["people"],
    }


def build_groups(open_tasks, done_tasks, names, group, today, opts):
    tasks = sorted((simplify(t, opts) for t in open_tasks), key=sort_key(opts["order"]))
    groups, index = [], {}
    for t in tasks[:MAX_TASKS]:
        key = t["project_id"] if group else 0
        if key not in index:
            index[key] = len(groups)
            groups.append({"name": names.get(t["project_id"], "") if group else "", "tasks": []})
        groups[index[key]]["tasks"].append(row(t, False, today, opts))
    # Ticked off today: last, newest first, so a long open list pushes them off screen first.
    far_past = datetime(1, 1, 1, tzinfo=timezone.utc)
    done = sorted((simplify(t, opts) for t in done_tasks), key=lambda t: (t["done_at"] or far_past, t["id"]),
                  reverse=True)
    if done:
        groups.append({"name": opts["w"]["done_group"], "tasks": [row(t, True, today, opts) for t in done[:MAX_TASKS]]})
    return groups


def due_by_tomorrow(task, today, tz):
    due = parse_time(task.get("due_date"))
    return due is not None and (due.astimezone(tz).date() - today).days <= 1


def demo_tasks(w, now):
    open_tasks, done_tasks, names = [], [], {}
    for p, (project, items) in enumerate(w["demo_groups"], start=1):
        names[p] = project
        for i, (title, prio, days, labels, who, done) in enumerate(items):
            due = (now + timedelta(days=days)).replace(hour=9, minute=0) if days is not None else None
            task = {"id": p * 100 + i, "title": title, "priority": prio, "project_id": p, "done": done,
                    "due_date": due.isoformat() if due else None, "labels": [{"title": l} for l in labels],
                    "assignees": [{"username": who.lower(), "name": who}] if who else [],
                    "done_at": (now - timedelta(minutes=30 + i)).isoformat() if done else None}
            (done_tasks if done else open_tasks).append(task)
    return open_tasks, done_tasks, names


def summary(w, open_count, done_count):
    text = w["open_n"].format(n=open_count)
    return text + (" · " + w["done_n"].format(n=done_count) if done_count else "")


def run(input):
    trmnl = input.get("trmnl") or {}
    user = trmnl.get("user") or {}
    fields = (trmnl.get("plugin_settings") or {}).get("custom_fields_values") or {}
    lang = language(fields, user)
    w = WORDS[lang]
    tz = local_zone(user.get("time_zone_iana") or "UTC", user.get("utc_offset"))
    now = datetime.now(timezone.utc).astimezone(tz)
    today = now.date()
    focus = str(fields.get("mode") or "all") == "focus"
    show_done = switch(fields, "show_done_today")
    opts = {"order": str(fields.get("sort") or "due"), "labels": switch(fields, "show_labels"),
            "assignees": switch(fields, "show_assignees"), "tz": tz, "w": w, "lang": lang}
    group = switch(fields, "group_by_project")
    bar = str(fields.get("title") or "").strip() or w["title"]
    host = str(fields.get("base_url") or "https://app.vikunja.cloud").split("//")[-1].split("/")[0]
    empty_text = w["focus_text"] if focus else w["done_text"]

    if not str(fields.get("api_token") or "").strip():
        open_tasks, done_tasks, names = demo_tasks(w, now)
        if focus:
            open_tasks = [t for t in open_tasks if due_by_tomorrow(t, today, tz)]
        done_tasks = done_tasks if show_done else []
        return {"vk": {"state": "demo", "title": bar, "instance": w["demo"],
                       "open": len(open_tasks), "done": len(done_tasks), "message": None,
                       "groups": build_groups(open_tasks, done_tasks, names, group, today, opts)}}

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
        quoted = ", ".join(f"„{m}“" if lang == "de" else f"“{m}”" for m in missing)
        return {"vk": message("missing", w["missing_title"], w["missing_text"].format(names=quoted), bar)}

    def chosen(t):
        return isinstance(t, dict) and (ids is None or t.get("project_id") in ids)

    open_tasks = [t for t in task_rows if chosen(t) and not t.get("done")
                  and (not focus or due_by_tomorrow(t, today, tz))]
    done_tasks = []
    if show_done:
        for t in rows(input.get("IDX_2")) or []:
            finished = parse_time(t.get("done_at")) if chosen(t) and t.get("done") else None
            if finished and finished.astimezone(tz).date() == today:
                done_tasks.append(t)

    shown = {t.get("project_id") for t in open_tasks + done_tasks} if ids is None else ids
    title = str(fields.get("title") or "").strip()
    if not title:
        title = (names.get(next(iter(shown))) or w["title"]) if len(shown) == 1 else w["title"]
    count = len(open_tasks) + len(done_tasks)
    return {"vk": {
        "state": "ok" if count else "empty",
        "title": title,
        "instance": summary(w, len(open_tasks), len(done_tasks)),
        "open": len(open_tasks),
        "done": len(done_tasks),
        "groups": build_groups(open_tasks, done_tasks, names, group and len(shown) > 1, today, opts),
        "message": None if count else {"title": w["done_title"], "text": empty_text},
    }}
