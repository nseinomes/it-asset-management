from flask import Flask, render_template, request, redirect, session, send_file
from database import get_connection
from datetime import date
import pandas as pd

app = Flask(__name__)
app.secret_key = "evolve_secret_key"


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
            AND password=%s
        """, (username, password))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session['user'] = user['username']
            return redirect('/dashboard')

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

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
def assets():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM assets")
    assets = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("assets.html", assets=assets)


@app.route('/add-asset', methods=['GET', 'POST'])
def add_asset():
    if 'user' not in session:
        return redirect('/login')

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
def edit_asset(id):
    if 'user' not in session:
        return redirect('/login')

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


@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect('/login')

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
def interventions():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT i.id, i.description, i.intervention_date,
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

    asset_id = request.form['asset_id']
    technician_id = request.form['technician_id']
    description = request.form['description']
    intervention_date = date.today()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO interventions (asset_id, technician_id, description, intervention_date)
        VALUES (%s, %s, %s, %s)
    """, (asset_id, technician_id, description, intervention_date))

    cursor.execute("""
        UPDATE assets SET status='Maintenance' WHERE id=%s
    """, (asset_id,))

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


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/export-assets')
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
        # Muda o asset para Active
        cursor.execute(
            "UPDATE assets SET status='Active' WHERE id=%s",
            (intervention['asset_id'],)
        )
        # Apaga a intervenção
        cursor.execute("DELETE FROM interventions WHERE id=%s", (id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/interventions')


if __name__ == '__main__':
    app.run(debug=True)