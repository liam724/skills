# Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Agent skills I use to get more out of Claude Code, Codex and Cursor.

Each skill is a small folder with a `SKILL.md` and, where it helps, a few
scripts. Read them, copy them, change them. They're meant to be yours.

## Install

Pick one method per agent. Installing both gives you every skill twice.

**Claude Code** (plugin, updates itself):

```sh
claude plugin marketplace add liam724/skills
claude plugin install liam-skills@liam724
```

**Any agent** (Codex, Cursor, Claude Code and others, via [skills.sh](https://skills.sh/liam724/skills)):

```sh
npx skills@latest add liam724/skills
```

This copies editable files into your agent's skills folder. Run
`npx skills@latest update` to pull changes.

## Skills

### transcript-mining

You correct your agent the same way every week. You paste the same context,
explain the same convention, and watch it fail on the same task. Each time
feels small, so you never fix the cause.

This skill reads your past conversations and finds those patterns for you.
It ranks what it finds by how often it happens, shows the evidence, and
proposes the smallest fix: a line in your instructions, a new or trimmed
skill, a script, or a settings change. You pick what to apply.

**Run it:** `/transcript-mining` in Claude Code, `$transcript-mining` in
Codex, or ask for it by name in a chat app.

**What it reads.** It uses the best source it can reach:

- On your machine: Claude Code, Cursor and Codex transcripts, from the last
  30 days by default. Needs Python 3.8+, with no packages and no network.
- In a web chat or cloud agent: your chat history, through the app's
  past-chats tools.
- Anywhere else: a Claude or ChatGPT data export you upload.

It tells you what it covered and what it couldn't read, rather than
guessing.

**Privacy.** Your conversations go to the model you're running. The local
helpers output full prompts and file paths with nothing anonymised, so keep
that output out of any repo. The tests here use synthetic data only.

**Limits.** Failure detection is a heuristic based on English phrasing and
tool errors. Treat its matches as leads, not verdicts.

## Develop

Inside this repo, `.claude/skills/` and `.agents/skills/` link to `skills/`,
so the skills load in Claude Code and Codex without installing.

```sh
python3 -m unittest discover -s tests -p test_transcript_mining.py -v
```

## License

[MIT](LICENSE)
