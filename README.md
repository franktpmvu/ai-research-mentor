# AI Research Mentor

**English** | [繁體中文](README.zh-TW.md)

An AI research mentor built on the *Atomic Habits* idea: every day it pushes a few papers, uses questions to help you get the mechanisms right, and remembers how far you've come.
It pairs with a local paper knowledge base, so the mentor can check the original text of papers you've read before explaining a mechanism.

| Folder | What it is | Requirements |
|---|---|---|
| [`mentor/`](mentor/) | The mentor: daily paper push, in-depth evaluation, knowledge-graph prerequisite gating, memory system, skill map, and a small nutrition track | Python 3.10+ (no packages needed; `openpyxl` only for the Excel reading log) |
| [`paper-kb/`](paper-kb/) | Paper knowledge base: PDFs → full-text index with page numbers, served to any AI through an MCP server | Python 3.11+, `pip install -r requirements.txt` |

Each works on its own. When they sit side by side, they connect automatically (see [Integration](#integration)).

> The rule files under `mentor/` (`CLAUDE.md`, `docs/`) and the paper-kb docs are written in Traditional Chinese. Claude reads them fine in any language you chat in.

## Install

```bash
git clone https://github.com/franktpmvu/ai-research-mentor.git
cd ai-research-mentor

# 1. Mentor: nothing to install
python3 mentor/mentor.py integrity      # health check; the first run creates the state files

# 2. Paper knowledge base (optional)
cd paper-kb
pip install -r requirements.txt         # on Windows you can just double-click maintain.bat (it creates a .venv)
# drop PDFs into paper-kb/input_raw/inbox/, then:
python update.py
```

## Usage

The mentor is **rules for an AI to read plus commands for it to run** — it is not a chat app by itself. Open the `mentor/` folder with Claude (Claude Code, the Claude desktop app, or any AI that can read a folder and run commands):

1. The AI reads `mentor/CLAUDE.md` first (the rules entry point), then the files in `mentor/docs/` it points to.
2. Say "run today's push" → it searches for papers, checks for duplicates, enforces prerequisites, and presents them to you.
3. Reply and discuss → it asks questions to help you get the mechanisms right (one question at a time, no handing out answers) and records your level.
4. Say "done" → it wraps up, checks in, and writes the logs. On low-energy days just checking in counts (habit > perfection).
5. Want a daily push automatically? Use Claude's scheduled tasks; the task prompt only needs to say "read `mentor/CLAUDE.md` and run the daily push by its rules".

All commands: [`mentor/docs/commands.md`](mentor/docs/commands.md). Paper knowledge base tools: [`paper-kb/README.md`](paper-kb/README.md).

## Personal settings (the only things you fill in; never uploaded)

| File | Contents | If it's missing |
|---|---|---|
| `mentor/profile.md` | Your background, goals, where you tend to get stuck, preferences | Falls back to the generic defaults in `profile.example.md` |
| `paper-kb/config.json` | Which PDFs are your own published papers (used to build "who you cited") | Treated as empty; everything else works |

Copy the templates and edit: `cp mentor/profile.example.md mentor/profile.md`, `cp paper-kb/config.example.json paper-kb/config.json`.

## Integration

Active automatically when both folders sit side by side.

- **Check the original text before explaining**: the mentor uses `kb_search` / `kb_read` to read the paper-kb index directly (no MCP needed) and cites page numbers.
- **Papers you finish go into the knowledge base**: at "done", `kb_queue --url ...` adds the paper's URL to `paper-kb/input_raw/url_queue.txt`; paper-kb downloads, parses, and indexes it on its next maintenance run.
- If paper-kb lives elsewhere, point to it with the `PAPER_KB_ROOT` environment variable. If it can't be found, these steps are skipped and the mentor keeps working.

Details: [`mentor/docs/paper_kb.md`](mentor/docs/paper_kb.md).

## What isn't uploaded

Your learning records (`state.json`, `learner.json`, `journal/`, `memory/`, …), personal settings, paper PDFs, and the index are all in `.gitignore`. The repo contains only code, rule documents, and templates.

## Acknowledgements

The Socratic questioning rules and the 0–5 skill map in `mentor/docs/learner_eval.md` draw on Jane Street's [agent_skills / socratic-tutor](https://github.com/janestreet/agent_skills) (MIT).

## License

[MIT](LICENSE)
