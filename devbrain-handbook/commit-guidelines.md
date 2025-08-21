# 📦 Commit Guidelines

This guide defines how commits should be written — for humans and agents alike.

> The commit log is a **narrative**, not a trash heap.  
> Every message should make sense on its own and in sequence.

---

## 🧠 Goals of Good Commits

- Tell the *why*, not just the *what*
- Make reviewing changes easier
- Help agents (and future you) understand how the project evolved
- Enable clean diffs, changelogs, and feature tracking

---

## 📏 Commit Format

```
<type>: <description> [optional scope]
<body> (optional)
```

### Common types:

| Type | Meaning |
|------|---------|
| `feat` | New feature |
| `fix` | Bugfix |
| `refactor` | Code change without behavior change |
| `test` | Test-related changes |
| `docs` | Markdown, comments, planning |
| `chore` | Internal tooling, cleanup |
| `style` | Linting, formatting, naming |
| `perf` | Performance tuning |
| `ci` | Devops / deployment changes |

### Examples:
```
feat: add password reset flow to /auth
fix: prevent double-submit in invite form
refactor: extract validateSession() from auth handler
docs(context): add architecture notes for feature flags
test: cover new fallback edge case in /notify
style: rename props for clarity
```

> You can always append scope (`(auth)` or `(feature-flags)`) when helpful.

---

## 📘 Description Best Practices

- Explain **why** the change was made
- Link it to a feature, prompt, or bug if relevant
- Summarize risks or architectural impact

Example:
```
refactor(auth): simplify token parsing flow

Extracted token parsing logic to its own function.
Prepping for upcoming session timeout overhaul.
```

---

## 🤖 Agent Rules for Commits

Agents must:
- Use a valid `type:` prefix
- Match the summary to the edit made
- Add reasoning in the description if structural or refactor-based
- Avoid vague messages like:
  - `update code`
  - `fix stuff`
  - `tweak logic`
  - `add test`

Agents should also:
- Link to prompt (if used)
- Mention test coverage or risk scope if relevant

---

## 🚫 Anti-Patterns

- ❌ "WIP", "checkpoint", "fix again" messages
- ❌ Multiple unrelated changes in one commit
- ❌ Commits without summaries
- ❌ Emoji-only or meme commits (fun but messy in shared history)

---

## ✅ Philosophy

> **If someone had to debug your project with only your commit log, could they?**

Write like the history matters. Because it does.