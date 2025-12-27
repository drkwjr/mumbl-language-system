# Wiki Station Extraction Prompt

**Purpose:** Parse Wikipedia-style station lists into normalized station records.

## Prompt contract

- Input: `source` metadata and `candidates` list of raw bullet entries.
- Output: JSON object with a single key `stations`.
- Each station:
  - `name` (string, required)
  - `stream_url` (string or null)
  - `homepage` (string or null)
  - `languages` (array of ISO-639-3 codes if known)
  - `tags` (array of strings)
  - `confidence` (0-1 float)

## Extraction rules

1) Do not invent stream URLs.
2) Keep unknown fields as null.
3) If uncertain, keep confidence <= 0.4.
4) Normalize tags to lowercase.
5) Use the few-shot output format as the exact schema template.

## Example output

```json
{
  "stations": [
    {
      "name": "Radio Example",
      "stream_url": null,
      "homepage": "https://example.com",
      "languages": ["aka"],
      "tags": ["talk", "news"],
      "confidence": 0.5
    }
  ]
}
```
