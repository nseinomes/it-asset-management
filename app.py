from flask import Flask, render_template, request, redirect, session, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection
from app_utils import log_action
from datetime import date, datetime, timedelta
from math import ceil
import bcrypt
import os
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'evolve_secret_key_dev')
app.permanent_session_lifetime = timedelta(minutes=30)


# ── Session timeout ──────────────────────────────────────────────
@app.before_request
def check_session_timeout():
    if 'user' in session:
        last = session.get('last_activity')
        if last:
            elapsed = datetime.now() - datetime.fromisoformat(last)
            if elapsed > timedelta(minutes=30):
                session.clear()
                return redirect('/login')
        session['last_activity'] = datetime.now().isoformat()


# ── Home ─────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template("index.html")


# ── Login ────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['user'] = user['username']
            session['user_id'] = user['id']
            session['last_activity'] = datetime.now().isoformat()
            return redirect('/dashboard')

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


# ── Dashboard ────────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM assets")
    total_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Active'")
    active_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Maintenance'")
    maintenance_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Inactive'")
    inactive_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM interventions WHERE status='Active'")
    total_interventions = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM interventions WHERE status='Completed'")
    completed_interventions = cursor.fetchone()['COUNT(*)']

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_assets=total_assets,
        active_assets=active_assets,
        maintenance_assets=maintenance_assets,
        inactive_assets=inactive_assets,
        total_interventions=total_interventions,
        completed_interventions=completed_interventions
    )


# ── Assets ───────────────────────────────────────────────────────
@app.route('/assets')
def assets():
    if 'user' not in session:
        return redirect('/login')

    per_page = 20

    # 1. Parse & sanitise query params
    try:
        page = max(1, int(request.args.get('page', 1) or 1))
    except (ValueError, TypeError):
        page = 1

    search   = request.args.get('search', '').strip()
    status   = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()
    brand    = request.args.get('brand', '').strip()

    # 2. Build parameterised WHERE clause
    conditions = ['1=1']
    params = []

    if status:
        conditions.append('a.status = %s')
        params.append(status)
    if category:
        conditions.append('c.name = %s')
        params.append(category)
    if brand:
        conditions.append('a.brand = %s')
        params.append(brand)
    if search:
        conditions.append('(a.asset_tag LIKE %s OR a.name LIKE %s OR a.brand LIKE %s)')
        like = f'%{search}%'
        params.extend([like, like, like])

    where_clause = ' AND '.join(conditions)

    conn = get_connection()
    cursor = conn.cursor()

    # 3. COUNT query for total_count
    count_sql = f"""
        SELECT COUNT(*) AS cnt
        FROM assets a
        LEFT JOIN categories c ON a.category_id = c.id
        WHERE {where_clause}
    """
    cursor.execute(count_sql, params)
    total_count = cursor.fetchone()['cnt']

    # 4. Compute total_pages and clamp page
    total_pages = max(1, ceil(total_count / per_page))
    page = min(page, total_pages)

    # 5. Data query with LIMIT / OFFSET
    offset = (page - 1) * per_page
    data_sql = f"""
        SELECT a.*, c.name as category_name
        FROM assets a
        LEFT JOIN categories c ON a.category_id = c.id
        WHERE {where_clause}
        ORDER BY a.id DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(data_sql, params + [per_page, offset])
    assets_list = cursor.fetchall()

    # 6. Fetch categories and distinct brands for filter dropdowns
    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = cursor.fetchall()

    cursor.execute("SELECT DISTINCT brand FROM assets WHERE brand IS NOT NULL AND brand != '' ORDER BY brand")
    brands = [row['brand'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    # 7. Render with all required context
    return render_template(
        "assets.html",
        assets=assets_list,
        categories=categories,
        brands=brands,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        filter_search=search,
        filter_status=status,
        filter_category=category,
        filter_brand=brand,
    )


@app.route('/asset/<int:id>')
def asset_detail(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.*, c.name as category_name
        FROM assets a
        LEFT JOIN categories c ON a.category_id = c.id
        WHERE a.id=%s
    """, (id,))
    asset = cursor.fetchone()

    if not asset:
        cursor.close()
        conn.close()
        return redirect('/assets')

    cursor.execute("""
        SELECT i.*, t.name as technician_name
        FROM interventions i
        JOIN technicians t ON i.technician_id = t.id
        WHERE i.asset_id = %s
        ORDER BY i.intervention_date DESC
    """, (id,))
    history = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("asset_detail.html", asset=asset, history=history)


