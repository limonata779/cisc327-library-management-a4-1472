from services.library_service import search_books_in_catalog
from database import insert_book, get_book_by_isbn
def plant_book(*, title: str, author: str, isbn: str, total: int, avail: int) -> int:
    """
    Insert a book and return its DB id.
    """
    assert len(isbn) == 13 and isbn.isdigit(), "ISBN must be 13 digits long"
    insert_book(title, author, isbn, total, avail)
    return get_book_by_isbn(isbn)["id"]

def seed_sample_stack():
    """
    Small shelf
    """
    plant_book(title="Nights",          author="Ignus Starling",   isbn="9845123764029", total=3, avail=2)
    plant_book(title="Ledger",          author="Eva Nova",         isbn="9728094157364", total=4, avail=4)
    plant_book(title="Quantum Physics", author="Richard Orchard",  isbn="9901738456207", total=2, avail=1)
    plant_book(title="Algorithms",      author="Mimi Moonfield",   isbn="9615402981735", total=5, avail=5)


def test_title_fuzzy_casefold_hits():
    """
    POSITIVE: Title search is partial + case-insensitive.
    Check two separate queries: 'nIgHt' -> 'Nights', 'LEDGER' -> 'Ledger'.
    """
    seed_sample_stack()

    # lower/upper mix shouldnt matter
    rows_night = search_books_in_catalog("nIgHt", "title")
    rows_ledger = search_books_in_catalog("LEDGER", "title")
    titles_night = {r["title"] for r in rows_night}
    titles_ledger = {r["title"] for r in rows_ledger}
    assert "Nights" in titles_night
    assert "Ledger" in titles_ledger

    # result rows look like catalog rows
    required = {"id", "title", "author", "isbn", "total_copies", "available_copies"}
    assert all(required.issubset(r.keys()) for r in rows_night + rows_ledger)

def test_author_fuzzy_hit():
    """
    positive Author search is partial + case-insensitive. 'mOOn' should match 'Mimi Moonfield'.
    """
    seed_sample_stack()
    rows = search_books_in_catalog("mOOn", "author")
    authors = {r["author"] for r in rows}
    assert "Mimi Moonfield" in authors


def test_isbn_exact_only():
    """
    positive ISBN must be an exact 13-digit match
    Expect one hit for 9901738456207 -> 'Quantum Physics'
    """
    seed_sample_stack()
    rows = search_books_in_catalog("9901738456207", "isbn")
    assert len(rows) == 1
    book = rows[0]
    assert book["title"] == "Quantum Physics"
    assert book["isbn"] == "9901738456207"


def test_isbn_partial_rejected():
    """
    Negative Partial ISBNs shouldnt match
    """
    seed_sample_stack()
    # One digit short should not return anything
    rows = search_books_in_catalog("990173845620", "isbn")
    assert rows == [] or len(rows) == 0


def test_search_rejects_empty_query():
    results = search_books_in_catalog("", "title")
    assert results == []
