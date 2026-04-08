# ifitwala_ed/api/test_org_communication_interactions.py

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from ifitwala_ed.api import org_communication_interactions
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    DOCTYPE as ENTRY_DOCTYPE,
)


class TestOrgCommunicationReadReceiptUpsert(FrappeTestCase):
    def test_upsert_retries_deadlock_and_succeeds(self):
        class QueryDeadlockError(Exception):
            pass

        read_at = now_datetime()
        with (
            patch("ifitwala_ed.api.org_communication_interactions.frappe.cache") as cache_mock,
            patch(
                "ifitwala_ed.api.org_communication_interactions.frappe.db.sql",
                side_effect=[QueryDeadlockError("deadlock"), None],
            ) as sql_mock,
            patch(
                "ifitwala_ed.api.org_communication_interactions.frappe.generate_hash",
                side_effect=["receipt-a", "receipt-b", "receipt-c"],
            ),
            patch("ifitwala_ed.api.org_communication_interactions.time.sleep") as sleep_mock,
        ):
            cache_mock.return_value.lock.return_value = nullcontext()
            org_communication_interactions._upsert_portal_read_receipt(
                user="guardian@example.com",
                reference_name="COMM-0001",
                read_at=read_at,
            )

        self.assertEqual(sql_mock.call_count, 2)
        sleep_mock.assert_called_once_with(org_communication_interactions.READ_RECEIPT_RETRY_BASE_DELAY_SEC)

    def test_upsert_raises_non_deadlock_errors(self):
        read_at = now_datetime()
        with (
            patch("ifitwala_ed.api.org_communication_interactions.frappe.cache") as cache_mock,
            patch(
                "ifitwala_ed.api.org_communication_interactions.frappe.db.sql",
                side_effect=RuntimeError("db failure"),
            ),
            patch(
                "ifitwala_ed.api.org_communication_interactions.frappe.generate_hash",
                return_value="receipt-a",
            ),
        ):
            cache_mock.return_value.lock.return_value = nullcontext()
            with self.assertRaises(RuntimeError):
                org_communication_interactions._upsert_portal_read_receipt(
                    user="guardian@example.com",
                    reference_name="COMM-0001",
                    read_at=read_at,
                )


class TestOrgCommunicationSeenNames(FrappeTestCase):
    def test_seen_names_include_read_receipts_and_self_interactions(self):
        def fake_get_all(doctype, **kwargs):
            if doctype == org_communication_interactions.READ_RECEIPT_DOCTYPE:
                return [{"reference_name": "COMM-READ"}]
            if doctype == ENTRY_DOCTYPE:
                return [{"org_communication": "COMM-INTERACT"}]
            return []

        with patch("ifitwala_ed.api.org_communication_interactions.frappe.get_all", side_effect=fake_get_all):
            seen = org_communication_interactions.get_seen_org_communication_names(
                user="guardian@example.com",
                communication_names=["COMM-READ", "COMM-INTERACT", "COMM-UNREAD"],
            )

        self.assertEqual(seen, {"COMM-READ", "COMM-INTERACT"})


class TestOrgCommunicationSummaryContract(FrappeTestCase):
    def test_summary_uses_entry_rows_for_reactions_counts_and_self(self):
        reaction_row = {
            "name": "ENTRY-REACTION",
            "org_communication": "COMM-0001",
            "user": "staff@example.com",
            "intent_type": "Acknowledged",
            "reaction_code": "like",
            "note": None,
            "visibility": "Public to audience",
            "creation": now_datetime(),
            "modified": now_datetime(),
        }
        self_row = {
            "name": "ENTRY-SELF",
            "org_communication": "COMM-0001",
            "user": "staff@example.com",
            "audience_type": "Staff",
            "surface": "Morning Brief",
            "intent_type": "Comment",
            "reaction_code": None,
            "note": "Seen",
            "visibility": "Public to audience",
            "is_teacher_reply": 0,
            "is_pinned": 0,
            "is_resolved": 0,
            "creation": now_datetime(),
            "modified": now_datetime(),
        }

        with (
            patch(
                "ifitwala_ed.api.org_communication_interactions._actor_context",
                return_value=("staff@example.com", {"Academic Staff"}, {"name": "EMP-1", "school": "SCH-1"}),
            ),
            patch(
                "ifitwala_ed.api.org_communication_interactions._visible_names_for_user",
                return_value=["COMM-0001"],
            ),
            patch(
                "ifitwala_ed.api.org_communication_interactions._reaction_row_query",
                return_value=[reaction_row],
            ),
            patch(
                "ifitwala_ed.api.org_communication_interactions._comment_counts",
                return_value={"COMM-0001": 2},
            ),
            patch(
                "ifitwala_ed.api.org_communication_interactions._latest_user_rows",
                return_value={"COMM-0001": self_row},
            ),
        ):
            summary = org_communication_interactions.get_org_communication_interaction_summary(["COMM-0001"])

        self.assertEqual(summary["COMM-0001"]["reaction_counts"]["like"], 1)
        self.assertEqual(summary["COMM-0001"]["reactions_total"], 1)
        self.assertEqual(summary["COMM-0001"]["comments_total"], 2)
        self.assertEqual(summary["COMM-0001"]["counts"]["Comment"], 2)
        self.assertEqual(summary["COMM-0001"]["self"]["name"], "ENTRY-SELF")
        self.assertEqual(summary["COMM-0001"]["self"]["reaction_code"], "like")


