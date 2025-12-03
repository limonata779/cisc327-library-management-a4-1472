from datetime import datetime, timedelta
from services.library_service import get_patron_status_report, return_book_by_patron
from database import (
    insert_borrow_record,
    insert_book,
    update_book_availability,
    get_book_by_isbn,
)


#helpers
def stash(*, title: str, author: str, isbn: str, total: int, avail: int) -> int:
    """
    Insert a book and return its id.
    """
    assert len(isbn) == 13 and isbn.isdigit()
    insert_book(title, author, isbn, total, avail)
    return get_book_by_isbn(isbn)["id"]


def checkout(patron: str, *, book_id: int, days_ago: int = 1, due_in: int = 7) -> None:
    """
    Create active loan (no return_date)
    """
    start = datetime.now() - timedelta(days=days_ago)
    due = datetime.now() + timedelta(days=due_in)
    insert_borrow_record(patron, book_id, start, due)


def checkout_overdue(patron: str, *, book_id: int, overdue_days: int) -> None:
    """
    Create an active loan thats already overdue by n days.
    """
    start = datetime.now() - timedelta(days=16)
    due = datetime.now() - timedelta(days=overdue_days)
    insert_borrow_record(patron, book_id, start, due)


# tests
def test_mixed_active_returned():
    """
    positive, one active (on time), one active (overdue), one returned
    """
    patron = "742981"
    b1 = stash(title="To Kill a Mockingbird", author="Harper Lee",
               isbn="9465128374009", total=2, avail=2)
    b2 = stash(title="The Hobbit", author="J.R.R. Tolkien",
               isbn="9057318645201", total=2, avail=2)
    b3 = stash(title="Pride and Prejudice", author="Jane Austen",
               isbn="8190476523814", total=2, avail=2)

    # active but not overdue
    checkout(patron, book_id=b1, days_ago=2, due_in=5)
    update_book_availability(b1, -1)

    # active but overdue by 4 days -> $2.00 fee at $0.50/day
    checkout_overdue(patron, book_id=b2, overdue_days=4)
    update_book_availability(b2, -1)

    # returned
    checkout(patron, book_id=b3, days_ago=10, due_in=2)
    update_book_availability(b3, -1)
    return_book_by_patron(patron, b3)
    report = get_patron_status_report(patron)
    assert isinstance(report, dict)
    assert {"borrowed_now", "active_count", "late_fees", "history"} <= report.keys()

    # counts line up
    assert report["active_count"] == len(report["borrowed_now"])
    now_titles = {row.get("title") for row in report["borrowed_now"]}
    assert "To Kill a Mockingbird" in now_titles
    assert "The Hobbit" in now_titles
    hist_titles = {row.get("title") for row in report["history"]}
    assert "Pride and Prejudice" in hist_titles

    # fee floor where 4 days late * $0.50
    assert float(report["late_fees"]) >= 2.00


def test_empty_patron():
    """
    positive, brand-new patron is no loans and no fees.
    """
    newcomer = "553207"
    report = get_patron_status_report(newcomer)
    assert isinstance(report, dict)
    assert report.get("active_count", 0) == 0
    assert report.get("borrowed_now", []) == []
    assert float(report.get("late_fees", 0.0)) == 0.0
    assert report.get("history", []) == []


def test_rejects_id():
    """
    negative, bad patron id should return an empty report.
    """
    bad = "12a456"
    report = get_patron_status_report(bad)
    assert isinstance(report, dict)
    zero = (
            report.get("active_count", 0) == 0
            and float(report.get("late_fees", 0.0)) == 0.0
            and report.get("borrowed_now", []) == []
    )
    assert zero or "status" in report


def test_status_list_len():
    """
    positive, active_count must equal len(borrowed_now)
    """
    who = "734268"
    b = stash(title="The Name of the Rose", author="Umberto Eco",
              isbn="9602847153097", total=1, avail=1)
    checkout(who, book_id=b, days_ago=1, due_in=6)
    update_book_availability(b, -1)
    report = get_patron_status_report(who)
    assert report["active_count"] == len(report["borrowed_now"])

