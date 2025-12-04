"""
Browser based tests for the library management system.
They use Selenium to drive a real browser and check two flows:
1) Adding a new book
2) Borrowing an existing book from the catalog and verifying the confirmation message.
"""
import requests
import subprocess
import sys
import contextlib
import time
import pytest
import os
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# webdriver_manager is optional we use it if present
try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

# Folder that contains app.py
project_root_dir = Path(__file__).resolve().parent.parent

# url where flask app is served
base_app_url = "http://localhost:5000"

def wait_for_server_ready(url: str, timeout_seconds: int = 10):
    """
    Poll the given url until the Flask server responds or timeout.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code < 500:

                # server is up
                return
        except requests.exceptions.ConnectionError:

            # Server not up yet so we wait and try again
            time.sleep(0.2)
    raise RuntimeError(f"The flask server ({url}) didn't start within {timeout_seconds} seconds")


@pytest.fixture(scope="session", autouse=True)
def start_flask_application():
    """
    Starts the flask app once for the whole test session. Removes library.db so we always start
    from the same sample data.
    """

    # Starting from a fresh database each run
    database_file_path = project_root_dir / "library.db"
    if database_file_path.exists():
        database_file_path.unlink()

    # Launching app.py as a child process
    environment_variables = os.environ.copy()
    flask_process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(project_root_dir),
        env=environment_variables,
    )
    wait_for_server_ready("http://127.0.0.1:5000")

    # Yielding control back to pytest as tests run here
    yield

    # The test session ends and we stop the flask process
    flask_process.terminate()
    with contextlib.suppress(subprocess.TimeoutExpired):
        flask_process.wait(timeout=5)

    # If it’s still running force end
    if flask_process.poll() is None:
        flask_process.kill()

@pytest.fixture
def selenium_driver():
    """
    Creates a new Chrome browser for each test.
    """
    chrome_options = Options()

    # sets to values chromedriver  and system accept
    chrome_options.page_load_strategy = "normal"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1280,720")
    if ChromeDriverManager is not None:
        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=chrome_options)
    else:
        browser = webdriver.Chrome(options=chrome_options)
    yield browser
    browser.quit()


def find_catalog_row_for_title(browser: webdriver.Chrome, book_title: str):
    """
    Returns the tr element whose text contains book_title. Fails the test if nothing matches.
    """
    rows = browser.find_elements(By.CSS_SELECTOR, "table tbody tr")
    matching_row = None
    for row in rows:
        if book_title in row.text:
            matching_row = row
            break
    assert matching_row is not None, (
        f'Couldnt find catalog row for title "{book_title}".'
    )
    return matching_row


def test_add_new_book_visible_in_catalog(selenium_driver):
    """
    add book E2E flow.
    1.Opens the add book page.
    2.Fills in fields for a new test book.
    3.Submits the form.
    4.Verifies that a success message is shown.
    5.Verifies that the new book shows up in the catalog table.
    """

    # staring on /catalog and countshow many rows exist before we add anything
    catalog_url = f"{base_app_url}/catalog"
    selenium_driver.get(catalog_url)
    rows_before_add = selenium_driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    number_of_rows_before_add = len(rows_before_add)

    # Navigating to the add book page we go directly to /add_book
    add_book_url = f"{base_app_url}/add_book"
    selenium_driver.get(add_book_url)

    # checking if we are on the page (url should contain /add_book)
    assert "/add_book" in selenium_driver.current_url

    # Waiting until the title input is present to know the page loaded
    WebDriverWait(selenium_driver, timeout=5).until(
        EC.presence_of_element_located((By.ID, "title"))
    )
    # Test book data (ids match the form field ids)
    test_book_details = {
        "title": "E2E Selenium book",
        "author": "E2E tester",
        "isbn": "9998881130322",
        "total_copies": "3",
    }

    # Filling each form field with keys in the dict match the html element ids in add_book.html
    for field_id, field_value in test_book_details.items():
        input_element = selenium_driver.find_element(By.ID, field_id)

        #if the field has prefilled data
        input_element.clear()
        input_element.send_keys(field_value)

    # Submitting the add book form we look for the submit button
    submit_button = selenium_driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # After submitting the app redirects us back to /catalog if all went well. We wait for that redirect to happen.
    WebDriverWait(selenium_driver, timeout=5).until(
        EC.url_contains("/catalog")
    )

    # Checking if the success flash message is displayed
    # We wait until one element of the kind appears.
    success_flash_element = WebDriverWait(selenium_driver, timeout=5).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "div.flash-success"))
    )

    # Grabbing the text to assert on it.
    success_flash_text = success_flash_element.text

    # we check the important pieces
    success_text_lower = success_flash_text.lower()
    assert test_book_details["title"].lower() in success_text_lower
    assert "successfully" in success_text_lower
    assert "added to the catalog" in success_text_lower

    # Also confirm no error flash is visible simultaneously
    error_banners = selenium_driver.find_elements(By.CSS_SELECTOR, "div.flash-error")
    assert not error_banners

    # Verifying the new book appears in the catalog table. Selenium finds
    # row where one of the td cells has the title
    book_title = test_book_details["title"]
    row_xpath = f"//table//tr[td[contains(normalize-space(.), '{book_title}')]]"
    catalog_row = WebDriverWait(selenium_driver, timeout=5).until(
        EC.presence_of_element_located((By.XPATH, row_xpath)),
        message=f'System couldnt find a catalog for "{book_title}"'
    )
    catalog_row_text = catalog_row.text

    # The row should contain the title, author and isbn we just submitted.
    assert test_book_details["title"] in catalog_row_text
    assert test_book_details["author"] in catalog_row_text
    assert test_book_details["isbn"] in catalog_row_text

    # check that the total number of rows increased by exactly one.
    rows_after_add = selenium_driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    number_of_rows_after_add = len(rows_after_add)
    assert number_of_rows_after_add == number_of_rows_before_add + 1, (
        f"catalog row after adding a book. "
        f"Before: {number_of_rows_before_add} \n After: {number_of_rows_after_add}"
    )

def test_borrow_book_from_catalog_shows_confirmation(selenium_driver):
    """
    Flow:
    1. Finds The Great Gatsby in the catalog.
    2. Enters a patron id
    3. Clicks borrow and check that the success flash shows the title and a valid due date
    """

    # I like to give the driver a more readable alias
    browser_session = selenium_driver

    # We're opening the catalog page
    library_catalog_page_url = f"{base_app_url}/catalog"
    browser_session.get(library_catalog_page_url)

    # Identifying book we'll borrow and finding the corresponding tr catalog element
    sample_book_title_to_borrow = "The Great Gatsby"

    # Deciding which patron id we'll use for this test.
    patron_identifier_for_test = "708888"

    # Getting all the rows in the catalog table body
    all_catalog_rows = WebDriverWait(browser_session, 5).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "table tbody tr")
        )
    )

    # there should be at least one book listed
    assert len(all_catalog_rows) > 0, "Catalog table is empty"
    book_row_element = None

    # Looping over each row and picking the 1st one whose text contains the title
    for current_row in all_catalog_rows:
        if sample_book_title_to_borrow in current_row.text:
            book_row_element = current_row
            break

    # Fail if not found
    assert book_row_element is not None, (
        f'Couldnt find book title "{sample_book_title_to_borrow} in catalog ".'
    )

    # Filling in the patron id
    patron_id_input_field = book_row_element.find_element(By.NAME, "patron_id")

    # The input should exist and be enabled.
    assert patron_id_input_field.is_enabled()

    # Cleaning out any preexisting text
    patron_id_input_field.clear()

    # Typing patron id we chose for this scenario.
    patron_id_input_field.send_keys(patron_identifier_for_test)

    # Triggering the borrow action for that specific row. In ui the borrow button for each row is styled with .btn-success.
    borrow_button_for_row = book_row_element.find_element(
        By.CSS_SELECTOR, "button.btn-success"
    )
    assert borrow_button_for_row.is_displayed()
    borrow_button_for_row.click()

    # Waiting for the success flash message and verifying its content.
    borrow_success_banner = WebDriverWait(browser_session, 5).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.flash-success")
        )
    )

    # flash message should contain the book title and a due date
    success_message_text = borrow_success_banner.text

    # First checksthe title and the word "borrowed" should be there
    assert sample_book_title_to_borrow in success_message_text
    assert "borrowed" in success_message_text.lower()

    # Second check pulling out the part after "Due date:" and make sure it looks like YYYY-MM-DD.
    _, _, date_part = success_message_text.partition("Due date:")
    borrow_due_date_text = date_part.strip().rstrip(".")

    # will raise error if the format is wrong which will fail the test
    datetime.strptime(borrow_due_date_text, "%Y-%m-%d")

    # Third check where with the add flow we expect no error flashes.
    error_banners = browser_session.find_elements(By.CSS_SELECTOR, "div.flash-error")
    assert not error_banners
