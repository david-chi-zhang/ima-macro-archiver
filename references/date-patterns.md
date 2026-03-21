# Date Detection Patterns

## Supported Formats

### Month + Year (Best)
```
"in February 2026" → 2026-02
"in Q4 2025" → 2025-12
"January 2026" → 2026-01
```

### Month Only (Use Current Year)
```
"in February" → 2026-02 (if current year is 2026)
"February reading" → 2026-02
"February data" → 2026-02
```

### Quarter
```
"in Q1 2026" → 2026-03
"in Q2 2025" → 2025-06
"in Q3 2025" → 2025-09
"in Q4 2025" → 2025-12
```

### ISO Date
```
"2026-02-15" → 2026-02
"released on 2026-01-20" → 2026-01
```

### Relative
```
"previous month" → Current - 1
"last month" → Current - 1
```

## Examples

| Text | Detected |
|------|----------|
| "PMI fell to 51.6 in February 2026" | 2026-02 |
| "GDP grew 0.3% in Q4 2025" | 2025-12 |
| "in January" | 2026-01 |
| "February reading" | 2026-02 |
| "released on 2026-02-15" | 2026-02 |
| "previous month" | 2026-02 (if current is March) |

## Usage

```bash
python3 scripts/detect_date.py "PMI fell in February 2026"
# Output: 2026-02
```
