---
name: korean-spell-checker
description: Korean spelling and spacing checker for Markdown or text translations, especially ko.javascript.info Korean articles. Use when the user asks to check 맞춤법, 띄어쓰기, 오탈자, run hanspell, review Korean spelling in .md files, or convert the Claude spell-checker workflow to Codex.
---

# Korean Spell Checker

Use the bundled `scripts/check_spelling.py` script to run `hanspell` and report Korean spelling and spacing issues in Markdown or plain text files.

## Workflow

1. Resolve the target file or files.
   - If the user gives a file path, check that file.
   - If the user gives a directory, find Markdown files under it with `rg --files <dir> | rg '\.md$'`.
   - If no target is clear, ask for the file or directory path.

2. Run the bundled script from this skill directory:

```bash
python3 scripts/check_spelling.py path/to/article.md
```

If the current working directory is not the skill directory, use the absolute path to this skill's `scripts/check_spelling.py`.

3. Parse the JSON output.
   - `violations` contains `line`, `problem`, `suggestion`, `explanation`, and `severity`.
   - `passed` contains `맞춤법 오류 없음` when no issues are found.
   - If the script returns an `error`, report the dependency or execution problem directly.

4. Report results as a concise Markdown table:

| line | rule_id | problem | suggestion | explanation |
|---:|---|---|---|---|

Use `SPELL` as the rule id and treat all script findings as `required` unless the user asks for a softer editorial review.

## Dependencies

The script requires Python 3, Node.js, and `npx`. It runs `npx --yes hanspell -d`, so the first run may download the `hanspell` npm package.

If `npx`, Node.js, or `hanspell` is unavailable, stop and report the exact script error. Do not invent spelling results.

## Editing Guidance

Do not edit files unless the user explicitly asks for fixes.

When applying fixes:

- Only change text outside fenced code blocks, inline code, URLs, Markdown image targets, and HTML tags.
- Skip a correction if the original text appears multiple times and the intended occurrence is ambiguous.
- Apply one correction at a time and re-read the changed area before continuing.
- Prefer leaving a manual suggestion when the correction rewrites a whole sentence or may alter technical meaning.
