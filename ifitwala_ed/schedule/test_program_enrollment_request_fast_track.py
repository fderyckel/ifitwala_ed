from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.schedule import program_enrollment_request_fast_track as fast_track


class _FakeRequest:
    def __init__(self, *, name, student, status, validation_status, requires_override=0, request_kind="Academic"):
        self.name = name
        self.student = student
        self.status = status
        self.validation_status = validation_status
        self.requires_override = requires_override
        self.request_kind = request_kind
        self.comments = []

    def save(self, ignore_permissions=False):
        if self.status == "Submitted" and self.validation_status == "Not Validated":
            self.validation_status = "Valid"

    def reload(self):
        return self

    def add_comment(self, _comment_type, text):
        self.comments.append(text)


class TestProgramEnrollmentRequestFastTrack(TestCase):
    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.has_permission",
        return_value=True,
    )
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.db.get_value")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_all", return_value=["PER-003"])
    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.get_filtered_requests",
        return_value=(
            frappe._dict({"academic_year": "AY-2026"}),
            [
                {
                    "name": "PER-001",
                    "request_status": "Approved",
                    "validation_status": "Valid",
                    "requires_override": 0,
                },
                {
                    "name": "PER-002",
                    "request_status": "Submitted",
                    "validation_status": "Invalid",
                    "requires_override": 1,
                },
                {
                    "name": "PER-003",
                    "request_status": "Approved",
                    "validation_status": "Valid",
                    "requires_override": 0,
                },
            ],
        ),
    )
    def test_preview_counts_clean_invalid_and_materialized_requests(
        self,
        _mock_requests,
        _mock_get_all,
        mock_get_value,
        _mock_permissions,
    ):
        mock_get_value.return_value = {
            "year_start_date": "2026-08-01",
            "year_end_date": "2027-06-30",
        }

        summary = fast_track.preview_fast_track_requests(
            {"school": "SCH-1", "academic_year": "AY-2026", "latest_request_only": 1}
        )

        self.assertEqual(summary["counts"]["selected"], 3)
        self.assertEqual(summary["counts"]["ready_now"], 1)
        self.assertEqual(summary["counts"]["needs_override"], 1)
        self.assertEqual(summary["counts"]["already_materialized"], 1)
        self.assertEqual(summary["default_enrollment_date"], "2026-08-01")

    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.has_permission",
        return_value=True,
    )
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.db.get_value")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_all", return_value=["PER-003"])
    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.get_filtered_requests",
        return_value=(
            frappe._dict({"academic_year": "AY-2026"}),
            [
                {
                    "name": "PER-001",
                    "request_status": "Approved",
                    "validation_status": "Valid",
                    "requires_override": 0,
                },
                {
                    "name": "PER-002",
                    "request_status": "Submitted",
                    "validation_status": "Invalid",
                    "requires_override": 1,
                },
                {
                    "name": "PER-003",
                    "request_status": "Approved",
                    "validation_status": "Valid",
                    "requires_override": 0,
                },
            ],
        ),
    )
    def test_preview_counts_approve_only_focuses_on_approval_readiness(
        self,
        _mock_requests,
        _mock_get_all,
        mock_get_value,
        _mock_permissions,
    ):
        mock_get_value.return_value = {
            "year_start_date": "2026-08-01",
            "year_end_date": "2027-06-30",
        }

        summary = fast_track.preview_fast_track_requests(
            {"school": "SCH-1", "academic_year": "AY-2026", "latest_request_only": 1},
            action=fast_track.ACTION_APPROVE_ONLY,
        )

        self.assertEqual(summary["counts"]["selected"], 3)
        self.assertEqual(summary["counts"]["already_approved"], 1)
        self.assertEqual(summary["counts"]["needs_override"], 1)
        self.assertEqual(summary["counts"]["already_materialized"], 1)
        self.assertEqual(summary["default_enrollment_date"], "")

    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.has_permission",
        return_value=True,
    )
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.db.get_value")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_all", return_value=["PER-003"])
    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.get_filtered_requests",
        return_value=(
            frappe._dict({"academic_year": "AY-2026"}),
            [
                {
                    "name": "PER-001",
                    "request_status": "Approved",
                    "validation_status": "Valid",
                    "requires_override": 0,
                },
                {
                    "name": "PER-002",
                    "request_status": "Submitted",
                    "validation_status": "Valid",
                    "requires_override": 0,
                },
                {
                    "name": "PER-003",
                    "request_status": "Approved",
                    "validation_status": "Valid",
                    "requires_override": 0,
                },
            ],
        ),
    )
    def test_preview_counts_materialize_only_focuses_on_ready_approved_requests(
        self,
        _mock_requests,
        _mock_get_all,
        mock_get_value,
        _mock_permissions,
    ):
        mock_get_value.return_value = {
            "year_start_date": "2026-08-01",
            "year_end_date": "2027-06-30",
        }

        summary = fast_track.preview_fast_track_requests(
            {"school": "SCH-1", "academic_year": "AY-2026", "latest_request_only": 1},
            action=fast_track.ACTION_MATERIALIZE_ONLY,
        )

        self.assertEqual(summary["counts"]["selected"], 3)
        self.assertEqual(summary["counts"]["ready_to_materialize"], 1)
        self.assertEqual(summary["counts"]["not_ready"], 1)
        self.assertEqual(summary["counts"]["already_materialized"], 1)
        self.assertEqual(summary["default_enrollment_date"], "2026-08-01")

    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track._publish_progress")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track._finalize")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.materialize_program_enrollment_request")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.validate_program_enrollment_request")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_doc")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_all", return_value=[])
    def test_execute_fast_track_approves_and_materializes_only_clean_requests(
        self,
        _mock_get_all,
        mock_get_doc,
        mock_validate,
        mock_materialize,
        mock_finalize,
        _mock_publish,
    ):
        docs = {
            "PER-001": _FakeRequest(
                name="PER-001",
                student="STU-1",
                status="Draft",
                validation_status="Not Validated",
            ),
            "PER-002": _FakeRequest(
                name="PER-002",
                student="STU-2",
                status="Submitted",
                validation_status="Invalid",
                requires_override=1,
            ),
        }

        def _get_doc(_doctype, name):
            return docs[name]

        def _validate(name, force=0):
            docs[name].validation_status = "Invalid"
            docs[name].requires_override = 1

        mock_get_doc.side_effect = _get_doc
        mock_validate.side_effect = _validate
        mock_finalize.side_effect = lambda **kwargs: kwargs

        summary = fast_track._execute_fast_track(
            request_names=["PER-001", "PER-002"],
            enrollment_date="2026-08-01",
            target_user="staff@example.com",
            batch_mode=False,
            action=fast_track.ACTION_APPROVE_AND_MATERIALIZE,
        )

        self.assertEqual(summary["counts"]["approved_now"], 1)
        self.assertEqual(summary["counts"]["materialized"], 1)
        self.assertEqual(summary["counts"]["invalid"], 1)
        self.assertTrue(docs["PER-001"].comments)
        mock_materialize.assert_called_once_with("PER-001", enrollment_date="2026-08-01")

    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track._publish_progress")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track._finalize")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.materialize_program_enrollment_request")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.validate_program_enrollment_request")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_doc")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_all", return_value=[])
    def test_execute_fast_track_approve_only_stops_before_materialization(
        self,
        _mock_get_all,
        mock_get_doc,
        mock_validate,
        mock_materialize,
        mock_finalize,
        _mock_publish,
    ):
        docs = {
            "PER-001": _FakeRequest(
                name="PER-001",
                student="STU-1",
                status="Draft",
                validation_status="Not Validated",
            )
        }

        mock_get_doc.side_effect = lambda _doctype, name: docs[name]
        mock_finalize.side_effect = lambda **kwargs: kwargs

        summary = fast_track._execute_fast_track(
            request_names=["PER-001"],
            enrollment_date="",
            target_user="staff@example.com",
            batch_mode=False,
            action=fast_track.ACTION_APPROVE_ONLY,
        )

        self.assertEqual(summary["counts"]["approved_now"], 1)
        self.assertNotIn("materialized", summary["counts"])
        mock_validate.assert_not_called()
        mock_materialize.assert_not_called()

    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track._publish_progress")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track._finalize")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.materialize_program_enrollment_request")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.validate_program_enrollment_request")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_doc")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.get_all", return_value=[])
    def test_execute_fast_track_materialize_only_requires_approved_valid_requests(
        self,
        _mock_get_all,
        mock_get_doc,
        mock_validate,
        mock_materialize,
        mock_finalize,
        _mock_publish,
    ):
        docs = {
            "PER-001": _FakeRequest(
                name="PER-001",
                student="STU-1",
                status="Approved",
                validation_status="Valid",
            ),
            "PER-002": _FakeRequest(
                name="PER-002",
                student="STU-2",
                status="Submitted",
                validation_status="Valid",
            ),
        }

        mock_get_doc.side_effect = lambda _doctype, name: docs[name]
        mock_finalize.side_effect = lambda **kwargs: kwargs

        summary = fast_track._execute_fast_track(
            request_names=["PER-001", "PER-002"],
            enrollment_date="2026-08-01",
            target_user="staff@example.com",
            batch_mode=False,
            action=fast_track.ACTION_MATERIALIZE_ONLY,
        )

        self.assertEqual(summary["counts"]["materialized"], 1)
        self.assertEqual(summary["counts"]["blocked"], 1)
        mock_validate.assert_not_called()
        mock_materialize.assert_called_once_with("PER-001", enrollment_date="2026-08-01")

    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.has_permission")
    def test_get_fast_track_access_requires_request_write_and_enrollment_create_write(self, mock_has_permission):
        permissions = {
            ("Program Enrollment Request", "write"): True,
            ("Program Enrollment", "create"): True,
            ("Program Enrollment", "write"): False,
        }

        def _has_permission(doctype, ptype="read", user=None):
            return permissions.get((doctype, ptype), False)

        mock_has_permission.side_effect = _has_permission

        can_run, reason = fast_track._get_fast_track_access(user="counselor@example.com")

        self.assertFalse(can_run)
        self.assertIn("Program Enrollment", reason)

    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.enqueue")
    @patch("ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.db.get_value")
    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.has_permission",
        return_value=True,
    )
    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.get_filtered_requests",
        return_value=(
            frappe._dict({"academic_year": "AY-2026"}),
            [{"name": f"PER-{idx:03d}"} for idx in range(1, 103)],
        ),
    )
    @patch(
        "ifitwala_ed.schedule.program_enrollment_request_fast_track.frappe.session",
        frappe._dict({"user": "staff@example.com"}),
    )
    def test_run_fast_track_queues_large_batches(
        self,
        _mock_requests,
        _mock_permissions,
        mock_get_value,
        mock_enqueue,
    ):
        mock_get_value.return_value = {
            "year_start_date": "2026-08-01",
            "year_end_date": "2027-06-30",
        }

        result = fast_track.run_fast_track_requests(
            {"school": "SCH-1", "academic_year": "AY-2026", "latest_request_only": 1}
        )

        self.assertEqual(result["queued"], 1)
        self.assertEqual(result["request_count"], 102)
        self.assertTrue(mock_enqueue.called)
