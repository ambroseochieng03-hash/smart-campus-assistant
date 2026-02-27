from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

# Flask-Mail (stub: configure for real emails later)
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='YOUR_EMAIL@gmail.com',
    MAIL_PASSWORD='YOUR_EMAIL_PASSWORD'
)
mail = Mail(app)

db = SQLAlchemy(app)

# ---------------- MODELS ---------------- #
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.String(100), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # e.g., Monday
    start_time = db.Column(db.String(5), nullable=False)  # HH:MM
    end_time = db.Column(db.String(5), nullable=False)

# ---------------- ROUTES ---------------- #
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = Student.query.filter_by(username=username, password=password).first()
    if user:
        session['user'] = username
        return redirect(url_for('dashboard'))
    else:
        return "Invalid Credentials"

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    new_user = Student(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    session['user'] = username
    return redirect(url_for('dashboard'))

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
        due_date = request.form['due_date']
        new_assignment = Assignment(title=title, due_date=due_date)
        db.session.add(new_assignment)
        db.session.commit()
        return redirect(url_for('dashboard'))

    assignments = Assignment.query.all()
    courses = Course.query.all()

    # Stats
    total = len(assignments)
    today = datetime.today().date()
    overdue = 0
    upcoming = 0
    week_counts = [0]*7  # Monday=0 ... Sunday=6

    for a in assignments:
        due = datetime.strptime(a.due_date, "%Y-%m-%d").date()
        weekday = due.weekday()
        week_counts[weekday] += 1
        if due < today:
            overdue += 1
        else:
            upcoming += 1

    return render_template('dashboard.html',
                           assignments=assignments,
                           courses=courses,
                           total=total,
                           overdue=overdue,
                           upcoming=upcoming,
                           today=today,
                           week_counts=week_counts)

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

# ---------------- EMAIL STUB ---------------- #
def send_reminder(assignment_title, to_email):
    # For Expo demo, just simulate sending
    msg = Message('Assignment Reminder',
                  sender='YOUR_EMAIL@gmail.com',
                  recipients=[to_email])
    msg.body = f'Reminder: Your assignment "{assignment_title}" is due soon!'
    # mail.send(msg)  # Uncomment when real email configured
    print(f"Reminder sent to {to_email} for assignment {assignment_title}")

# ---------------- RUN ---------------- #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)