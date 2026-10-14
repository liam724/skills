# Skills

## transcript-mining

Review local Claude Code, Cursor, and Codex transcripts to improve your
coding-agent configuration: instructions, skills, tools, scripts, and settings.
Requires Python 3.8+; no external Python packages or network access are needed
by the helpers. Analysis runs through your coding agent's configured model.

### Use

When working inside this checkout, the relative links in `.claude/skills/`
and `.agents/skills/` expose the same `transcript-mining/` folder:

- Claude Code: `/transcript-mining`
- Codex: `$transcript-mining`

For use across projects, copy the complete `transcript-mining/` folder into
`~/.claude/skills/` for Claude Code or `~/.agents/skills/` for Codex. If a skill
with that name already exists, review it before replacing it. Windows checkouts
need Git symlink support for the repository links; copying the folder into the
agent's skill directory also works.

See the official [Claude Code skill documentation](https://code.claude.com/docs/en/skills)
and [Codex skill documentation](https://developers.openai.com/codex/skills).

### Coverage and privacy

The helpers read supported JSONL layouts, include archived Codex sessions,
and report missing sources, unsupported exports, and parsing failures.
They do not read Cursor's internal database or parse plain-text exports.
Source formats can change; partial coverage is reported, not hidden.

The default window selects sessions active in the last 30 days and preserves
their earlier context. Failure detection is heuristic, with English text
patterns and structured tool-error checks. It is not a root-cause classifier.

Helper output contains full private prompts or traces and local paths. It is
not anonymized. Keep it outside this repository and never publish it.
The shipped tests contain only synthetic data, never real session history.

### Test

```sh
python3 -m unittest discover -s tests -p test_transcript_mining.py -v
```