@app.route('/add-asset', methods=['GET', 'POST'])
def add_asset():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        asset_tag     = request.form['asset_tag']
        name          = request.form['name']
        brand         = request.form['brand']
        model         = request.form['model']
        serial_number = request.form.get('serial_number', '')
        category_id   = request.form.get('category_id') or None
        status        = request.form['status']
        location      = request.form.get('location', '')
        purchase_date = request.form.get('purchase_date') or None
        warranty_exp  = request.form.get('warranty_expiration') or None
        notes         = request.form.get('notes', '')

        cursor.execute("""
            INSERT INTO assets
            (asset_tag, name, brand, model, serial_number, category_id,
             status, location, purchase_date, warranty_expiration, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (asset_tag, name, brand, model, serial_number, category_id,
              status, location, purchase_date, warranty_exp, notes))

        conn.commit()
        new_asset_id = cursor.lastrowid
        cursor.close()
        conn.close()

        new_value = {k: v for k, v in {
            'asset_tag':          asset_tag,
            'name':               name,
            'brand':              brand,
            'model':              model,
            'serial_number':      serial_number,
            'category_id':        category_id,
            'status':             status,
            'location':           location,
            'purchase_date':      str(purchase_date) if purchase_date else None,
            'warranty_expiration': str(warranty_exp) if warranty_exp else None,
            'notes':              notes,
        }.items() if v is not None and v != ''}
        try:
            log_action(session['user_id'], 'CREATE', 'asset', new_asset_id,
                       new_value=new_value)
        except Exception as e:
            app.logger.error(f"Audit log failed for add_asset id={new_asset_id}: {e}")

        return redirect('/assets')

    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("add_asset.html", categories=categories)


@app.route('/edit-asset/<int:id>', methods=['GET', 'POST'])
def edit_asset(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        asset_tag     = request.form['asset_tag']
        name          = request.form['name']
        brand         = request.form['brand']
        model         = request.form['model']
        serial_number = request.form.get('serial_number', '')
        category_id   = request.form.get('category_id') or None
        status        = request.form['status']
        location      = request.form.get('location', '')
        purchase_date = request.form.get('purchase_date') or None
        warranty_exp  = request.form.get('warranty_expiration') or None
        notes         = request.form.get('notes', '')

        # Fetch old asset row before updating (for audit log)
        cursor.execute("SELECT * FROM assets WHERE id=%s", (id,))
        old_asset = cursor.fetchone()
        old_value = {k: (str(v) if v is not None else None)
                     for k, v in old_asset.items()} if old_asset else {}

        cursor.execute("""
            UPDATE assets
            SET asset_tag=%s, name=%s, brand=%s, model=%s, serial_number=%s,
                category_id=%s, status=%s, location=%s, purchase_date=%s,
                warranty_expiration=%s, notes=%s
            WHERE id=%s
        """, (asset_tag, name, brand, model, serial_number, category_id,
              status, location, purchase_date, warranty_exp, notes, id))

        conn.commit()
        cursor.close()
        conn.close()

        new_value = {
            'asset_tag':          asset_tag,
            'name':               name,
            'brand':              brand,
            'model':              model,
            'serial_number':      serial_number,
            'category_id':        category_id,
            'status':             status,
            'location':           location,
            'purchase_date':      str(purchase_date) if purchase_date else None,
            'warranty_expiration': str(warranty_exp) if warranty_exp else None,
            'notes':              notes,
        }
        try:
            log_action(session['user_id'], 'UPDATE', 'asset', id,
                       old_value=old_value, new_value=new_value)
        except Exception as e:
            app.logger.error(f"Audit log failed for edit_asset id={id}: {e}")

        return redirect('/assets')

    cursor.execute("SELECT * FROM assets WHERE id=%s", (id,))
    asset = cursor.fetchone()

    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("edit_asset.html", asset=asset, categories=categories)


@app.route('/delete-asset/<int:id>')
def delete_asset(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM interventions WHERE asset_id=%s", (id,)
    )
    count = cursor.fetchone()['cnt']

    if count > 0:
        cursor.close()
        conn.close()
        flash("Cannot delete asset: intervention records exist. Delete the interventions first.")
        return redirect('/assets')

    # Fetch asset row before deletion (for audit log)
    cursor.execute("SELECT * FROM assets WHERE id=%s", (id,))
    asset_row = cursor.fetchone()
    old_value = {k: (str(v) if v is not None else None)
                 for k, v in asset_row.items()} if asset_row else {}

    cursor.execute("DELETE FROM assets WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    try:
        log_action(session['user_id'], 'DELETE', 'asset', id,
                   old_value=old_value)
    except Exception as e:
        app.logger.error(f"Audit log failed for delete_asset id={id}: {e}")

    return redirect('/assets')


# ── Interventions ────────────────────────────────────────────────
@app.route('/interventions')
def interventions():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.id, i.description, i.intervention_date, i.status,
               a.asset_tag, a.name as asset_name,
               t.name as technician_name
        FROM interventions i
        JOIN assets a ON i.asset_id = a.id
        JOIN technicians t ON i.technician_id = t.id
        WHERE i.status = 'Active'
        ORDER BY i.intervention_date DESC
    """)
    interventions = cursor.fetchall()

    cursor.execute("""
        SELECT i.id, i.description, i.intervention_date, i.status,
               a.asset_tag, a.name as asset_name,
               t.name as technician_name
        FROM interventions i
        JOIN assets a ON i.asset_id = a.id
        JOIN technicians t ON i.technician_id = t.id
        WHERE i.status = 'Completed'
        ORDER BY i.intervention_date DESC
    """)
    completed_interventions = cursor.fetchall()

    cursor.execute("""
        SELECT id, asset_tag, name FROM assets
        WHERE status = 'Inactive'
        ORDER BY asset_tag
    """)
    assets = cursor.fetchall()

    cursor.execute("SELECT id, name FROM technicians ORDER BY name")
    technicians = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'interventions.html',
        interventions=interventions,
        completed_interventions=completed_interventions,
        assets=assets,
        technicians=technicians
    )


