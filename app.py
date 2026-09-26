from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


def init_db():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL,
            fine REAL DEFAULT 0
        )
    """)

    try:
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN fine REAL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


@app.route("/")
def home():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM members")
    total_members = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE status = 'Issued'"
    )
    issued_books = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE status = 'Returned'"
    )
    returned_books = cursor.fetchone()[0]

    # Latest 5 books
    cursor.execute("""
        SELECT id, title, author
        FROM books
        ORDER BY id DESC
        LIMIT 5
    """)
    recent_books = cursor.fetchall()

    # Latest 5 activities
    cursor.execute("""
        SELECT
            transactions.id,
            books.title,
            members.name,
            transactions.issue_date,
            transactions.return_date,
            transactions.status
        FROM transactions
        JOIN books ON transactions.book_id = books.id
        JOIN members ON transactions.member_id = members.id
        ORDER BY transactions.id DESC
        LIMIT 5
    """)
    recent_activity = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        total_books=total_books,
        total_members=total_members,
        issued_books=issued_books,
        returned_books=returned_books,
        recent_books=recent_books,
        recent_activity=recent_activity
    )


@app.route("/books")
def books():
    search = request.args.get("search", "")

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    if search:
        cursor.execute(
            """
            SELECT * FROM books
            WHERE title LIKE ? OR author LIKE ?
            """,
            (f"%{search}%", f"%{search}%")
        )
    else:
        cursor.execute("SELECT * FROM books")

    books = cursor.fetchall()

    conn.close()

    return render_template("books.html", books=books)


@app.route("/members")
def members():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()

    conn.close()

    return render_template("members.html", members=members)


@app.route("/add-member", methods=["POST"])
def add_member():
    name = request.form["name"]
    email = request.form["email"]

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO members (name, email) VALUES (?, ?)",
        (name, email)
    )

    conn.commit()
    conn.close()

    return redirect("/members")


@app.route("/issue-book", methods=["POST"])
def issue_book():
    book_id = request.form["book_id"]
    member_id = request.form["member_id"]

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Check if the book is already issued
    cursor.execute(
        """
        SELECT id FROM transactions
        WHERE book_id = ? AND status = 'Issued'
        """,
        (book_id,)
    )

    already_issued = cursor.fetchone()

    if already_issued:
        conn.close()
        return redirect("/issue-return?error=already_issued")

    # Issue the book
    cursor.execute(
        """
        INSERT INTO transactions
        (book_id, member_id, issue_date, status)
        VALUES (?, ?, date('now'), ?)
        """,
        (book_id, member_id, "Issued")
    )

    conn.commit()
    conn.close()

    return redirect("/issue-return")


@app.route("/return-book", methods=["POST"])
def return_book():
    transaction_id = request.form["transaction_id"]

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT issue_date FROM transactions WHERE id = ?",
        (transaction_id,)
    )

    transaction = cursor.fetchone()

    if transaction:
        cursor.execute("""
            UPDATE transactions
            SET return_date = date('now'),
                status = 'Returned',
                fine = CASE
                    WHEN julianday(date('now')) - julianday(issue_date) > 7
                    THEN (julianday(date('now')) - julianday(issue_date) - 7) * 5
                    ELSE 0
                END
            WHERE id = ?
        """, (transaction_id,))

    conn.commit()
    conn.close()

    return redirect("/issue-return")


@app.route("/issue-return")
def issue_return():
    error = request.args.get("error")

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT transactions.id,
               books.title,
               members.name,
               transactions.issue_date,
               transactions.status,
               transactions.fine
        FROM transactions
        JOIN books ON transactions.book_id = books.id
        JOIN members ON transactions.member_id = members.id
        ORDER BY transactions.id DESC
    """)

    transactions = cursor.fetchall()

    conn.close()

    return render_template(
        "issue_return.html",
        transactions=transactions,
        error=error
    )
@app.route("/reports")
def reports():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Total books
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    # Total members
    cursor.execute("SELECT COUNT(*) FROM members")
    total_members = cursor.fetchone()[0]

    # Currently issued books
    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE status = 'Issued'"
    )
    issued_books = cursor.fetchone()[0]

    # Returned books
    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE status = 'Returned'"
    )
    returned_books = cursor.fetchone()[0]

    # Total transactions
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = cursor.fetchone()[0]

    # Total fine
    cursor.execute("SELECT COALESCE(SUM(fine), 0) FROM transactions")
    total_fine = cursor.fetchone()[0]

    # Recent transactions
    cursor.execute("""
        SELECT
            transactions.id,
            books.title,
            members.name,
            transactions.issue_date,
            transactions.return_date,
            transactions.status,
            transactions.fine
        FROM transactions
        JOIN books ON transactions.book_id = books.id
        JOIN members ON transactions.member_id = members.id
        ORDER BY transactions.id DESC
        LIMIT 10
    """)

    transactions = cursor.fetchall()

    conn.close()

    return render_template(
        "reports.html",
        total_books=total_books,
        total_members=total_members,
        issued_books=issued_books,
        returned_books=returned_books,
        total_transactions=total_transactions,
        total_fine=total_fine,
        transactions=transactions
    )


@app.route("/add-book", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)",
            (title, author)
        )

        conn.commit()
        conn.close()

        return redirect("/books")

    return render_template("add_book.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)