from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_file
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
import io
import csv
from datetime import datetime, date

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'data.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'dev-secret-change-me')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

def owner_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'owner':
            flash('Owner access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return wrapped

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    if user_id:
        g.user = query_db('SELECT id, username, role FROM users WHERE id = ?', (user_id,), one=True)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = query_db('SELECT * FROM users WHERE username = ?', (username,), one=True)
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/transactions')
@login_required
def transactions():
    rows = query_db('SELECT * FROM transactions ORDER BY date DESC')
    return render_template('transactions.html', transactions=rows)

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
@owner_required
def add_transaction():
    if request.method == 'POST':
        counterparty = request.form.get('counterparty', '').strip()
        item = request.form.get('item', '').strip()
        transaction_type = request.form.get('transaction_type', '').strip()
        description = request.form.get('description', '').strip()
        amount = request.form.get('amount', '').strip()
        date_value = request.form.get('date') or date.today().isoformat()

        if not counterparty or not item or not amount or not transaction_type:
            flash('All fields except description are required', 'danger')
            return render_template('add_edit_transaction.html', action='Add', tx=request.form)

        try:
            amount_value = float(amount)
        except ValueError:
            flash('Amount must be a number', 'danger')
            return render_template('add_edit_transaction.html', action='Add', tx=request.form)

        execute_db(
            'INSERT INTO transactions (counterparty, item, transaction_type, amount, date, description, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)',
            (counterparty, item, transaction_type, amount_value, date_value, description, session.get('username'), datetime.utcnow().isoformat()),
        )
        flash('Transaction added', 'success')
        return redirect(url_for('transactions'))
    return render_template('add_edit_transaction.html', action='Add', tx=None)

@app.route('/transactions/edit/<int:tid>', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_transaction(tid):
    tx = query_db('SELECT * FROM transactions WHERE id = ?', (tid,), one=True)
    if not tx:
        flash('Transaction not found', 'danger')
        return redirect(url_for('transactions'))
    if request.method == 'POST':
        counterparty = request.form.get('counterparty', '').strip()
        item = request.form.get('item', '').strip()
        transaction_type = request.form.get('transaction_type', '').strip()
        description = request.form.get('description', '').strip()
        amount = request.form.get('amount', '').strip()
        date_value = request.form.get('date') or tx['date']

        if not counterparty or not item or not amount or not transaction_type:
            flash('All fields except description are required', 'danger')
            return render_template('add_edit_transaction.html', action='Edit', tx=request.form)

        try:
            amount_value = float(amount)
        except ValueError:
            flash('Amount must be a number', 'danger')
            return render_template('add_edit_transaction.html', action='Edit', tx=request.form)

        execute_db(
            'UPDATE transactions SET counterparty=?, item=?, transaction_type=?, amount=?, date=?, description=? WHERE id=?',
            (counterparty, item, transaction_type, amount_value, date_value, description, tid),
        )
        flash('Transaction updated', 'success')
        return redirect(url_for('transactions'))
    return render_template('add_edit_transaction.html', action='Edit', tx=tx)

@app.route('/transactions/delete/<int:tid>', methods=['POST'])
@login_required
@owner_required
def delete_transaction(tid):
    execute_db('DELETE FROM transactions WHERE id = ?', (tid,))
    flash('Transaction deleted', 'success')
    return redirect(url_for('transactions'))

@app.route('/reports/daily')
@login_required
@owner_required
def daily_report():
    selected_date = request.args.get('date') or date.today().isoformat()
    rows = query_db('SELECT * FROM transactions WHERE date = ? ORDER BY id', (selected_date,))
    total = sum(r['amount'] for r in rows)
    return render_template('reports.html', date=selected_date, transactions=rows, total=total)

@app.route('/reports/daily/download')
@login_required
@owner_required
def daily_report_download():
    selected_date = request.args.get('date') or date.today().isoformat()
    rows = query_db('SELECT * FROM transactions WHERE date = ? ORDER BY id', (selected_date,))
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['id', 'counterparty', 'item', 'type', 'amount', 'date', 'description', 'created_by', 'created_at'])
    for r in rows:
        cw.writerow([
            r['id'],
            r['counterparty'],
            r['item'],
            r['transaction_type'],
            r['amount'],
            r['date'],
            r['description'],
            r['created_by'],
            r['created_at'],
        ])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=f'report_{selected_date}.csv')

@app.route('/invoices/<int:tid>')
@login_required
@owner_required
def invoice(tid):
    tx = query_db('SELECT * FROM transactions WHERE id = ?', (tid,), one=True)
    if not tx:
        flash('Transaction not found', 'danger')
        return redirect(url_for('transactions'))
    return render_template('invoice.html', tx=tx)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
