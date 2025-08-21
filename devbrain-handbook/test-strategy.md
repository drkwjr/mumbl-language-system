# ✅ Test Strategy

This file defines when, where, and how to write tests in Dev Brain–enabled projects — for both you and the agents.

> The goal is **confidence without clutter**.  
> Tests should prove value, not pad numbers.

---

## 🎯 Purpose of Testing

- Prevent regressions
- Expose edge cases
- Guide future contributors (and agents)
- Make refactoring fearless

---

## 🧪 Test Expectations

### Core Rules:

| Type                      | Required?     | Notes                                       |
| ------------------------- | ------------- | ------------------------------------------- |
| **Business logic**        | ✅ Required   | Anything affecting user behavior            |
| **Data mutations**        | ✅ Required   | Any function that changes app state         |
| **Pure utils**            | ✅ Encouraged | Especially if reused in >1 place            |
| **Rendering/UI**          | ⚠️ Optional   | Smoke tests are good; full coverage is rare |
| **Third-party wrappers**  | ❌ Skip       | Don't test what isn't yours                 |
| **Experimental features** | ⚠️ Optional   | Document instead of testing for now         |

---

## 🔍 Types of Tests

| Type                  | Description                                     | Tooling                               |
| --------------------- | ----------------------------------------------- | ------------------------------------- |
| **Unit Tests**        | One function, one outcome                       | `jest`, `vitest`, `pytest`            |
| **Integration Tests** | Modules working together (e.g. controller + DB) | `supertest`, `Playwright`, `requests` |
| **Regression Tests**  | Locked-in outputs for legacy logic              | Snapshots, expected results           |
| **Validation Tests**  | Edge cases, schema checks                       | Zod, Yup, Pydantic validation layers  |

---

## 📁 Folder Structure & Placement

- Use `/__tests__/` to mirror the `/src/` tree
- Keep test files named the same as the module they test:

```
/src/users/create.ts
/__tests__/users/create.test.ts
```

- Do not place tests inside `/src/` unless required by framework.

---

## ✍️ Naming & Format

- Use clear, intent-based test names:

```ts
it("returns null if user is not found", ...)
```

- Group related cases using describe blocks
- Prefer readability over brevity — your test file is also documentation

---

## 🤖 Agent Responsibilities

When agents are called via test-agent or related prompts, they must:

- Check for existing tests before generating new ones
- Suggest new tests only for untested paths or edge cases
- Never write "placeholder" tests with no asserts
- Never suggest 100% coverage if 80% well-targeted tests are sufficient

When in doubt, agents should explain test rationale first.

---

## 🚨 Red Flags (What Not to Do)

- Duplicate tests with slightly different values
- Giant catch-all `utils.test.ts`
- Commented-out tests (delete them!)
- Tests that assert truthiness without meaning:

```ts
expect(result).toBeTruthy(); // ❌
```

- Test files with 5% meaningful coverage and 95% noise

---

## 🧠 Strategic Coverage Targets

| Zone                               | Coverage Goal            |
| ---------------------------------- | ------------------------ |
| Core logic (e.g. auth, billing)    | 90–100%                  |
| Data services (e.g. CRUD handlers) | 80–90%                   |
| UI logic / rendering               | 50–70% (optional)        |
| Utility modules                    | 70–90%                   |
| Experimental or new code           | Best-effort w/ good docs |

These are goals, not dogma. Prioritize meaningful branches.

---

## 🪄 AI-Powered Testing Prompts (Examples)

You can say:

- "Add missing tests for the /users/create handler"
- "Why doesn't this test catch the bug?"
- "Check if this module needs more test coverage"
- "Write a regression test for this specific failure"

Use the test-agent for these cases — it understands the context.

---

## 📘 Summary

**Tests are the narrative of your logic.**

If something matters, prove it. If something doesn't, don't fake it.

You don't need 100% coverage — you need strategic confidence.

---

## 💡 Resilient Prompt Assertions (LLM-driven code)

LLM prompt templates evolve often, causing brittle exact-string checks to break. Follow these rules to keep tests stable:

1. **Assert intent, not prose**  
   Use section headers, JSON keys, or key phrases that are unlikely to change (`"PLATFORM"`, `"CANDIDATE_SCORING"`) instead of full paragraph matches.
2. **Case-insensitive helpers**  
   Create utilities such as `expect(text.toLowerCase()).toContain('keyword')` or a shared `expectIncludesCI()` to avoid casing variations.
3. **Import constants**  
   When wording _must_ be locked, export the string from the source module (`src/prompts/**`) and import it in the test, so changes propagate automatically.
4. **Avoid snapshot bloat**  
   Snapshots of entire prompts become stale quickly; snapshot only the critical sections or use inline expectations.

Keeping expectations flexible ensures prompt improvements don't break CI for purely cosmetic reasons, while still guarding important contract elements.

---

## 🟢 Current Baseline (CI)

As of July 2025 the full unit-test suite runs in ~2 s with:

| Metric            | Count                           |
| ----------------- | ------------------------------- |
| Test files        | **14**                          |
| Tests             | **132** (130 passed, 2 skipped) |
| Coverage provider | v8                              |

CI will show a green check when these numbers hold or improve.
