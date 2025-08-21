# 📝 Documentation Rules

This guide defines when and how to document features, modules, and logic — for both humans and MCP agents.

The goal:  
**Write only what matters. Keep it where it belongs. Let agents help.**

---

## 🧠 What Counts As Documentation?

Documentation lives in three places:

1. **Inline comments** — inside your code, attached to logic
2. **Markdown files** — in `/context/docs/` or `/context/features/`
3. **Prompt scaffolds** — in `/prompts/` (used by Cursor or agents)

If it's not in one of these places, it's probably not real documentation.

---

## ✍️ When to Document

| Trigger | Required? | Where |
|--------|-----------|-------|
| New feature | ✅ | `context/features/feature-name.md` |
| Complex logic | ✅ | Inline code comment |
| Public module API | ✅ | Top-of-file docblock or `README.md` |
| Experimental idea | ⚠️ | Draft in `/context/features/` |
| UI layout | ⚠️ | Optional diagram or Figma note |
| Refactor | ✅ (if structural) | Brief summary in `/context/docs/` |
| One-liner util | ❌ | Self-documenting via name |

> If you wouldn't understand it three weeks from now — write it down.

---

## 📄 Markdown Rules

- Keep it light. Bullet points > essays.
- Don't write paragraphs unless you're shipping a product decision.
- Use this structure:
```md
# Feature: User Signup
## Purpose
## Core Flow
## Edge Cases
## Test Notes (if any)
## MCP Notes (optional)
```
- Never duplicate doc content across files.
- Agents should summarize doc edits inline (vs. spawning extra `.md` files).

---

## 💬 Inline Comments

- Write for clarity of intent:
```ts
// This avoids a race condition when two tokens are refreshed simultaneously
```
- Don't explain what — explain why
- Don't leave dead comments that no longer apply

---

## 🪄 AI-Facing Documentation

Agents must:
- Read from `/context/docs/` and inline comments
- Write summaries to `/context/features/` or append intelligently
- Never generate "doc.md" or "summary.md" unless prompted explicitly

If an agent writes a doc:
- It must explain what changed and why it matters
- It must use a Markdown header, not a blob of paragraphs
- It must attach itself to a feature or file

---

## 🚫 Anti-Patterns

- ❌ Commenting every line of a function — your code should explain itself
- ❌ Dropping auto-generated markdown files with no purpose
- ❌ Repeating the same doc in multiple locations
- ❌ Agent logs pretending to be documentation

---

## 🤖 Prompt-Driven Docs (Recommended)

You can use prompts like:
- "Write a summary of this refactor"
- "Create a feature doc for this handler"
- "What does this file do?"
- "Update `/context/features/auth-session.md` to match this logic"

Only generate docs when the new logic changes how you reason about the system.

---

## ✅ Philosophy

**Good documentation tells the story of your thinking — not every keystroke.**

Write with intent. Store with purpose. Keep your future self in mind.