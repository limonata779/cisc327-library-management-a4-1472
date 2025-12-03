# Assignment 1 

**Name:** Ester Lucia Narduzzi  
**Student Number** 20421472    

### Project overview
**Purpose:** A small, testable library system that manages a catalog, allows to borrow/return books, compute late fees, search, and view a patron’s status.  
**Stack:** Python 3.x, Flask, SQLite, pytest.

## How to run the app
python -m venv .venv

macOS/Linux

    source .venv/bin/activate

Windows

    .\.venv\Scripts\activate

installing dependencies 

    pip install -r requirements.txt

    python -c "from database import init_database, add_sample_data; init_database(); add_sample_data()"

    # start the Flask app
    flask --app app.py run


    pytest -q               # run all tests
    pytest -k r4 -q         # e.g. just run R4 tests



# Architecture

**App and Blueprints**
  - App created in `app.py`
  - Routes are grouped by feature using Flask Blueprints.
  - UI uses Jinja2 templates.

**Business logic (`library_service.py`)**
  - Core rules are plain functions so they’re easy to unit test:
    - `add_book_to_catalog()` - R1
    - `borrow_book_by_patron()` - R3
    - `return_book_by_patron()` - R4
    - `calculate_late_fee_for_book()` - R5
    - `search_books_in_catalog()` - R6
    - `get_patron_status_report()` - R7


- `database.py`
  - All SQLite I/O in one place: connection setup, CRUD and small query helpers:
    - `get_all_books()`, `get_book_by_id()`, `get_book_by_isbn()`
    - `insert_book()`, `insert_borrow_record()`
    - `update_book_availability()`
    - `get_active_borrow()`
    - `update_borrow_record_return_date()`
    - `get_patron_borrowed_books()` (active loans + titles-authors)
    - `get_patron_borrow_count()` (number of active loans)
    - `get_patron_borrow_history()` (active + returned history)



# Data Model & Constraints
 `books`

| column            | type    | notes                                             |
|-------------------|---------|---------------------------------------------------|
| `id`              |  Int   | PK, autoincrement(positive integer)               |
| `title`           | String  | required                                          |
| `author`          | String     | required                                          |
| `isbn`            | String    | exactly 13 digits UNIQUE                          |
| `total_copies`    |  Int   | required, `> 0`                                   |
| `available_copies`|  Int   | required, `0 <= available_copies <= total_copies` |

Enforced in code:
- ISBN must be 13 numeric characters.
- `available_copies` can’t exceed `total_copies` and can’t go below 0.

`borrow_records`

| column        | type   | notes                                                |
|---------------|--------|------------------------------------------------------|
| `id`          | Int    | PK, autoincrement                                    |
| `patron_id`   | String | exactly 6 digits**                                   |
| `book_id`     | Int    | FK becomes `books.id`                                |
| `borrow_date` | String | ISO-8601 string                                      |
| `due_date`    | String | ISO-8601 string (default policy is borrow + 14 days) |
| `return_date` | String | ISO-8601 string or `NULL` while the loan is active   |

**Business rules**
- Max **5 active loans** per patron (`return_date IS NULL`).
- Late fees (R5): due at 14 days, first 7 overdue days at \$0.50/day, then \$1/day, cap is \$15 per book.

## Requirements R1  R7

### R1 Book Catalog Management
- **Status:** Pre-Created
- **What:** `add_book_to_catalog(...)` validates inputs (title and author present with size limits, ISBN  is exactly 13 digits, total copies > 0), blocks duplicate ISBNs, writes a book with "available_copies = total_copies"



### R2 Catalog Display
- **Status:** Pre-Created
- **What:** UI pulls from `database.get_all_books()` which returns rows ordered by title and shaped for the table: id, title, author, isbn, total_copies, available_copies.

### R3 Borrow Book
- **Status:** Pre-Created  
- **What:** `borrow_book_by_patron(patron_id, book_id)`:
  - book exists and has available_copies > 0
  - patron ID is exactly 6 digits  
  - patron has < 5 active borrows  
  Creates a borrow record (borrow + 14 days) and decrements availability.

### R4 Return Book
- **Status:** Done  
- **What:** `return_book_by_patron(patron_id, book_id)` 
  - requires an active loan for that patron+book
  - stamps `return_date`
  - adds availability by +1
    - reports a late fee in the message if overdue.

### R5 Late Fee API
- **Status:**  Done  
- **What: `calculate_late_fee_for_book(patron_id, book_id)` uses the active loan’s `due_date`:
  - first 7 overdue days at $0.50/day , after that $1.00/day. Gets gapped at **$15.00**  
  - returns `{ fee_amount, days_overdue, status }`

### R6 Book Search
- **Status:** Done  
- What: `search_books_in_catalog(q, type)`:
  - `type="title"` or `type="author"` → **partial**, **case-insensitive** match
  - `type="isbn"` exact 13-digit match
  Returns rows in the same shape as the catalog.

### R7  Patron Status Report
- **Status:**: Done  
- What: `get_patron_status_report(patron_id)` returns:
  - `borrowed_now`: active loans with `title/author/due_date/overdue`
  - `active_count`: number of active loans
  - `late_fees`: sum of R5 fees for active loans (as a string with 2 decimals)
  - `history`: lightweight borrow history (returned + active)

### Tests

## R1 

**Target:** `library_service.add_book_to_catalog(title, author, isbn, total_copies)`

