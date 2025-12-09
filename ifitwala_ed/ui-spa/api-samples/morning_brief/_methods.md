# Morning Brief backend methods

Source of truth: `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue` (createResource/call usage) and `ifitwala_ed/ui-spa/src/components/HistoryDialog.vue`.

- `ifitwala_ed.api.morning_brief.get_briefing_widgets` — GET (via `createResource.fetch`, auto) — returns the full Morning Brief widget payload (announcements, birthdays, analytics, attendance, logs) tailored to the signed-in user; see `ifitwala_ed/api/morning_brief.py`.
- `ifitwala_ed.api.morning_brief.get_critical_incidents_details` — GET (via `createResource.fetch`) — returns open Student Log entries that require follow up for the user’s school; defined in `ifitwala_ed/api/morning_brief.py`.
- `ifitwala_ed.api.morning_brief.get_clinic_visits_trend` — GET (via `HistoryDialog` resource `fetch`) — returns clinic visit counts over a selectable time window (1M/3M/6M/YTD); defined in `ifitwala_ed/api/morning_brief.py`.
- `ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_org_comm_interaction_summary` — POST (via `createResource.submit` with `comm_names`) — returns per-announcement interaction aggregates plus the current user’s own interaction, from `ifitwala_ed/setup/doctype/communication_interaction/communication_interaction.py`.
- `ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_communication_thread` — GET (via `createResource.fetch`) — returns the visible interaction thread for an Org Communication, filtered by interaction_mode/visibility rules; defined in `ifitwala_ed/setup/doctype/communication_interaction/communication_interaction.py`.
- `ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.upsert_communication_interaction` — POST (via `call`) — creates or updates the current user’s interaction (acknowledge/comment/etc.) on an Org Communication; defined in `ifitwala_ed/setup/doctype/communication_interaction/communication_interaction.py`.
