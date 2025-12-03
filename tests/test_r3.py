import pytest
from datetime import datetime, timedelta
from services.library_service import borrow_book_by_patron

# Minimal DB helpers used to inspect state
from database import (
    insert_book,
    get_book_by_id,
    get_book_by_isbn,
    get_patron_borrow_count,
    insert_borrow_record,
)

def mint_book(*, title: str, author: str, isbn: str, total: int, avail: int) -> int:
    """
    Insert a book and return its DB id.
    """
    insert_book(title, author, isbn, total, avail)
    return get_book_by_isbn(isbn)["id"]

def stack_loans(patron_id: str, quota: int):
    """
    Give this patron quota active loans (no return_date).
    """
    for i in range(quota):
        book_pk = mint_book(
            title=f"Foundation Vol.{i}",
            author="Isaac Asimov",
            isbn=f"9791{i:09d}",
            total=1,
            avail=1,
        )
        began_at = datetime.now() - timedelta(days=2)
        due_on = began_at + timedelta(days=14)
        insert_borrow_record(patron_id, book_pk, began_at, due_on)

def test_borrow_happy_path_drops_stock():
    """
    Positive, valid 6 digit patron and instock book then success and availability drops by 1.
    """
    card = "246813"
    book_pk = mint_book(
        title="The Hobbit",
        author="J.R.R. Tolkien",
        isbn="9780547928227",
        total=3,
        avail=3,
    )
    avail_before = get_book_by_id(book_pk)["available_copies"]
    ok, msg = borrow_book_by_patron(card, book_pk)
    avail_after = get_book_by_id(book_pk)["available_copies"]
    assert ok is True, "This borrow should go through."
    assert "success" in (msg or "").lower()
    assert avail_after == avail_before - 1, "Stock should drop by exactly one."
    assert get_patron_borrow_count(card) == 1, "Patron’s active count should tick up."

@pytest.mark.parametrize("bad_patron", ["", "12345", "1234567", "12A456", "abcdef", " 123456 "])
def test_reject_bad_patron_format(bad_patron):
    """
    Negative: patron ID must be exactly six digits.
    """
    book_pk = mint_book(
        title="Pride and Prejudice",
        author="Jane Austen",
        isbn="9780141439518",
        total=1,
        avail=1,
    )
    ok, msg = borrow_book_by_patron(bad_patron, book_pk)
    assert ok is False
    assert "invalid patron id" in (msg or "").lower()

def test_reject_when_zero_stock():
    """
    Negative, book exists but availability is 0 then borrow is refused and stock unchanged
    """
    card = "135790"
    book_pk = mint_book(
        title="One Hundred Years of Solitude",
        author="Gabriel García Márquez",
        isbn="9780060883287",
        total=1,
        avail=0,
    )
    avail_before = get_book_by_id(book_pk)["available_copies"]
    ok, msg = borrow_book_by_patron(card, book_pk)
    avail_after = get_book_by_id(book_pk)["available_copies"]
    assert ok is False
    assert "not available" in (msg or "").lower()
    assert avail_after == avail_before == 0, "Should stay at zero when the borrow is denied."

def test_reject_over_five_active():
    """
    Negative: patrons can carry at most five active loans the sixth must be refused
    """
    card = "703981"
    stack_loans(card, 5)
    book_pk = mint_book(
        title="Beloved",
        author="Toni Morrison",
        isbn="9781400033416",
        total=1,
        avail=1,
    )
    ok, msg = borrow_book_by_patron(card, book_pk)
    assert ok is False
    assert "maximum borrowing limit" in (msg or "").lower()


def test_borrow_fails_book_missing(mocker):
    """
    get_book_by_id() returns None and then "Book not found." branch at lines 83 and 84
    """
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    ok, msg = borrow_book_by_patron("413579", 7777)
    assert ok is False
    assert msg == "Book not found."


def test_borrow_reports_record_error(mocker):
    """
    insert_borrow_record() returns False which is the error branch at 95–96.
    """
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 41, "title": "Hansel and Gretel", "available_copies": 2},
    )
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=0)
    mocker.patch("services.library_service.insert_borrow_record", return_value=False)
    mocker.patch("services.library_service.update_book_availability", return_value=True)
    ok, msg = borrow_book_by_patron("606060", 41)
    assert ok is False
    assert msg == "Database error occurred while creating borrow record."


def test_borrow_reports_stock_error(mocker):
    """
    insert_borrow_record() succeeds, but update_book_availability() fails. line 98 never jumped to line 99 because line
    99 was never true
    """
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 52, "title": "Stock Market", "available_copies": 1},
    )
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=0)
    mocker.patch("services.library_service.insert_borrow_record", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=False)
    ok, msg = borrow_book_by_patron("717171", 52)
    assert ok is False
    assert msg == "Database error occurred while updating book availability."
