# How to Write QA Rules

QA Rules are domain-specific validators that enforce business logic beyond basic JSON schema validation. They run after schema validation and catch state-specific requirements, edge cases, and business rules.

## When to Use QA Rules vs Schema

### Use JSON Schema for:
- Required fields (`jurisdiction`, `interest_rate`)
- Data types (`number`, `string`, `array`)
- Basic ranges (`0 <= interest_rate <= 40`)
- Enum values (`compounding: "simple" | "annual"`)

### Use QA Rules for:
- State-specific caps (CA interest rate ≤ 10%, NY ≤ 9%)
- Business logic (NY daily compounding after 2015)
- Complex validations (fee bracket continuity)
- Required explanations (minimum note length)
- Cross-field relationships

## Helper Utilities

Import from `backend/src/validators/qa-helpers.ts`:

```typescript
import { rangeCheck, assertPositive, assertDatePattern } from "../../../../backend/src/validators/qa-helpers.js";
```

### Available Helpers:
- `rangeCheck(value, min, max, fieldName)` - Validates numeric ranges
- `mustEqual(value1, value2, field1Name, field2Name)` - Ensures equality
- `assertEnum(value, allowedValues, fieldName)` - Validates enum values
- `assertRequired(value, fieldName)` - Checks required fields
- `assertPositive(value, fieldName)` - Ensures positive numbers
- `assertDatePattern(value, fieldName)` - Validates YYYY-MM-DD format

## Writing a QA Rule

### 1. Create the File
Place in `context/features/calculators/<calculator>/qaRules.ts`

### 2. Define Interface
```typescript
interface MyRule {
  jurisdiction: string;
  interest_rate: number;
  effective_date: string;
  // ... other fields
}
```

### 3. Implement Validation Function
```typescript
export default async function(ruleJson: MyRule): Promise<string[]> {
  const failures: string[] = [];
  const jurisdiction = ruleJson.jurisdiction;

  // State-specific validations
  if (jurisdiction === "CA") {
    failures.push(...rangeCheck(ruleJson.interest_rate, 0, 10, "interest_rate"));
  }

  // Business logic
  if (ruleJson.interest_rate > 7) {
    failures.push("Rate should not exceed 7% for most cases");
  }

  return failures;
}
```

### 4. Return String Array
- Return empty array `[]` for success
- Return array of error messages for failures
- Each message should be clear and actionable

## Common Patterns

### State-Specific Validation
```typescript
if (jurisdiction === "CA") {
  failures.push(...rangeCheck(rate, 0, 10, "interest_rate"));
} else if (jurisdiction === "NY") {
  failures.push(...rangeCheck(rate, 0, 9, "interest_rate"));
}
```

### Date Validation
```typescript
failures.push(...assertDatePattern(ruleJson.effective_date, "effective_date"));

const effectiveDate = new Date(ruleJson.effective_date);
const now = new Date();
if (effectiveDate > now) {
  failures.push("effective_date cannot be in the future");
}
```

### Array Validation
```typescript
if (!Array.isArray(ruleJson.exceptions)) {
  failures.push("exceptions must be an array");
}
```

### Required Explanations
```typescript
if (!ruleJson.notes || ruleJson.notes.length < 50) {
  failures.push("detailed notes required (minimum 50 characters)");
}
```

## Testing

### Unit Tests
Create `qaRules.test.ts` in the same directory:

```typescript
import qaRules from "./qaRules.js";

describe("My Calculator QA Rules", () => {
  it("should pass for valid rule", async () => {
    const result = await qaRules(validRule);
    expect(result).toEqual([]);
  });

  it("should fail for invalid rule", async () => {
    const result = await qaRules(invalidRule);
    expect(result).toContain("expected error message");
  });
});
```

### Manual Testing
Use the CLI to test specific rules:
```bash
npm run qa:rules -- --calculator judgment-interest-calculator --state CA
```

## Best Practices

1. **Keep functions small** - Use helper utilities to avoid repetition
2. **State-specific logic** - Always check jurisdiction first
3. **Clear error messages** - Explain what's wrong and how to fix
4. **Reasonable defaults** - Provide fallback validations for unknown states
5. **Document complex logic** - Add comments for business rules
6. **Test edge cases** - Include tests for boundary conditions

## Integration

QA Rules are automatically loaded by the pipeline:
1. Schema validation runs first
2. If schema passes, QA Rules run
3. Both failure arrays are combined
4. Rule is flagged for review if any failures exist

## Debugging

- Check `backend/src/pipelines/rule-harvest/lib/qa-loader.ts` for loading issues
- Verify TypeScript compilation with `npx tsc --noEmit`
- Run unit tests with `npm test`
- Check pipeline logs for execution errors