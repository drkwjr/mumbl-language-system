# ♻️ Refactor Rules

This guide defines how and when code can be safely refactored — by you or an MCP agent.

> Refactors should fix clutter, not create it.  
> Clean code is a feature. Clean commits are mandatory.

---

## 🔁 What Qualifies as a Refactor?

A refactor:
- Changes *how* code is written
- Keeps *what* the code does exactly the same
- Improves readability, structure, reusability, or performance

It is **not**:
- A feature
- A bugfix
- A rewrite of uncertain behavior

---

## 🧭 When Refactors Are Allowed

| Context | Rule |
|--------|------|
| You understand the full file's purpose | ✅ Proceed |
| There's solid test coverage | ✅ Proceed |
| You're touching shared utilities | ⚠️ Be cautious |
| No tests exist for this logic | ❌ Don't touch yet |
| You're guessing what code does | ❌ Don't refactor blindly |

If you're unsure — **don't refactor**. Plan first.

---

## 🧠 Goals of Refactoring

- Improve **clarity**, not cleverness
- Remove **duplication** or tight coupling
- Improve **testability**
- Prepare code for a future change
- Make it easier to reason about

Refactors are *measured by cognitive load*, not LOC changed.

---

## 🧪 Refactor Checklist

Before committing a refactor:
- [ ] Do all tests pass?
- [ ] Did you avoid changing public interfaces?
- [ ] Does this still work for all existing use cases?
- [ ] Are agents or docs updated if structure changed?

For agents:
- Must always pass a test-agent coverage check
- Must summarize what changed *and why*

---

## 🤖 Agent Rules for Refactoring

Agents may refactor only when:

- The original code is well understood  
- There are tests already covering the behavior  
- A planning step or intent explicitly authorizes the refactor

Agents must never:
- Blindly rename symbols across files
- Split logic into new files without planning
- Modify unrelated code "for style"

### Agent Output Example:
```md
# Refactor Summary: `src/auth/session.ts`

✓ Extracted `parseToken()` to clarify session validation logic  
✓ Removed unreachable fallback branch  
✓ Tests confirmed to pass
```

---

## 🚫 Anti-Patterns

- ❌ Refactor for the sake of activity
- ❌ "Might as well clean this up too" mid-feature
- ❌ Massive PRs that combine logic + cleanup
- ❌ Refactor without a before/after comparison

---

## 🧰 Suggested Prompt Usage

Use prompts like:
- "Safely refactor this function for readability"
- "Break this module into two files — explain the separation"
- "Remove dead branches and summarize what's changed"
- "Improve naming without altering behavior"

If the agent can't explain why the change is helpful — don't accept it.

---

## ✅ Philosophy

**Refactoring is editing code for the reader.**

Clean code is not just for the compiler — it's for the next mind that opens the file. Make sure they nod, not groan.