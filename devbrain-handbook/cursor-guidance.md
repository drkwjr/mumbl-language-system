# 💻 Cursor Guidance

This guide explains how to use Cursor effectively inside your Dev Brain–enabled projects.

It's written for **you** — not just your agents.  
Use it to reduce friction, prompt with clarity, and stay in flow.

---

## 🧠 Cursor Is a Coding Assistant, Not a Psychic

Cursor is powerful — but it doesn't know what you *meant* unless you're explicit.

The more signal you give it:
- The better the suggestions
- The tighter the diffs
- The fewer broken assumptions

---

## ✍️ Writing Good Prompts

### ✅ Do:

- Be direct:  
  > "Add loading state to this component"  
  > "Extract this logic into a helper in the same folder"

- Use file references or function names:
  > "Match the pattern used in `authHandler.ts`"

- Add constraints:
  > "Update this logic but don't change the return type"

- Ask for a plan first:
  > "How would you restructure this to make it testable?"

- Include test or doc expectations:
  > "Make this change and also update the test file if needed"

---

### ❌ Avoid:

- Vague goals like:
  > "Clean this up"  
  > "Make this better"  
  > "What do you think of this?"

- Asking multiple things at once:
  > "Refactor this and add tests and improve the naming and also check perf"

- Letting it guess too much:
  > Don't assume it knows your file conventions, folder purpose, or naming strategy unless you've established that.

---

## 🧠 Let the System Guide You

With your Dev Brain config and `context/` files in place, Cursor becomes much more context-aware. But to take full advantage, you should:

- Reference prompt templates in `/prompts/` — or reuse them directly
- Keep `/context/features/` up to date so Cursor doesn't drift
- Start new ideas as Markdown planning docs so agents can scaffold correctly

---

## 🗺️ Cursor Prompt Patterns (Reusable)

| Intent | Prompt |
|--------|--------|
| 🧪 Add tests | "Add missing tests for untested branches in `userHandler.ts`" |
| 🧹 Refactor | "Refactor this handler for readability, but don't change functionality" |
| 🛠️ Fix a bug | "This returns null unexpectedly — fix and explain what changed" |
| 📈 Add feature | "Add a flag to disable email verification. Reflect this in tests." |
| 📄 Update docs | "Update `feature-auth-session.md` to reflect this change" |
| 🔍 Analyze | "What is the data flow through this function?" |
| 📉 Reduce scope | "Keep this change minimal — one function max" |

Store your favorites in `/prompts/` for reuse.

---

## 💡 Cursor Behavior Tips

- You can **lock files** (via comments or config) to prevent agents from editing them
- Cursor respects diffs — always review changes before clicking "Accept"
- Use the **ask-to-plan-first** approach when making broad changes

---

## ⚠️ What to Watch Out For

- Cursor sometimes **renames things unnecessarily**  
  → Add: "Do not rename any variables" if this is important

- Cursor will **create extra files** unless told not to  
  → Add: "Do not create new files unless absolutely necessary"

- Cursor doesn't track subtle business logic well  
  → Ask it to "explain what changed" before accepting refactors

- Agents might edit multiple files — review all affected paths before merge

---

## 🔄 Cursor + Agent Protocol (Best Practice)

1. Write prompt → keep it focused
2. Let Cursor respond with plan or diff
3. Review scope of changes
4. Accept or ask for revision
5. Run test-agent or check test coverage
6. Update `/context/` or prompt logs if major logic changes

---

## ✅ Philosophy

> **Your prompts shape the system's intelligence.**  
> Ask clearly. Accept intentionally. Maintain rhythm.

You don't have to be perfect — just consistent. Cursor + Dev Brain will take care of the rest.