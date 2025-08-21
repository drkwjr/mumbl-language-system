# ✨ Coding Style Guide

This guide defines the baseline code style rules for all Dev Brain–enabled projects. It enforces consistency, clarity, and legibility — optimized for both human and AI collaboration.

> You don't need to obsess over style. You just need to not break it.

---

## 🧱 General Philosophy

- **Readable > Clever** — prioritize clarity over brevity or abstraction.
- **Small is strong** — small functions, small files, small scopes.
- **Consistent wins** — follow the rhythm of the existing codebase.
- **Less config, more convention** — avoid overengineering unless necessary.
- **Agents write too** — style should be easy for AI to mimic predictably.

---

## 🔤 Naming Conventions

- **Variables:** `camelCase` for JS/TS, `snake_case` for Python
- **Constants:** `ALL_CAPS_WITH_UNDERSCORES` only when immutably global
- **Functions:** `verbNoun` format (e.g. `getUser`, `createSession`)
- **Files:** 
  - Use `kebab-case` for file names (`create-user.ts`)
  - Match file name to exported function or component
- **Directories:** use plural nouns (`/utils`, `/routes`, `/services`)

---

## 📁 File Organization

- **One logical unit per file.** If a file does more than one thing, break it.
- **Order inside files:**
  1. Imports
  2. Constants
  3. Main function(s)
  4. Helpers
  5. Exports

Use vertical whitespace for separation, but don't overdo it.

---

## 🧪 Function Structure

- Functions should be **short and focused**. Prefer under ~40 LOC per function.
- Avoid deep nesting — use early returns or guard clauses:
  
```ts
if (!user) return null;
```

- Prefer explicit parameters over passing entire objects unless justified.
- Don't be afraid to break things into tiny helpers — especially when they improve testability.

---

## 💬 Comments & Annotations

- Avoid obvious comments.

Instead of:
```ts
// increment i
i += 1;
```
Just write readable code.

- Use comments for intent, not what the code does.

Example:
```ts
// This needs to happen before auth middleware attaches headers
setupCookies();
```

- AI-facing comments (like for doc-agent) should:
  - Be high-level and declarative
  - Include reasoning when appropriate  
  - Avoid hand-waving or vague phrasing

---

## ✨ Code Patterns to Prefer

- Use composition over inheritance
- Avoid deep object mutation — prefer pure functions where possible
- Default to async/await, not .then() chaining
- Use TypeScript types or Python type hints to clarify intent
- Don't optimize prematurely, but do avoid obviously poor patterns

---

## 🛑 Anti-Patterns to Avoid

- `utils.ts` files with unrelated logic — break them into domains
- Mega-functions or 1,000-line files
- Deep ternary chains or nested conditionals
- Empty placeholder files or functions
- Unused arguments or magic numbers

---

## 🪶 Light Preferences

These are flexible but encouraged:
- Prefer `for...of` over `forEach`
- Inline small conditionals:
```ts
return isValid ? user : null;
```
- Prefer named exports unless the file has a single purpose

---

## ✅ Linting and Formatting

- Use Prettier for formatting
- Use ESLint or Ruff (for Python) with sensible defaults
- Let agents follow these tools' outputs for consistency
- If linters conflict with clarity — choose clarity

---

## 🧠 Notes for Agents

When AI agents write code:
- They must follow the structure and naming of existing modules
- They must default to readable, modular patterns
- They must not introduce random abstractions or generic helpers without a clear purpose
- If unsure, agents should suggest, not assume

---

## 🌟 Style in One Sentence

**Code should read like an answer, not a riddle.**

If a senior engineer reads your code and can nod without squinting — you've done it right.