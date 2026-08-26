# Summary

- Adds exact, inclusive `measurement_start` and `measurement_end` dates to report builds.
- Filters daily Meta metrics, content exports, and ZoomSphere rows to the resolved range before KPI calculation.
- Adds campaign status pages and visible period-accuracy warnings to the editable HTML report.
- Keeps existing calendar-month projects backward compatible when exact dates cannot be resolved.

# Period precedence

The engine resolves one authoritative interval in this order:

1. a complete manager-supplied start/end pair;
2. a common date window detected in daily source exports;
3. the Meta Ads reporting window;
4. the calendar month as an explicit `assumed` fallback.

A one-sided manager value is ignored instead of creating a half-defined period. The closing date determines the report's `YYYY-MM` period identifier. Continuity checks use exact adjacent dates when both reports contain measurement boundaries.

# Filtering rules

- Both boundary dates are included.
- Daily series and content rows are filtered before totals, joins, rankings, and comparisons are calculated.
- ZoomSphere content is filtered by publication date.
- A standard monthly measurement lasts 27-32 inclusive days. Gaps, overlaps, nonstandard lengths, and assumed dates remain buildable but are surfaced through `measurement_credibility`.
- Daily source windows that cannot support the resolved interval still fail validation rather than silently producing incomplete totals.

# Meta Ads and campaign truth boundaries

Meta Ads totals are never prorated. When the Ads export covers a different window, its complete totals remain in the report as indicative values with the actual query dates and a visible warning. Boost matching is only strict when the Ads window exactly matches the report interval.

Campaign start date, end date, delivery status, ongoing state, result type, and result count come directly from the export and are locked report data. Only the campaign-section headline and explanatory narrative are editable. Missing dates remain missing; the narrative layer cannot invent them.

# Tests

Verified on the upstream branch before review:

```text
git status --short
git diff --check origin/master...HEAD
python -m pytest -q
```

Result: clean worktree, no whitespace errors, `427 passed, 1 deselected in 28.11s`.
