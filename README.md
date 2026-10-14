# Skills

[![skills.sh](https://skills.sh/b/liam724/skills)](https://skills.sh/liam724/skills)
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

- **[transcript-mining](skills/transcript-mining/SKILL.md)**: reviews your
  local Claude Code, Cursor and Codex transcripts to find repeated work and
  failures, then suggests fixes to your instructions, skills, tools and
  settings. Run `/transcript-mining` in Claude Code or `$transcript-mining`
  in Codex.

## transcript-mining notes

**Privacy.** The helper scripts output your full prompts, traces and local
paths. Nothing is anonymised. Keep that output out of any repo and never
publish it. The tests here use synthetic data only.

**What it reads.** JSONL transcripts from Claude Code, Cursor and Codex,
including archived Codex sessions, from the last 30 days by default. It does
not read Cursor's internal database or plain-text exports. It reports missing
sources and parse failures instead of hiding them.

**Limits.** Failure detection is a heuristic based on English text patterns
and tool errors, not a root-cause classifier.

**Requirements.** Python 3.8+. No packages and no network access.

## Develop

Inside this repo, `.claude/skills/` and `.agents/skills/` link to `skills/`,
so the skills load in Claude Code and Codex without installing.

```sh
python3 -m unittest discover -s tests -p test_transcript_mining.py -v
```

## License

[MIT](LICENSE)