class TestOrgCommunicationVisibilityGuards(FrappeTestCase):
    def test_ensure_visible_org_communication_allows_creator_override(self):
        with (
            patch("ifitwala_ed.api.org_communication_interactions.frappe.db.exists", return_value=True),
            patch(
                "ifitwala_ed.api.org_communication_interactions.check_audience_match",
                return_value=True,
            ) as audience_match_mock,
        ):
            org_communication_interactions._ensure_visible_org_communication(
                "COMM-0001",
                user="teacher@example.com",
                roles={"Instructor"},
                employee={"name": "EMP-1", "school": "SCH-1"},
            )

        audience_match_mock.assert_called_once_with(
            "COMM-0001",
            "teacher@example.com",
            {"Instructor"},
            {"name": "EMP-1", "school": "SCH-1"},
            allow_owner=True,
        )

    def test_visible_names_for_user_passes_creator_override(self):
        with patch(
            "ifitwala_ed.api.org_communication_interactions.check_audience_match",
            side_effect=[True, False],
        ) as audience_match_mock:
            visible = org_communication_interactions._visible_names_for_user(
                ["COMM-0001", "COMM-0002"],
                user="teacher@example.com",
                roles={"Instructor"},
                employee={"name": "EMP-1", "school": "SCH-1"},
            )

        self.assertEqual(visible, ["COMM-0001"])
        self.assertEqual(len(audience_match_mock.call_args_list), 2)
        self.assertEqual(audience_match_mock.call_args_list[0].kwargs, {"allow_owner": True})
        self.assertEqual(audience_match_mock.call_args_list[1].kwargs, {"allow_owner": True})


class TestOrgCommunicationWorkflowEndpoints(FrappeTestCase):
    def test_react_endpoint_maps_reaction_to_intent(self):
        with (
            patch(
                "ifitwala_ed.api.org_communication_interactions._actor_context",
                return_value=("staff@example.com", {"Academic Staff"}, {"name": "EMP-1", "school": "SCH-1"}),
            ),
            patch("ifitwala_ed.api.org_communication_interactions._ensure_visible_org_communication"),
            patch(
                "ifitwala_ed.api.org_communication_interactions.create_interaction_entry",
                return_value={"name": "ENTRY-0001"},
            ) as create_entry_mock,
        ):
            result = org_communication_interactions.react_to_org_communication(
                org_communication="COMM-0001",
                reaction_code="like",
                surface="Morning Brief",
            )

        create_entry_mock.assert_called_once_with(
            org_communication="COMM-0001",
            user="staff@example.com",
            reaction_code="like",
            intent_type="Acknowledged",
            surface="Morning Brief",
        )
        self.assertEqual(result, {"name": "ENTRY-0001"})

    def test_post_comment_uses_named_comment_workflow(self):
        with (
            patch(
                "ifitwala_ed.api.org_communication_interactions._actor_context",
                return_value=("guardian@example.com", {"Guardian"}, {}),
            ),
            patch("ifitwala_ed.api.org_communication_interactions._ensure_visible_org_communication"),
            patch(
                "ifitwala_ed.api.org_communication_interactions.create_interaction_entry",
                return_value={"name": "ENTRY-0002"},
            ) as create_entry_mock,
        ):
            result = org_communication_interactions.post_org_communication_comment(
                org_communication="COMM-0002",
                note="Thanks for the update",
                surface="Guardian Portal",
            )

        create_entry_mock.assert_called_once_with(
            org_communication="COMM-0002",
            user="guardian@example.com",
            intent_type="Comment",
            note="Thanks for the update",
            surface="Guardian Portal",
        )
        self.assertEqual(result, {"name": "ENTRY-0002"})

    def test_structured_feedback_thread_is_hidden_from_non_staff(self):
        with (
            patch(
                "ifitwala_ed.api.org_communication_interactions._actor_context",
                return_value=("guardian@example.com", {"Guardian"}, {}),
            ),
            patch("ifitwala_ed.api.org_communication_interactions._ensure_visible_org_communication"),
            patch(
                "ifitwala_ed.api.org_communication_interactions.frappe.get_cached_doc",
                return_value=SimpleNamespace(interaction_mode="Structured Feedback"),
            ),
        ):
            rows = org_communication_interactions.get_org_communication_thread("COMM-0003")

        self.assertEqual(rows, [])
