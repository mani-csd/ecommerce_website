from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    # Sample products
    p1 = Product(title="Laptop", description="Powerful laptop for work", price=70000, stock=5)
    p2 = Product(title="Headphones", description="Noise-cancelling wireless headphones", price=5000, stock=15)
    p3 = Product(title="Smartphone", description="Latest Android phone", price=30000, stock=10)

    # Add to database
    db.session.add_all([p1, p2, p3])
    db.session.commit()

    print("Sample products added successfully!")

