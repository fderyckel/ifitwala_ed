# Org Communication Archive dev notes

## Audience summary contract
Story: add `audience_summary` alongside `audience_label` to enable compact scan-mode chips
in the list view and a stable detail header, without needing another API change for an expanded view.

### Where it appears
- `ifitwala_ed.api.org_communication_archive.get_org_communication_feed`
- `ifitwala_ed.api.org_communication_archive.get_org_communication_item`

### Payload shape
- `primary`: selected row for detail header (deterministic priority: Student Group, Team, School Scope, Global)
- `chips`: up to 2 recipient chips + overflow `+N`, plus exactly one scope chip
- `meta`: counts for audiences and recipients (use `audience_rows` to show `+N` badge)

### Abbreviations used for scope chips
- Organization: `Organization.abbr`
- School: `School.abbr`
- Student Group: `Student Group.student_group_abbreviation`
- Team: `Team.team_code` (fallback to team name)
- Global: `All`

### Notes
- `primary.scope_label` is intended for tooltips and expanded audience views.
- Comment counts already ignore empty notes and `visibility = 'Hidden'` in
  `communication_interaction.get_org_comm_interaction_summary`.
