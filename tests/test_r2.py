from database import get_all_books, insert_book

# R2 focus:
# Table shows: id, title, author, isbn, available_copies, total_copies
# Business rules: IDs are auto-generated positive ints and copies consistent and ISBN is 13 digits.

def test_empty():
    """
    With no books inserted, the catalog should come back empty.
    """
    stack = get_all_books()
    assert isinstance(stack, list)
    assert len(stack) == 0


def test_ids():
    """
    IDs must be generated positive integers.
    """
    insert_book("The Hobbit", "J.R.R. Tolkien", "9780547928227", 1, 1)
    insert_book("The Catcher in the Rye", "J.D. Salinger", "9780316769488", 1, 1)

    book_ids = [row["id"] for row in get_all_books()]
    assert all(isinstance(i, int) and i > 0 for i in book_ids)

    # sanity check for no duplicates
    assert len(book_ids) == len(set(book_ids))


def test_fields():
    """
    After inserts every row includes the fields the UI relies on.
    """
    insert_book("Pride and Prejudice", "Jane Austen", "9780141439518", 2, 2)
    insert_book("1984", "George Orwell", "9780451524935", 1, 1)

    catalog_rows = get_all_books()
    assert len(catalog_rows) >= 2
    must_have = {"id", "title", "author", "isbn", "total_copies", "available_copies"}

    for row in catalog_rows:
        # Makes sure all required keys are present
        assert must_have.issubset(row.keys())

def test_copies_ok():
    """
    Copies consistency: available_copies must be between 0 and total_copies.
    """
    insert_book("Sardinian Structs", "E. Isola", "9000000000005", 3, 3)

    # If DB/business layer allows only valid inserts the row should respect the invariant.
    shelf = get_all_books()
    for row in shelf:
        avail = row["available_copies"]
        total = row["total_copies"]
        assert isinstance(avail, int) and isinstance(total, int)
        assert 0 <= avail <= total



