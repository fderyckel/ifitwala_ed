# ifitwala_ed/website/tests/test_vite_utils.py

import json
import os
import tempfile
import time
import unittest

from ifitwala_ed.website import vite_utils


class TestViteUtils(unittest.TestCase):
    def setUp(self):
        vite_utils._VITE_MANIFEST_CACHE.clear()
        vite_utils._WEBSITE_BUNDLE_CACHE.clear()

    def tearDown(self):
        vite_utils._VITE_MANIFEST_CACHE.clear()
        vite_utils._WEBSITE_BUNDLE_CACHE.clear()

    def test_get_vite_assets_includes_recursive_import_css(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = os.path.join(temp_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "src/apps/portal/main.ts": {
                            "file": "assets/main.AAAAAAAA.js",
                            "isEntry": True,
                            "css": ["assets/main.AAAAAAAA.css"],
                            "imports": ["_shared.BBBBBBBB.js"],
                        },
                        "_shared.BBBBBBBB.js": {
                            "file": "assets/shared.BBBBBBBB.js",
                            "css": ["assets/shared.BBBBBBBB.css"],
                            "imports": ["_deep.CCCCCCCC.js"],
                        },
                        "_deep.CCCCCCCC.js": {
                            "file": "assets/deep.CCCCCCCC.js",
                            "css": ["assets/deep.CCCCCCCC.css"],
                        },
                    },
                    handle,
                )

            js_entry, css_urls, preload_urls = vite_utils.get_vite_assets(
                app_name="ifitwala_ed",
                manifest_paths=[manifest_path],
                public_base="/assets/ifitwala_ed/vite/",
                entry_keys=["src/apps/portal/main.ts"],
            )

        self.assertEqual(js_entry, "/assets/ifitwala_ed/vite/assets/main.AAAAAAAA.js")
        self.assertEqual(
            css_urls,
            [
                "/assets/ifitwala_ed/vite/assets/main.AAAAAAAA.css",
                "/assets/ifitwala_ed/vite/assets/shared.BBBBBBBB.css",
                "/assets/ifitwala_ed/vite/assets/deep.CCCCCCCC.css",
            ],
        )
        self.assertEqual(
            preload_urls,
            [
                "/assets/ifitwala_ed/vite/assets/shared.BBBBBBBB.js",
                "/assets/ifitwala_ed/vite/assets/deep.CCCCCCCC.js",
            ],
        )

    def test_load_manifest_reuses_last_good_manifest_during_partial_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = os.path.join(temp_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "src/apps/portal/main.ts": {
                            "file": "assets/main.AAAAAAAA.js",
                            "isEntry": True,
                        }
                    },
                    handle,
                )

            js_entry, _, _ = vite_utils.get_vite_assets(
                app_name="ifitwala_ed",
                manifest_paths=[manifest_path],
                public_base="/assets/ifitwala_ed/vite/",
                entry_keys=["src/apps/portal/main.ts"],
            )
            self.assertEqual(js_entry, "/assets/ifitwala_ed/vite/assets/main.AAAAAAAA.js")

            time.sleep(0.001)
            with open(manifest_path, "w", encoding="utf-8") as handle:
                handle.write("{")

            js_entry, _, _ = vite_utils.get_vite_assets(
                app_name="ifitwala_ed",
                manifest_paths=[manifest_path],
                public_base="/assets/ifitwala_ed/vite/",
                entry_keys=["src/apps/portal/main.ts"],
            )

        self.assertEqual(js_entry, "/assets/ifitwala_ed/vite/assets/main.AAAAAAAA.js")

    def test_get_website_bundle_urls_prefers_newest_hash_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            css_dir = os.path.join(temp_dir, "css")
            js_dir = os.path.join(temp_dir, "js")
            os.makedirs(css_dir)
            os.makedirs(js_dir)

            old_css = os.path.join(css_dir, "ifitwala_site.aaaaaaaa.bundle.css")
            new_css = os.path.join(css_dir, "ifitwala_site.bbbbbbbb.bundle.css")
            old_js = os.path.join(js_dir, "ifitwala_site.aaaaaaaa.bundle.js")
            new_js = os.path.join(js_dir, "ifitwala_site.bbbbbbbb.bundle.js")

            for path in (old_css, old_js):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("old")

            time.sleep(0.001)

            for path in (new_css, new_js):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("new")

            css_url, js_url = vite_utils.get_website_bundle_urls(
                app_public_dir=temp_dir,
                public_base="/assets/ifitwala_ed/",
            )

        self.assertEqual(css_url, "/assets/ifitwala_ed/css/ifitwala_site.bbbbbbbb.bundle.css")
        self.assertEqual(js_url, "/assets/ifitwala_ed/js/ifitwala_site.bbbbbbbb.bundle.js")

    def test_get_website_bundle_urls_invalidates_when_hash_bundle_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            css_dir = os.path.join(temp_dir, "css")
            js_dir = os.path.join(temp_dir, "js")
            os.makedirs(css_dir)
            os.makedirs(js_dir)

            with open(
                os.path.join(css_dir, "ifitwala_site.aaaaaaaa.bundle.css"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("css-v1")
            with open(
                os.path.join(js_dir, "ifitwala_site.aaaaaaaa.bundle.js"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("js-v1")

            first = vite_utils.get_website_bundle_urls(
                app_public_dir=temp_dir,
                public_base="/assets/ifitwala_ed/",
            )

            time.sleep(0.001)
            with open(
                os.path.join(css_dir, "ifitwala_site.bbbbbbbb.bundle.css"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("css-v2")
            with open(
                os.path.join(js_dir, "ifitwala_site.bbbbbbbb.bundle.js"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("js-v2")

            second = vite_utils.get_website_bundle_urls(
                app_public_dir=temp_dir,
                public_base="/assets/ifitwala_ed/",
            )

        self.assertEqual(
            first,
            (
                "/assets/ifitwala_ed/css/ifitwala_site.aaaaaaaa.bundle.css",
                "/assets/ifitwala_ed/js/ifitwala_site.aaaaaaaa.bundle.js",
            ),
        )
        self.assertEqual(
            second,
            (
                "/assets/ifitwala_ed/css/ifitwala_site.bbbbbbbb.bundle.css",
                "/assets/ifitwala_ed/js/ifitwala_site.bbbbbbbb.bundle.js",
            ),
        )
