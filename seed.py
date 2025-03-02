from app import db
from models import Book

def seed_books():
    books = [
        Book(title="The Great Gatsby", author="F. Scott Fitzgerald", genre="Classic", price=10.99),
        Book(title="To Kill a Mockingbird", author="Harper Lee", genre="Classic", price=8.99),
        Book(title="1984", author="George Orwell", genre="Dystopian", price=9.99),
        Book(title="Pride and Prejudice", author="Jane Austen", genre="Romance", price=7.99),
        Book(title="Moby-Dick", author="Herman Melville", genre="Adventure", price=11.49)
    ]
    db.session.add_all(books)
    db.session.commit()
    print("✅ Books added successfully!")

if __name__ == '__main__':
    with db.app.app_context():
        seed_books()
