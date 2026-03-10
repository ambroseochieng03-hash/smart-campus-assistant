from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- APP SETUP ---------------- #
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'

# SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- DATABASE MODELS ---------------- #

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)  # allow duplicate emails
    password = db.Column(db.String(200), nullable=False)  # hashed password


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)


# ---------------- CREATE TABLES ---------------- #
with app.app_context():
    db.create_all()


# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    hashed_pw = generate_password_hash(password)
    new_user = Student(username=username, email=email, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    session['user'] = email
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    users = Student.query.filter_by(email=email).all()
    
    for user in users:
        if check_password_hash(user.password, password):
            session['user'] = email
            return redirect(url_for('dashboard'))

    # Instead of plain text, render the login page with an error flag
    return render_template('index.html', login_error=True, email=email)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        due_date_str = request.form.get('due_date')
        if title and due_date_str:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            new_assignment = Assignment(title=title, due_date=due_date)
            db.session.add(new_assignment)
            db.session.commit()
            return redirect(url_for('dashboard'))

    assignments = Assignment.query.order_by(Assignment.due_date).all()
    courses = Course.query.all()

    total = len(assignments)
    today = datetime.today()
    overdue = sum(1 for a in assignments if a.due_date < today)
    upcoming = total - overdue
    week_counts = [0]*7
    for a in assignments:
        weekday = a.due_date.weekday()
        week_counts[weekday] += 1

    return render_template(
        'dashboard.html',
        assignments=assignments,
        courses=courses,
        total=total,
        overdue=overdue,
        upcoming=upcoming,
        today=today,
        week_counts=week_counts
    )


@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect(url_for('index'))

    assignment = Assignment.query.get_or_404(id)
    db.session.delete(assignment)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/add_course', methods=['POST'])
def add_course():
    if 'user' not in session:
        return redirect(url_for('index'))

    name = request.form.get('name')
    day = request.form.get('day')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    if name and day and start_time and end_time:
        course = Course(name=name, day=day, start_time=start_time, end_time=end_time)
        db.session.add(course)
        db.session.commit()

    return redirect(url_for('dashboard'))


# ---------------- LOCAL RUN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)