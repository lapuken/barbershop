from __future__ import annotations

import os
import unittest
from datetime import datetime

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    PlaywrightTimeoutError = RuntimeError
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, "Playwright is not installed. Install requirements-smoke.txt first.")
class BrowserSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        cls.username = os.getenv("SMOKE_USERNAME", "platformadmin")
        cls.password = os.getenv("SMOKE_PASSWORD", "ChangeMe12345!")
        cls.headless = os.getenv("SMOKE_HEADLESS", "true").lower() != "false"
        cls.write_tests = os.getenv("SMOKE_WRITE_TESTS", "false").lower() == "true"

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=cls.headless)
        cls.page = cls.browser.new_page()
        cls.page.set_default_timeout(10000)

    @classmethod
    def tearDownClass(cls):
        cls.page.close()
        cls.browser.close()
        cls.playwright.stop()

    def test_login_and_navigation(self):
        self.page.goto(f"{self.base_url}/accounts/login/")
        self.page.get_by_label("Username").fill(self.username)
        self.page.get_by_label("Password").fill(self.password)
        self.page.get_by_role("button", name="Login").click()

        self.page.wait_for_url(f"{self.base_url}/")
        self.assertIn("Operations Dashboard", self.page.locator("body").inner_text())

        navigation_checks = [
            ("/appointments/customers/", "Customers"),
            ("/appointments/", "Appointments"),
            ("/barbers/", "Barbers"),
            ("/products/", "Products"),
            ("/sales/", "Daily Sales"),
            ("/expenses/", "Expenses"),
            ("/reports/", "Reports & Intelligence"),
            ("/audit/", "Audit Log"),
            ("/settings/", "Settings"),
        ]
        for path, expected_text in navigation_checks:
            with self.subTest(path=path):
                self.page.goto(f"{self.base_url}{path}")
                self.assertIn(expected_text, self.page.locator("body").inner_text())

    def test_optional_write_smoke(self):
        if not self.write_tests:
            self.skipTest("SMOKE_WRITE_TESTS is not enabled.")

        self._login_if_needed()
        suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        self.page.goto(f"{self.base_url}/barbers/new/")
        self.page.get_by_label("Full name").fill(f"Smoke Barber {suffix}")
        self.page.get_by_label("Employee code").fill(f"SMK-{suffix}")
        self.page.get_by_label("Phone").fill("555-0001")
        self.page.get_by_label("Commission rate").fill("40.00")
        self.page.get_by_role("button", name="Save Barber").click()
        self.assertIn("Smoke Barber", self.page.locator("body").inner_text())

        self.page.goto(f"{self.base_url}/products/new/")
        self.page.get_by_label("Name").fill(f"Smoke Product {suffix}")
        self.page.get_by_label("SKU").fill(f"SMKSKU-{suffix}")
        self.page.get_by_label("Category").fill("Smoke")
        self.page.get_by_label("Cost price").fill("2.00")
        self.page.get_by_label("Sale price").fill("5.00")
        self.page.get_by_role("button", name="Save Product").click()
        self.assertIn("Smoke Product", self.page.locator("body").inner_text())

    def _login_if_needed(self):
        self.page.goto(f"{self.base_url}/")
        if "/accounts/login/" in self.page.url:
            self.page.get_by_label("Username").fill(self.username)
            self.page.get_by_label("Password").fill(self.password)
            self.page.get_by_role("button", name="Login").click()
            try:
                self.page.wait_for_url(f"{self.base_url}/")
            except PlaywrightTimeoutError as exc:
                raise AssertionError("Login did not redirect to the dashboard.") from exc
