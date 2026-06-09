from flask import Flask, render_template, request, redirect, session, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection
from datetime import date, datetime, timedelta
from functools import wraps
import pandas as pd

app = Flask(__name__)
app.secret_key = "evolve_secret_key"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM users
            WHERE username=%s
        """, (username,))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            session['user_id'] = user['id']
            return redirect('/dashboard')

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route('/dashboard')
@login_required
def dashboard():

    conn = get_connection()
    cursor = conn.cursor()

    # Contagem de Assets
    cursor.execute("SELECT COUNT(*) FROM assets")
    total_assets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Active'")
    active_assets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Maintenance'")
    maintenance_assets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Inactive'")
    inactive_assets = cursor.fetchone()[0]

    # --- CORREÇÃO: Nova contagem para as Intervenções ---
    cursor.execute("SELECT COUNT(*) FROM interventions")
    total_interventions = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    # Passar todas as variáveis necessárias para o template
    return render_template(
        "dashboard.html",
        total_assets=total_assets,
        active_assets=active_assets,
        maintenance_assets=maintenance_assets,
        inactive_assets=inactive_assets,
        total_interventions=total_interventions  # <-- Variável adicionada aqui!
    )


@app.route('/assets')
@login_required
def assets():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM assets")
    assets = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("assets.html", assets=assets)


@app.route('/add-asset', methods=['GET', 'POST'])
@login_required
def add_asset():

    if request.method == 'POST':
        asset_tag = request.form['asset_tag']
        name = request.form['name']
        brand = request.form['brand']
        model = request.form['model']
        status = request.form['status']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO assets (asset_tag, name, brand, model, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (asset_tag, name, brand, model, status))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/assets')

    return render_template("add_asset.html")


@app.route('/edit-asset/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_asset(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        asset_tag = request.form['asset_tag']
        name = request.form['name']
        brand = request.form['brand']
        model = request.form['model']
        status = request.form['status']

        cursor.execute("""
            UPDATE assets
            SET asset_tag=%s, name=%s, brand=%s, model=%s, status=%s
            WHERE id=%s
        """, (asset_tag, name, brand, model, status, id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/assets')

    cursor.execute("SELECT * FROM assets WHERE id=%s", (id,))
    asset = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("edit_asset.html", asset=asset)


@app.route('/delete-asset/<int:id>')
@login_required
def delete_asset(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM assets WHERE id=%s", (id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/assets')


@app.route('/reports')
@login_required
def reports():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM assets")
    total_assets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM assets WHERE status='Active'")
    active_assets = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        'reports.html',
        total_assets=total_assets,
        active_assets=active_assets
    )


@app.route('/interventions')
@login_required
def interventions():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT i.id, i.description, i.intervention_date, i.status,
               a.asset_tag, a.name as asset_name,
               t.name as technician_name
        FROM interventions i
        JOIN assets a ON i.asset_id = a.id
        JOIN technicians t ON i.technician_id = t.id
        ORDER BY i.intervention_date DESC
    """)
    interventions = cursor.fetchall()

    cursor.execute("""
        SELECT id, asset_tag, name FROM assets
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
        assets=assets,
        technicians=technicians
    )


@app.route('/interventions/add', methods=['POST'])
@login_required
def add_intervention():

    asset_id = request.form['asset_id']
    technician_id = request.form['technician_id']
    description = request.form['description']
    intervention_date = request.form.get('intervention_date', date.today())

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO interventions (asset_id, technician_id, description, intervention_date, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (asset_id, technician_id, description, intervention_date, 'Pending'))

    cursor.execute("""
        UPDATE assets SET status='Maintenance' WHERE id=%s
    """, (asset_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/interventions')


@app.route('/interventions/delete/<int:id>')
@login_required
def delete_intervention(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM interventions WHERE id=%s", (id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/interventions')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/export-assets')
@login_required
def export_assets():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM assets", conn)
    conn.close()

    filename = "assets_report.csv"
    df.to_csv(filename, index=False)

    return send_file(filename, as_attachment=True)

@app.route('/interventions/complete/<int:id>')
def complete_intervention(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Busca o asset_id da intervenção
    cursor.execute("SELECT asset_id FROM interventions WHERE id=%s", (id,))
    intervention = cursor.fetchone()

    if intervention:
        # Atualiza status para Completed em vez de apagar
        cursor.execute(
            "UPDATE interventions SET status='Completed' WHERE id=%s",
            (id,)
        )
        # Muda o asset para Active
        cursor.execute(
            "UPDATE assets SET status='Active' WHERE id=%s",
            (intervention['asset_id'],)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/interventions')


# ========== NEW FEATURES ==========

# Asset Detail Page
@app.route('/asset/<int:id>')
@login_required
def asset_detail(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get asset info
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
        return render_template("404.html"), 404

    # Get intervention history
    cursor.execute("""
        SELECT i.id, i.description, i.intervention_date, i.status,
               t.name as technician_name, i.created_at
        FROM interventions i
        JOIN technicians t ON i.technician_id = t.id
        WHERE i.asset_id=%s
        ORDER BY i.intervention_date DESC
    """, (id,))
    interventions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("asset_detail.html", asset=asset, interventions=interventions)


# Technician Management
@app.route('/technicians')
@login_required
def technicians():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM technicians ORDER BY name")
    technicians = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("technicians.html", technicians=technicians)


@app.route('/technician/add', methods=['GET', 'POST'])
@login_required
def add_technician():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO technicians (name, email, phone)
            VALUES (%s, %s, %s)
        """, (name, email, phone))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/technicians')

    return render_template("add_technician.html")


@app.route('/technician/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_technician(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')

        cursor.execute("""
            UPDATE technicians
            SET name=%s, email=%s, phone=%s
            WHERE id=%s
        """, (name, email, phone, id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/technicians')

    cursor.execute("SELECT * FROM technicians WHERE id=%s", (id,))
    technician = cursor.fetchone()

    cursor.close()
    conn.close()

    if not technician:
        return render_template("404.html"), 404

    return render_template("edit_technician.html", technician=technician)


@app.route('/technician/delete/<int:id>')
@login_required
def delete_technician(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM technicians WHERE id=%s", (id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/technicians')


# API for Dashboard Chart
@app.route('/api/assets-by-status')
@login_required
def api_assets_by_status():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM assets
        GROUP BY status
        ORDER BY status
    """)
    
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    result = {
        'labels': [row['status'] for row in data],
        'data': [row['count'] for row in data]
    }

    return jsonify(result)


# API for Asset Filtering
@app.route('/api/assets')
@login_required
def api_assets():
    status = request.args.get('status', '')
    brand = request.args.get('brand', '')
    category = request.args.get('category', '')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM assets WHERE 1=1"
    params = []

    if status:
        query += " AND status=%s"
        params.append(status)
    if brand:
        query += " AND brand=%s"
        params.append(brand)
    if category:
        query += " AND category_id=%s"
        params.append(category)

    cursor.execute(query, params)
    assets = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([dict(row) for row in assets])


# 404 Error Handler
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == '__main__':
    app.run(debug=True)