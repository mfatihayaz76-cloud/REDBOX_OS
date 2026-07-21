import hashlib
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from application_metadata import (
    APP_BUILD,
    APP_DISPLAY_NAME,
    APP_VERSION,
    BUNDLE_IDENTIFIER,
)
from runtime_environment import (
    configure_runtime_logging,
    install_exception_hooks,
    runtime_directories,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class DistributionRuntimeContractTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.assertEqual(
            hashlib.sha256(LIVE_DB.read_bytes()).hexdigest(),
            self.live_sha,
        )

    def test_professional_application_metadata(self):
        self.assertEqual(APP_DISPLAY_NAME, "REDBOX OS")
        self.assertRegex(
            APP_VERSION,
            r"^[0-9]+\.[0-9]+\.[0-9]+$",
        )
        self.assertRegex(APP_BUILD, r"^[1-9][0-9]*$")
        self.assertEqual(
            BUNDLE_IDENTIFIER,
            "com.redboxgida.redboxos",
        )

    def test_development_runtime_directories_are_project_safe(self):
        paths = runtime_directories(
            frozen=False,
            platform_name="darwin",
            home=Path("/tmp/example-home"),
            project_root=PROJECT_ROOT,
            environment={},
        )
        self.assertEqual(
            paths["data"],
            PROJECT_ROOT / "database",
        )
        self.assertEqual(
            paths["logs"],
            PROJECT_ROOT / "logs",
        )
        self.assertEqual(
            paths["crashes"],
            PROJECT_ROOT / "logs" / "crashes",
        )

    def test_packaged_macos_uses_application_support(self):
        home = Path("/Users/example")
        paths = runtime_directories(
            frozen=True,
            platform_name="darwin",
            home=home,
            project_root=PROJECT_ROOT,
            environment={},
        )
        base = (
            home
            / "Library"
            / "Application Support"
            / "REDBOX_OS"
        )
        self.assertEqual(paths["data"], base)
        self.assertEqual(paths["logs"], base / "logs")
        self.assertEqual(
            paths["crashes"],
            base / "logs" / "crashes",
        )

    def test_runtime_logging_creates_rotating_log(self):
        with tempfile.TemporaryDirectory() as temp:
            log_dir = Path(temp) / "logs"
            result = configure_runtime_logging(log_dir)
            try:
                logging.getLogger(
                    "redbox.contract"
                ).warning("contract-event")
                for handler in result["handlers"]:
                    handler.flush()

                self.assertTrue(result["log_path"].is_file())
                self.assertIn(
                    "contract-event",
                    result["log_path"].read_text(
                        encoding="utf-8"
                    ),
                )
            finally:
                root_logger = logging.getLogger()
                for handler in result["handlers"]:
                    root_logger.removeHandler(handler)
                    handler.close()

    def test_exception_hooks_write_crash_report(self):
        with tempfile.TemporaryDirectory() as temp:
            crash_dir = Path(temp) / "crashes"
            original_sys_hook = sys.excepthook

            try:
                result = install_exception_hooks(crash_dir)
                self.assertTrue(result["installed"])

                error = RuntimeError("controlled-crash")
                sys.excepthook(
                    RuntimeError,
                    error,
                    error.__traceback__,
                )

                reports = list(
                    crash_dir.glob("redbox_os_crash_*.log")
                )
                self.assertEqual(len(reports), 1)
                content = reports[0].read_text(
                    encoding="utf-8"
                )
                self.assertIn(
                    "RuntimeError: controlled-crash",
                    content,
                )
                self.assertNotIn(
                    str(PROJECT_ROOT / "database/redbox_os.db"),
                    content,
                )
            finally:
                sys.excepthook = original_sys_hook

    def test_packaging_uses_single_version_source(self):
        spec = (
            PROJECT_ROOT / "REDBOX_OS.spec"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "from application_metadata import",
            spec,
        )
        self.assertIn(
            "version=APP_VERSION",
            spec,
        )
        self.assertIn(
            '"CFBundleVersion": APP_BUILD',
            spec,
        )
        self.assertIn(
            "icon=",
            spec,
        )
        self.assertNotIn("icon=None", spec)


    def test_application_icon_assets_are_packaged(self):
        png_path = (
            PROJECT_ROOT / "assets" / "REDBOX_OS.png"
        )
        icns_path = (
            PROJECT_ROOT / "assets" / "REDBOX_OS.icns"
        )
        self.assertTrue(png_path.is_file())
        self.assertTrue(icns_path.is_file())
        self.assertGreater(png_path.stat().st_size, 10_000)
        self.assertGreater(icns_path.stat().st_size, 10_000)
        self.assertEqual(
            png_path.read_bytes()[:8],
            b"\x89PNG\r\n\x1a\n",
        )
        self.assertEqual(
            icns_path.read_bytes()[:4],
            b"icns",
        )


if __name__ == "__main__":
    unittest.main()