@app.route('/interventions/add', methods=['POST'])
def add_intervention():
    if 'user' not in session:
        return redirect('/login')

    asset_id      = request.form['asset_id']
    technician_id = request.form['technician_id']
    description   = request.form['description']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM assets WHERE id=%s", (asset_id,))
    asset = cursor.fetchone()

    if asset is None:
        cursor.close()
        conn.close()
        flash("Asset not found.")
        return redirect('/interventions'), 404

    if asset['status'] != 'Inactive':
        cursor.close()
        conn.close()
        flash("Asset is not available for intervention.")
        return redirect('/interventions'), 400

    cursor.execute("""
        INSERT INTO interventions (asset_id, technician_id, description, intervention_date, status)
        VALUES (%s, %s, %s, %s, 'Active')
    """, (asset_id, technician_id, description, date.today()))

    new_intervention_id = cursor.lastrowid
    cursor.execute("UPDATE assets SET status='Maintenance' WHERE id=%s", (asset_id,))

    conn.commit()
    cursor.close()
    conn.close()

    try:
        log_action(
            session['user_id'],
            'CREATE',
            'intervention',
            new_intervention_id,
            new_value={
                'asset_id': asset_id,
                'technician_id': technician_id,
                'description': description,
                'intervention_date': str(date.today()),
                'status': 'Active',
            }
        )
    except Exception as e:
        app.logger.error(f"Audit log failed for add_intervention (id={new_intervention_id}): {e}")

    return redirect('/interventions')