Test count: 5

- `test_valid_insert`, positive: accepts a normal book. Verifies it’s persisted and that `available_copies == total_copies` (example data: ISBN `9425830617429`, *Pride and Prejudice* by Jane Austen, 3 copies).
- `test_title_required`, negative: rejects empty or whitespace only titles. Confirms no rows are created for the bad ISBNs (9817352046197, 9305718642204).
- `test_isbn_length_13`, negative: ISBN must be exactly 13 characters. one too short (314159265358) and one too long (`27182818284590`) are not inserted.
- **`test_copies_positive_int`, negative: total_copies must be a positive integer. Tries `0` and `-2` and both fail and leave the DB clean
- `test_duplicate_isbn`, negative: inserting a second row with the same ISBN is rejected. First insert with `9550013377777` succeeds and the second insert with same ISBN fails.


## R2 

**Target:** `database.get_all_books()` 

Test count: 4

- `test_empty` - returns an empty list when no books exist.
- `test_ids` - IDs are auto-generated positive integers and unique after inserting two titles (The Hobbit).
- `test_fields` - every catalog row includes the fields the UI expects:  
  `{id, title, author, isbn, total_copies, available_copies}`. Uses "Pride and Prejudice" and 1984 as samples.
- `test_copies_ok` - consistency check: `0 ≤ available_copies ≤ total_copies` for every row in the catalog


## R3 

**Target:** `library_service.borrow_book_by_patron(patron_id, book_id)`

Test count: 4

- `test_borrow_happy_path_drops_stock`positive: a valid 6 digit patron borrows an available book. Expects success, message mentions success, stock drops by 1, and patron’s active loan count goes to 1.
- `test_reject_bad_patron_format` negative: rejects IDs that aren’t exactly six digits. Confirms error message mentions “invalid patron id”.
- `test_reject_when_zero_stock` negative: book exists but `available_copies == 0`. Borrow is refused, message notes “not available”
- `test_reject_over_five_active` negative: patron already has 5 active loans and a 6th request is denied via message.


## R4 

**Target:** `library_service.return_book_by_patron(patron_id, book_id)`

Test count: 4

- `test_increments_stock_and_clears_active`- positive: the real borrower returns their book. Expects success (or “return complete”), stock +1, and their active-loan count decreases by 1.
- `test_patron_id` negative: rejects patron IDs that aren’t exactly six digits. Stock is unchanged; message includes “invalid patron id”.
- `test_rejects_not_borrower` negative: someone other than the borrower tries to return it. Operation is refused and message mentions “not borrowed” and stock remains unchanged.
- `test_overdue_fee_updates_stock` positive: overdue return still succeeds and increments stock. The message references a fee (not $0.00).


## R5 

**Target:** `library_service.calculate_late_fee_for_book(patron_id, book_id)`

**Helpers used:**  
`shelve()` inserts a unique book and returns its id.  
`borrow_with_due(patron, book_id, days_overdue)` creates an active loan whose due date is `days_overdue` 

Test count: 4

- `test_fee_none_when_before_due` positive: loan is not overdue. Expects `days_overdue == 0` and `$0.00` fee.
- `test_fee_first_band_three_days`positive: 3 days late `3 * $0.50 = $1.50`. checks both days and amount.
- `test_fee_second_band_ten_days`positive: 10 days late `7 * $0.50 + 3 * $1.00 = $6.50`. Checks math.
- `test_fee_capped_at_max`positive: 40 days late hits the cap. Expects $15.00 max

## R6 

**Target:** `library_service.search_books_in_catalog(search_term, search_type)`

**Helpers used:**  
`plant_book(...)` and `seed_sample_stack()` build a tiny shelf with varied titles and authors and ISBNs.

Test count: 4

- `test_title_fuzzy_casefold_hits`positive: title search is partial and case insensitive (`"nIgHt"` becomes “Nights”). Sanity checks returned row fields.
- `test_author_fuzzy_hit` positive: author search is partial + case insensitive (`"mOOn"` matches “Mimi Moonfield”).
- `test_isbn_exact_only` positive: exact 13 digit long ISBN returns a single row and verifies if there's a title - ISBN match.
- `test_isbn_partial_rejected` negative: the partial ISBNs return nothing.

## R7

**Target:** `library_service.get_patron_status_report(patron_id)`

**Helpers used:**   
`checkout()` creates an on time active loan.  
`stash()` inserts a book and returns id. 
`checkout_overdue()` creates an already late active loan.

Test count: 4

- `test_mixed_active_returned` positive: one on-time active, one overdue and active, one returned.  
  Asserts structure (`borrowed_now`, `active_count`, `late_fees`, `history`), titles present in the right lists, `active_count == len(borrowed_now)`, and fee total >= `$2.00` (for 4 days late at `$0.50`).
- `test_empty_patron` positive: new patron. Has zero active loans, zero fees and an empty history.
- `test_rejects_id` negative: bad patron id returns an empty report and a status flag.
- `test_status_list_len` positive: with one active checkout `active_count` matches `len(borrowed_now)`.




## Future additions
- **History API:** R7 builds a lightweight history list. A dedicated endpoint (with features like paging and sort) would make it more useful.
- **Validation edges:** we accept any 13 digit ISBN. Could need additional EAN13/ISBN-13 checksum validation.
- **Logging observability:** adding structured logs around borrow and return paths.
