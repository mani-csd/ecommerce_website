import os
from app import create_app, db
from app.models import Product

# Delete existing database file if it exists
db_file = "app.db"
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"Deleted existing database: {db_file}")
else:
    print("No existing database found. Creating a new one.")

# Create app and database
app = create_app()
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

    # Add sample products
    p1 = Product(title="Laptop", description="Powerful laptop for work", price=70000, stock=5)
    p2 = Product(title="Headphones", description="Noise-cancelling wireless headphones", price=5000, stock=15)
    p3 = Product(title="Smartphone", description="Latest Android phone", price=30000, stock=10)

    db.session.add_all([p1, p2, p3])
    db.session.commit()
    print("Sample products added successfully!")