@app.route('/interventions/complete/<int:id>')
def complete_intervention(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT asset_id FROM interventions WHERE id=%s", (id,))
    intervention = cursor.fetchone()

    if intervention:
        cursor.execute("UPDATE assets SET status='Active' WHERE id=%s", (intervention['asset_id'],))
        cursor.execute("UPDATE interventions SET status='Completed' WHERE id=%s", (id,))

    conn.commit()
    cursor.close()
    conn.close()

    if intervention:
        try:
            log_action(
                session['user_id'],
                'UPDATE',
                'intervention',
                id,
                old_value={'status': 'Active'},
                new_value={'status': 'Completed'}
            )
        except Exception as e:
            app.logger.error(f"Audit log failed for complete_intervention (id={id}): {e}")

    return redirect('/interventions')


@app.route('/interventions/delete/<int:id>')
def delete_intervention(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM interventions WHERE id=%s", (id,))
    intervention = cursor.fetchone()

    cursor.execute("DELETE FROM interventions WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    if intervention:
        try:
            old_value = {k: v for k, v in intervention.items() if v is not None}
            log_action(
                session['user_id'],
                'DELETE',
                'intervention',
                id,
                old_value=old_value
            )
        except Exception as e:
            app.logger.error(f"Audit log failed for delete_intervention (id={id}): {e}")

    return redirect('/interventions')


# ── Technicians ──────────────────────────────────────────────────
@app.route('/technicians')
def technicians():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM technicians ORDER BY name")
    technicians = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('technicians.html', technicians=technicians)


@app.route('/technicians/add', methods=['POST'])
def add_technician():
    if 'user' not in session:
        return redirect('/login')

    name  = request.form['name']
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO technicians (name, email, phone) VALUES (%s, %s, %s)",
        (name, email, phone)
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()

    new_value = {k: v for k, v in {'name': name, 'email': email, 'phone': phone}.items() if v}
    try:
        log_action(session['user_id'], 'CREATE', 'technician', new_id, new_value=new_value)
    except Exception as e:
        app.logger.error(f"Audit log failed for add_technician id={new_id}: {e}")

    return redirect('/technicians')


@app.route('/technicians/delete/<int:id>')
def delete_technician(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM technicians WHERE id=%s", (id,))
    tech = cursor.fetchone()
    cursor.execute("DELETE FROM technicians WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    if tech:
        old_value = {k: v for k, v in tech.items() if v is not None}
        try:
            log_action(session['user_id'], 'DELETE', 'technician', id, old_value=old_value)
        except Exception as e:
            app.logger.error(f"Audit log failed for delete_technician id={id}: {e}")

    return redirect('/technicians')


# ── Users ────────────────────────────────────────────────────────
@app.route('/users')
def users():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.id, u.username, r.name as role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        ORDER BY u.username
    """)
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM roles ORDER BY name")
    roles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('users.html', users=users, roles=roles)


@app.route('/users/create', methods=['POST'])
def create_user():
    if 'user' not in session:
        return redirect('/login')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role_id  = request.form.get('role_id', '')

    def _rerender(error):
        conn2 = get_connection()
        cur2  = conn2.cursor()
        cur2.execute("""
            SELECT u.id, u.username, r.name as role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            ORDER BY u.username
        """)
        all_users = cur2.fetchall()
        cur2.execute("SELECT * FROM roles ORDER BY name")
        all_roles = cur2.fetchall()
        cur2.close()
        conn2.close()
        return render_template('users.html', users=all_users, roles=all_roles, error=error)

    # ── Validate input fields ─────────────────────────────────────
    if not username or len(username) > 50:
        return _rerender('Username must be between 1 and 50 characters.')
    if len(password) < 8:
        return _rerender('Password must be at least 8 characters.')

    conn = get_connection()
    cursor = conn.cursor()

    # Validate role_id exists
    try:
        role_id_int = int(role_id)
    except (ValueError, TypeError):
        cursor.close()
        conn.close()
        return _rerender('Please select a valid role.')

    cursor.execute("SELECT id FROM roles WHERE id = %s", (role_id_int,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        return _rerender('Selected role does not exist.')

    # ── Duplicate username check (case-insensitive) ───────────────
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
    if cursor.fetchone() is not None:
        cursor.close()
        conn.close()
        return _rerender('Username already in use.')

    # ── Hash password ─────────────────────────────────────────────
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # ── Insert new user ───────────────────────────────────────────
    cursor.execute(
        "INSERT INTO users (username, password, role_id) VALUES (%s, %s, %s)",
        (username, hashed_password, role_id_int)
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()

    # ── Audit log ─────────────────────────────────────────────────
    try:
        log_action(
            session['user_id'], 'CREATE', 'user', new_id,
            new_value={'username': username, 'role_id': role_id_int}
        )
    except Exception as e:
        app.logger.error('audit log failed for create_user id=%s: %s', new_id, e)

    return redirect('/users')


@app.route('/users/delete/<int:id>')
def delete_user(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    # ── Fetch user ────────────────────────────────────────────────
    cursor.execute("SELECT id, username FROM users WHERE id = %s", (id,))
    user = cursor.fetchone()

    if user is None:
        cursor.close()
        conn.close()
        flash('User not found.')
        return redirect('/users')

    username = user['username']

    # ── Self-delete guard ─────────────────────────────────────────
    if username == session['user']:
        cursor.close()
        conn.close()
        flash('Cannot delete your own account.')
        return redirect('/users')

    # ── Delete user ───────────────────────────────────────────────
    cursor.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    # ── Audit log ─────────────────────────────────────────────────
    try:
        log_action(
            session['user_id'], 'DELETE', 'user', id,
            old_value={'username': username}
        )
    except Exception as e:
        app.logger.error('audit log failed for delete_user id=%s: %s', id, e)

    return redirect('/users')


@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    # Fetch the target user
    cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        flash('User not found.')
        return redirect('/users')

    # Fetch all roles for the dropdown
    cursor.execute("SELECT * FROM roles ORDER BY name")
    roles = cursor.fetchall()

    if request.method == 'GET':
        cursor.close()
        conn.close()
        return render_template('edit_user.html', user=user, roles=roles)

    # ── POST — process the edit form ──────────────────────────────
    role_id      = request.form.get('role_id', '').strip()
    new_password = request.form.get('password', '')

    # Validate role_id
    try:
        role_id_int = int(role_id)
    except (ValueError, TypeError):
        cursor.close()
        conn.close()
        return render_template('edit_user.html', user=user, roles=roles,
                               error='Please select a valid role.')

    cursor.execute("SELECT id FROM roles WHERE id = %s", (role_id_int,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return render_template('edit_user.html', user=user, roles=roles,
                               error='Selected role does not exist.')

    old_role_id = user['role_id']

    if new_password:
        if len(new_password) < 8:
            cursor.close()
            conn.close()
            return render_template('edit_user.html', user=user, roles=roles,
                                   error='New password must be at least 8 characters.')
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        cursor.execute(
            "UPDATE users SET role_id = %s, password = %s WHERE id = %s",
            (role_id_int, hashed, id)
        )
    else:
        cursor.execute(
            "UPDATE users SET role_id = %s WHERE id = %s",
            (role_id_int, id)
        )

    conn.commit()
    cursor.close()
    conn.close()

    # ── Audit log ─────────────────────────────────────────────────
    try:
        log_action(
            session['user_id'], 'UPDATE', 'user', id,
            old_value={'role_id': old_role_id},
            new_value={'role_id': role_id_int}
        )
    except Exception as e:
        app.logger.error('audit log failed for edit_user id=%s: %s', id, e)

    return redirect('/users')


# ── Categories ───────────────────────────────────────────────────
@app.route('/categories')
def categories():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name, COUNT(a.id) AS asset_count
        FROM categories c
        LEFT JOIN assets a ON a.category_id = c.id
        GROUP BY c.id, c.name
        ORDER BY c.name
    """)
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('categories.html', categories=categories)


@app.route('/categories/create', methods=['POST'])
def create_category():
    if 'user' not in session:
        return redirect('/login')

    name = request.form.get('name', '').strip()

    # Validation: non-empty and ≤ 100 chars
    if not name:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, COUNT(a.id) AS asset_count
            FROM categories c
            LEFT JOIN assets a ON a.category_id = c.id
            GROUP BY c.id, c.name
            ORDER BY c.name
        """)
        categories_list = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('categories.html', categories=categories_list,
                               error='Category name cannot be empty.')

    if len(name) > 100:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, COUNT(a.id) AS asset_count
            FROM categories c
            LEFT JOIN assets a ON a.category_id = c.id
            GROUP BY c.id, c.name
            ORDER BY c.name
        """)
        categories_list = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('categories.html', categories=categories_list,
                               error='Category name must be 100 characters or fewer.')

    conn = get_connection()
    cursor = conn.cursor()

    # Duplicate check (case-insensitive)
    cursor.execute('SELECT id FROM categories WHERE LOWER(name) = LOWER(%s)', (name,))
    if cursor.fetchone():
        cursor.execute("""
            SELECT c.id, c.name, COUNT(a.id) AS asset_count
            FROM categories c
            LEFT JOIN assets a ON a.category_id = c.id
            GROUP BY c.id, c.name
            ORDER BY c.name
        """)
        categories_list = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('categories.html', categories=categories_list,
                               error=f'Category "{name}" already exists.')

    # Insert new category
    cursor.execute('INSERT INTO categories (name) VALUES (%s)', (name,))
    conn.commit()
    new_id = cursor.lastrowid

    try:
        log_action(
            session['user_id'], 'CREATE', 'category', new_id,
            new_value={'name': name}
        )
    except Exception as e:
        app.logger.error('audit log failed for create_category name=%s: %s', name, e)

    cursor.close()
    conn.close()

    return redirect('/categories')


@app.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    # Fetch the category
    cursor.execute('SELECT id, name FROM categories WHERE id = %s', (category_id,))
    category = cursor.fetchone()
    if not category:
        cursor.close()
        conn.close()
        flash('Category not found.')
        return redirect('/categories')

    if request.method == 'GET':
        cursor.close()
        conn.close()
        return render_template('edit_category.html', category=category)

    # POST: validate
    name = request.form.get('name', '').strip()

    if not name:
        cursor.close()
        conn.close()
        return render_template('edit_category.html', category=category,
                               error='Category name cannot be empty.')

    if len(name) > 100:
        cursor.close()
        conn.close()
        return render_template('edit_category.html', category=category,
                               error='Category name must be 100 characters or fewer.')

    # Duplicate check excluding self
    cursor.execute(
        'SELECT id FROM categories WHERE LOWER(name) = LOWER(%s) AND id != %s',
        (name, category_id)
    )
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return render_template('edit_category.html', category=category,
                               error=f'Category "{name}" already exists.')

    old_name = category['name']

    # Update
    cursor.execute('UPDATE categories SET name = %s WHERE id = %s', (name, category_id))
    conn.commit()

    try:
        log_action(
            session['user_id'], 'UPDATE', 'category', category_id,
            old_value={'name': old_name},
            new_value={'name': name}
        )
    except Exception as e:
        app.logger.error('audit log failed for edit_category id=%s: %s', category_id, e)

    cursor.close()
    conn.close()

    return redirect('/categories')


@app.route('/categories/delete/<int:category_id>')
def delete_category(category_id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    # Fetch the category
    cursor.execute('SELECT id, name FROM categories WHERE id = %s', (category_id,))
    category = cursor.fetchone()
    if not category:
        cursor.close()
        conn.close()
        flash('Category not found.')
        return redirect('/categories')

    name = category['name']

    # Asset-count guard
    cursor.execute('SELECT COUNT(*) AS cnt FROM assets WHERE category_id = %s', (category_id,))
    row = cursor.fetchone()
    count = row['cnt'] if row else 0
    if count > 0:
        cursor.close()
        conn.close()
        flash(f'Cannot delete: {count} asset(s) use this category.')
        return redirect('/categories')

    # Delete category
    cursor.execute('DELETE FROM categories WHERE id = %s', (category_id,))
    conn.commit()

    try:
        log_action(
            session['user_id'], 'DELETE', 'category', category_id,
            old_value={'name': name}
        )
    except Exception as e:
        app.logger.error('audit log failed for delete_category id=%s: %s', category_id, e)

    cursor.close()
    conn.close()

    return redirect('/categories')


# ── Audit Log ────────────────────────────────────────────────────
@app.route('/audit-log')
def audit_log_view():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT al.id, al.timestamp, u.username, al.action,
               al.entity_type, al.entity_id, al.old_value, al.new_value
        FROM audit_log al
        JOIN users u ON al.user_id = u.id
        ORDER BY al.timestamp DESC
        LIMIT 500
    """)
    entries = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('audit_log.html', entries=entries)


# ── Reports ──────────────────────────────────────────────────────
@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM assets")
    total_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Active'")
    active_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Maintenance'")
    maintenance_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Inactive'")
    inactive_assets = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM interventions WHERE status='Completed'")
    completed_interventions = cursor.fetchone()['COUNT(*)']

    cursor.close()
    conn.close()

    return render_template(
        'reports.html',
        total_assets=total_assets,
        active_assets=active_assets,
        maintenance_assets=maintenance_assets,
        inactive_assets=inactive_assets,
        completed_interventions=completed_interventions
    )


@app.route('/export-assets')
def export_assets():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.asset_tag, a.name, a.brand, a.model, a.serial_number,
               c.name as category, a.status, a.location,
               a.purchase_date, a.warranty_expiration, a.notes
        FROM assets a
        LEFT JOIN categories c ON a.category_id = c.id
        ORDER BY a.asset_tag
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    df = pd.DataFrame(rows)
    df.columns = ['Asset Tag', 'Name', 'Brand', 'Model', 'Serial Number',
                  'Category', 'Status', 'Location',
                  'Purchase Date', 'Warranty Expiration', 'Notes']

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Assets')
        ws = writer.sheets['Assets']
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=f"assets_report_{date.today()}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ── Logout ───────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ── Errors ───────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    import traceback
    return f"<pre>{traceback.format_exc()}</pre>", 500


if __name__ == '__main__':
    app.run(debug=True)