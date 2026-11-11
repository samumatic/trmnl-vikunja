<img src="docs/icon.svg" alt="Vikunja Tasks icon" width="88" align="right">

# Vikunja Tasks

The open tasks of your [Vikunja](https://vikunja.io) as a calm checklist on [TRMNL](https://trmnl.com) e-paper displays: a box for every task, the most pressing first, due dates in plain words, priority marks for what is urgent and who each task belongs to. What you tick off today stays on the list, ticked, until midnight.

![Full layout](docs/full.png)

| Portrait | TRMNL X | Half (vertical) |
|---|---|---|
| ![Portrait](docs/portrait.png) | ![TRMNL X](docs/trmnl-x.png) | ![Half vertical](docs/half_vertical.png) |

| Half (horizontal) | Quadrant |
|---|---|
| ![Half horizontal](docs/half_horizontal.png) | ![Quadrant](docs/quadrant.png) |

## Features

- One project, several or all, chosen by name or ID; with several, tasks are grouped under their project
- Due dates as *Today 18:00*, *Tomorrow*, *Sat* or *2 days late*: late tasks filled black, today outlined
- Vikunja priority 3 to 5 as `!` to `!!!`; people (first name or username) and labels, optional
- **Done today**: tasks ticked off today stay on the list with a ticked box and struck through, until midnight
- **Only due by tomorrow**: just what is overdue or due today or tomorrow
- An extra [Vikunja filter](https://vikunja.io/docs/filters) on top, e.g. `due_date < now+7d` or `priority >= 3`
- Clear screens for *all done*, a rejected token or an unreachable server
- German or English (or follow the TRMNL account language)
- All four TRMNL layouts, in landscape and portrait, on TRMNL OG and TRMNL X; long lists flow into a second column and end with "and N more"

Read only: the plugin never changes anything in Vikunja.

## Setup

1. In Vikunja, open **Settings**, then **API Tokens**, and create a token with these permissions (people and labels come with the tasks):
   - **Projects: Read All**
   - **Tasks: Read All**
2. Add the plugin to TRMNL and paste the token. For your own server, also enter its address, e.g. `https://tasks.example.com`. TRMNL fetches the tasks from its servers, so the address must be reachable from the internet.
3. Optional: choose projects.

Without a token the plugin shows sample tasks.

## Settings

| Setting | Default | |
|---|---|---|
| Vikunja address | Vikunja Cloud | Base URL of your Vikunja |
| API token | – | Projects: Read All, Tasks: Read All |
| Projects | all | Names or IDs, comma separated |
| Show | All open tasks | Or only what is due by tomorrow (overdue, today, tomorrow) |
| Task details | People and labels | Or people only, or none |
| Done today | on | Tasks finished today stay, ticked off, until midnight |
| Advanced filter | – | Vikunja filter syntax, e.g. `priority >= 3` |
| Language | Auto | Auto, Deutsch, English |

Tasks are always ordered by due date (overdue first, undated last, higher priority first on ties). With more than one project they are grouped by project, and the title is the project name when there is just one.

The plugin asks for up to 250 open tasks and 250 done today; Vikunja caps each at its `max_items_per_page`, 50 by default. If you have more, narrow the list with projects or the advanced filter.

## Development

Needs Docker (or `gem install trmnl_preview`).

```bash
bin/trmnlp serve
```

Preview with your own Vikunja instead of sample tasks:

```bash
VIKUNJA_URL=https://tasks.example.com VIKUNJA_TOKEN=tk_… bin/trmnlp serve
```

Tests and lint (also run in CI):

```bash
bin/trmnlp lint
```

```bash
bin/trmnlp test --report report
```

`src/transform.py` turns Vikunja's answer into what the views show; `src/shared.liquid` holds the list markup, the four view files only pick the layout. Built with the [TRMNL Framework](https://trmnl.com/framework) and [trmnlp](https://github.com/usetrmnl/trmnlp).

## License

MIT, see [LICENSE](LICENSE). Vikunja is a trademark of its authors; this plugin is not affiliated with Vikunja.
