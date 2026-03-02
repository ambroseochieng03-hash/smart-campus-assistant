from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ---------------- SETUP ---------------- #
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

db = SQLAlchemy(app)

# Create tables automatically in production
with app.app_context():
    db.drop_all()
    db.create_all()

# ---------------- DATABASE MODELS ---------------- #

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)   # removed unique=True
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)      # removed unique=True


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']

    new_user = Student(username=username, password=password, email=email)
    db.session.add(new_user)
    db.session.commit()

    session['user'] = username
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = Student.query.filter_by(username=username, password=password).first()

    if user:
        session['user'] = username
        return redirect(url_for('dashboard'))

    return "Invalid Credentials"


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        due_date_str = request.form['due_date']
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")

        new_assignment = Assignment(title=title, due_date=due_date)
        db.session.add(new_assignment)
        db.session.commit()

        return redirect(url_for('dashboard'))

    assignments = Assignment.query.all()
    courses = Course.query.all()

    total = len(assignments)
    today = datetime.today()
    overdue = sum(1 for a in assignments if a.due_date < today)
    upcoming = total - overdue

    return render_template(
        'dashboard.html',
        assignments=assignments,
        courses=courses,
        total=total,
        overdue=overdue,
        upcoming=upcoming,
        today=today
    )


@app.route('/delete/<int:id>')
def delete(id):
    assignment = Assignment.query.get_or_404(id)
    db.session.delete(assignment)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/add_course', methods=['POST'])
def add_course():
    if 'user' not in session:
        return redirect(url_for('index'))

    name = request.form['name']
    day = request.form['day']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    course = Course(name=name, day=day, start_time=start_time, end_time=end_time)
    db.session.add(course)
    db.session.commit()

    return redirect(url_for('dashboard'))

# ---------------- RUN LOCAL ONLY ---------------- #
if __name__ == '__main__':
    app.run(debug=True)