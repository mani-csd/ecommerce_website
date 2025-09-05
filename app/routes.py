from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, send_file
from .extensions import db, login_manager
from .models import User, Product, Category, Order, OrderItem
from .forms import RegisterForm, LoginForm, ProductForm
from .utils import save_image
from flask_login import login_user, logout_user, login_required, current_user
import os
import csv

main_bp = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main_bp.route('/')
def home():
    q = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 6
    query = Product.query
    if q:
        query = query.filter(Product.title.ilike(f"%{q}%"))
    products = query.paginate(page=page, per_page=per_page)
    categories = Category.query.all()
    return render_template('home.html', products=products, categories=categories, q=q)

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    p = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=p)

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered', 'warning')
            return redirect(url_for('main.register'))
        u = User(email=form.email.data, name=form.name.data)
        u.set_password(form.password.data)
        admin_email = os.getenv('ADMIN_EMAIL')
        if admin_email and u.email.lower() == admin_email.lower():
            u.is_admin = True
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash('Registered and logged in', 'success')
        return redirect(url_for('main.home'))
    return render_template('register.html', form=form)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in', 'success')
            return redirect(url_for('main.home'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('main.home'))

# CART helpers (session-based)
def _get_cart():
    return session.setdefault('cart', {})

def _save_cart(cart):
    session['cart'] = cart
    session.modified = True

@main_bp.route('/cart')
def view_cart():
    cart = _get_cart()
    items = []
    total = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if not p:
            continue
        subtotal = p.price * qty
        items.append({'product': p, 'qty': qty, 'subtotal': subtotal})
        total += subtotal
    return render_template('cart.html', items=items, total=total)

@main_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    qty = int(request.form.get('quantity', 1))
    cart = _get_cart()
    cart[str(product_id)] = cart.get(str(product_id), 0) + qty
    _save_cart(cart)
    flash('Added to cart', 'success')
    return redirect(request.referrer or url_for('main.home'))

@main_bp.route('/cart/update', methods=['POST'])
def update_cart():
    cart = _get_cart()
    for key, val in request.form.items():
        if key.startswith('qty_'):
            product_id = key.split('_', 1)[1]
            try:
                q = int(val)
            except ValueError:
                q = 0
            if q <= 0:
                cart.pop(product_id, None)
            else:
                cart[product_id] = q
    _save_cart(cart)
    flash('Cart updated', 'info')
    return redirect(url_for('main.view_cart'))

@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = _get_cart()
    if not cart:
        flash('Cart is empty', 'warning')
        return redirect(url_for('main.home'))
    total = 0
    order = Order(user_id=current_user.id)
    db.session.add(order)
    db.session.flush()  # get order.id
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if not p:
            continue
        oi = OrderItem(order_id=order.id, product_id=p.id, quantity=qty, price=p.price)
        db.session.add(oi)
        total += p.price * qty
        p.stock = max(0, p.stock - qty)
    order.total = total
    db.session.commit()
    session.pop('cart', None)
    flash('Order placed successfully', 'success')
    return redirect(url_for('main.orders'))

@main_bp.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

# ADMIN
def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access required', 'danger')
        return False
    return True

@main_bp.route('/admin/products')
@login_required
def admin_products():
    if not admin_required():
        return redirect(url_for('main.home'))
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@main_bp.route('/admin/product/new', methods=['GET', 'POST'])
@login_required
def admin_new_product():
    if not admin_required():
        return redirect(url_for('main.home'))
    form = ProductForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        filename = None
        image_file = request.files.get('image')
        if image_file:
            filename = save_image(image_file, current_app.config['UPLOAD_FOLDER'])
        p = Product(title=form.title.data, description=form.description.data,
                    price=form.price.data, stock=form.stock.data, image=filename,
                    category_id=form.category.data if form.category.data else None)
        db.session.add(p)
        db.session.commit()
        flash('Product created', 'success')
        return redirect(url_for('main.admin_products'))
    return render_template('admin/edit_product.html', form=form)

@main_bp.route('/admin/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    if not admin_required():
        return redirect(url_for('main.home'))
    p = Product.query.get_or_404(product_id)
    form = ProductForm(obj=p)
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        image_file = request.files.get('image')
        if image_file:
            filename = save_image(image_file, current_app.config['UPLOAD_FOLDER'])
            p.image = filename
        p.title = form.title.data
        p.description = form.description.data
        p.price = form.price.data
        p.stock = form.stock.data
        p.category_id = form.category.data
        db.session.commit()
        flash('Product updated', 'success')
        return redirect(url_for('main.admin_products'))
    return render_template('admin/edit_product.html', form=form, product=p)

@main_bp.route('/admin/orders/export')
@login_required
def admin_export_orders():
    if not admin_required():
        return redirect(url_for('main.home'))
    orders = Order.query.all()
    filepath = os.path.join(current_app.root_path, 'orders_export.csv')
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Order ID', 'User', 'Created', 'Total'])
        for o in orders:
            writer.writerow([o.id, o.user.email if o.user else '', o.created_at, o.total])
    return send_file(filepath, as_attachment=True)
