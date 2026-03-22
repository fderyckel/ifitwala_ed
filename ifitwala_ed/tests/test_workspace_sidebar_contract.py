import json
from pathlib import Path
from unittest import TestCase


class TestWorkspaceSidebarContract(TestCase):
    def test_workspace_sidebar_workspace_links_resolve(self):
        app_root = Path(__file__).resolve().parents[1]
        workspace_names = {
            json.loads(path.read_text()).get("name")
            for path in app_root.glob("**/workspace/*/*.json")
            if json.loads(path.read_text()).get("doctype") == "Workspace"
        }

        missing_targets: list[str] = []

        for sidebar_path in sorted((app_root / "workspace_sidebar").glob("*.json")):
            sidebar = json.loads(sidebar_path.read_text())
            for item in sidebar.get("items", []):
                if item.get("link_type") != "Workspace":
                    continue
                target = item.get("link_to")
                if target not in workspace_names:
                    missing_targets.append(f"{sidebar_path.name}: {target}")

        self.assertFalse(
            missing_targets,
            "Workspace Sidebar items reference missing Workspace records: " + ", ".join(missing_targets),
        )
