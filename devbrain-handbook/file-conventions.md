# 🗂️ File & Directory Conventions

This document defines where code, documentation, prompts, and support files should live in Dev Brain–enabled projects. The goal is **clarity, not complexity**.

> If a file doesn't have a clear reason to exist, it doesn't belong.

---

## 🧭 Core Layout

Every project should follow this basic structure:
```
/
├── src/              → App logic only
├── context/          → Agent-readable docs, reasoning, notes
├── __tests__/        → Tests that mirror src/
├── prompts/          → Prompt templates used in Cursor or agents
├── scripts/          → Local utilities, agent runners
├── .devbrainrc       → Dev Brain config (MCP, rules, defaults)
```

Other folders (`/public`, `/assets`, `/api`, etc.) are opt-in depending on the project.

---

## 📂 Folder Responsibilities

### `/src/`
- Domain-first, not layer-first.
```
src/
  users/
  auth/
  notifications/
```
- One concern per file.
- Avoid mega-files or "god folders."
- Don't store test files, helper docs, or random utilities here.

---

### `/context/`
- Holds agent-facing docs (feature plans, summaries, specs).
- Use **plain Markdown** that is skimmable and structured.
- Suggested structure:
```
context/
  docs/           ← permanent architectural references
  features/       ← specific feature breakdowns
  graphs/         ← agent outputs like call graphs or coverage
  index.md        ← quick links / entry point
```

Only create files when there's real thinking to record or reuse.

---

### `/__tests__/`
- Mirrors `/src/` exactly — same folder and file names.
- Use `.test.ts` or `.spec.ts` suffix.
- Never leave empty test files "just in case."

**Bad:**
```
__tests__/users/new-feature.test.ts  ← empty
```

**Good:**
```
__tests__/users/create.test.ts       ← covers src/users/create.ts
```

---

### `/prompts/`
- Store re-usable prompts for Cursor or MCP agents.
- Group by function or agent:
```
prompts/
  test-agent/
  planning/
  fixes/
```

Don't create prompts unless you intend to reuse or maintain them.

---

### `/scripts/`
- CLI scripts, agent setup, automation tasks.
- Should be runnable and helpful — not placeholders.

---

## 📄 File Naming Rules

| File Type | Format | Notes |
|-----------|--------|-------|
| Logic files (JS/TS) | `kebab-case.ts` | Match file to function name if possible |
| Python | `snake_case.py` | Match folder logic |
| Tests | `name.test.ts` or `.spec.ts` | Must mirror src path |
| Prompts | `intent--action.prompt.md` | Self-explanatory |
| Docs | `feature-name.md` | Descriptive and discoverable |
| Scripts | `do-something.sh` or `.py` | Be explicit |

No cryptic names. No throwaway files. No ambiguity.

---

## 🚫 What NOT to Do

- ❌ Don't create `utils/` with everything under the sun  
→ Split by domain (`/users/utils.ts`) or by job (`/lib/formatters.ts`)

- ❌ Don't make empty files for "future you"  
→ Write it or delete it. Drafts belong in `/context/features/`

- ❌ Don't generate agent output unless it's worth keeping  
→ Use scratchpads or logs if unsure

- ❌ Don't litter the project with one-off Markdown or test files  
→ Consolidate or organize inside `/context/`

---

## 🧠 Agent Behavior Notes

Agents must:
- Only write to `/src`, `/__tests__/`, or `/context/` unless explicitly told otherwise
- Never create a new file without attaching a rationale
- Always use existing file structure if it exists
- Avoid duplicating prompts, docs, or helpers that already exist

---

## ✅ Philosophy

> **Your file tree is the first impression of your project's intelligence.**

Keep it tight. Keep it clear. If it's not clearly needed — it's not needed.