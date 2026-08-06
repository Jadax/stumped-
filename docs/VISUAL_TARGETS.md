# Visual target map

The supplied Cricket Captain screenshots are layout references, not copied
assets. The target is a modern, readable Godot presentation with the same
information hierarchy:

- **Match Day:** score header, innings card, batter/bowler perspective panel,
  live pitch/shot map, ball tracker, commentary, and compact decision controls.
- **Player profile:** identity header, current-match analytics, career records,
  batting/bowling form, shot maps, and a persistent back/section rail.
- **Team hub:** team identity, latest result, next fixture, squad health,
  finances, training and board objectives in a bento grid.
- **Selection:** full squad table with role/fitness/form/morale, XI slots,
  conditions, tactical recommendations, and a clear confirm action.
- **Competitions:** group standings, domestic tables, fixtures, and bracket
  stages with promotion/relegation or qualification zones clearly marked.

## Implementation order

1. Match Day (highest frequency and current v4.35 foundation).
2. Player profile and records (reusable analytics widgets).
3. Selection and team hub (manager decision flow).
4. Domestic/international competition views.
5. Final responsive and accessibility pass at 1280x720 and 4K.

Use AppTheme tokens for colours, spacing and typography. New screens should
compose existing widgets rather than introduce another visual language.
