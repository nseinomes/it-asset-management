from flask import Flask, render_template, request, redirect, session, send_file, flash
from database import get_connection
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "evolve_secret_key"
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

    cursor.execute("SELECT COUNT(*) FROM interventions")
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

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.*, c.name as category_name
        FROM assets a
        LEFT JOIN categories c ON a.category_id = c.id
        ORDER BY a.id DESC
    """)
    assets = cursor.fetchall()

    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("assets.html", assets=assets, categories=categories)


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
        cursor.close()
        conn.close()
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
    cursor.execute("DELETE FROM assets WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
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
        assets=assets,
        technicians=technicians
    )


@app.route('/interventions/add', methods=['POST'])
def add_intervention():
    if 'user' not in session:
        return redirect('/login')

    asset_id       = request.form['asset_id']
    technician_id  = request.form['technician_id']
    description    = request.form['description']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO interventions (asset_id, technician_id, description, intervention_date, status)
        VALUES (%s, %s, %s, %s, 'Active')
    """, (asset_id, technician_id, description, date.today()))

    cursor.execute("UPDATE assets SET status='Maintenance' WHERE id=%s", (asset_id,))

    conn.commit()
    cursor.close()
    conn.close()
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
    return redirect('/interventions')


@app.route('/interventions/delete/<int:id>')
def delete_intervention(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM interventions WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
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
    cursor.close()
    conn.close()
    return redirect('/technicians')


@app.route('/technicians/delete/<int:id>')
def delete_technician(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM technicians WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/technicians')


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


# ── Auth ─────────────────────────────────────────────────────────
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