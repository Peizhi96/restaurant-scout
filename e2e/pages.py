"""Page objects for the Restaurant Scout dashboard.

Tests talk to these classes instead of raw selectors, so a markup change is fixed in one
place and the tests read as user workflows.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import quote_plus

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

DEFAULT_TIMEOUT = 20
TABLE_TITLES = (By.CSS_SELECTOR, "table.listing-table tbody tr td:first-child strong")


class BasePage:
    def __init__(self, driver: WebDriver, base_url: str) -> None:
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    def heading(self) -> str:
        return self.wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h1"))).text

    def _visible_texts(self, locator: tuple[str, str]) -> list[str]:
        try:
            return [element.text for element in self.driver.find_elements(*locator)]
        except StaleElementReferenceException:
            return []  # the page re-rendered mid-read; the caller polls again

    def wait_for_texts(
        self,
        locator: tuple[str, str],
        *,
        present: Iterable[str] = (),
        absent: Iterable[str] = (),
    ) -> list[str]:
        """Poll until every `present` text shows and no `absent` text does.

        Polling covers both full page loads (GET forms) and client-side navigations
        (Next.js links), where the DOM updates after the URL changes.
        """
        present, absent = set(present), set(absent)
        seen: list[str] = []

        def condition(_: WebDriver) -> bool:
            nonlocal seen
            seen = self._visible_texts(locator)
            return present <= set(seen) and not (absent & set(seen))

        try:
            self.wait.until(condition)
        except TimeoutException as error:
            raise AssertionError(
                f"expected present={sorted(present)} absent={sorted(absent)}; page shows {seen}"
            ) from error
        return seen


class DashboardPage(BasePage):
    def open(self) -> DashboardPage:
        self.driver.get(f"{self.base_url}/")
        self.wait.until(EC.url_contains("/dashboard"))  # "/" redirects to the dashboard
        return self

    def wait_for_recent_titles(self, titles: Iterable[str]) -> list[str]:
        return self.wait_for_texts(TABLE_TITLES, present=titles)


class ListingsPage(BasePage):
    def open(self, query: str = "") -> ListingsPage:
        self.driver.get(f"{self.base_url}/listings{'?' + query if query else ''}")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form.filter-bar")))
        return self

    def filter_by_city(self, city: str) -> None:
        city_select = self.driver.find_element(By.CSS_SELECTOR, "form.filter-bar select[name=city]")
        Select(city_select).select_by_value(city)
        self.driver.find_element(By.CSS_SELECTOR, "form.filter-bar button[type=submit]").click()
        self.wait.until(EC.url_contains(f"city={quote_plus(city)}"))

    def clear_filters(self) -> None:
        self.driver.find_element(By.CSS_SELECTOR, "form.filter-bar a.clear-link").click()
        self.wait.until(lambda driver: "?" not in driver.current_url)

    def wait_for_titles(
        self, *, present: Iterable[str] = (), absent: Iterable[str] = ()
    ) -> list[str]:
        return self.wait_for_texts(TABLE_TITLES, present=present, absent=absent)

    def open_listing(self, title: str) -> ListingDetailPage:
        row_link = (
            By.XPATH,
            "//table[contains(@class,'listing-table')]"
            f"//tr[.//strong[normalize-space()='{title}']]//a[contains(@class,'arrow-link')]",
        )
        self.wait.until(EC.element_to_be_clickable(row_link)).click()
        detail = ListingDetailPage(self.driver, self.base_url)
        detail.wait_loaded(title)
        return detail


class ListingDetailPage(BasePage):
    STATUS = (By.CSS_SELECTOR, "form.workflow-form select[name=status]")
    NOTES = (By.CSS_SELECTOR, "form.workflow-form textarea[name=notes]")

    def open(self, listing_id: str, title: str) -> ListingDetailPage:
        self.driver.get(f"{self.base_url}/listings/{listing_id}")
        self.wait_loaded(title)
        return self

    def wait_loaded(self, title: str) -> None:
        self.wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "h1"), title))

    def score_panel_heading(self) -> str:
        return self.driver.find_element(By.CSS_SELECTOR, "section.score-panel h2").text

    def ai_panel_heading(self) -> str:
        return self.driver.find_element(By.CSS_SELECTOR, "section.ai-panel h2").text

    def missing_information(self) -> list[str]:
        return self._visible_texts((By.CSS_SELECTOR, "section.missing-panel .tag-cloud span"))

    def save_review(self, *, status: str, notes: str) -> None:
        Select(self.driver.find_element(*self.STATUS)).select_by_value(status)
        notes_field = self.driver.find_element(*self.NOTES)
        notes_field.clear()
        notes_field.send_keys(notes)
        self.driver.find_element(By.CSS_SELECTOR, "form.workflow-form button[type=submit]").click()

    def review_values(self) -> tuple[str, str]:
        status = Select(self.driver.find_element(*self.STATUS)).first_selected_option
        notes = self.driver.find_element(*self.NOTES)
        return status.get_attribute("value") or "", notes.get_attribute("value") or ""
