from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail, Message
#import threading

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

# ---------------- MAIL CONFIG ---------------- #
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='smartcampusassistants@gmail.com',
    MAIL_PASSWORD='zzkbjxbnnnmjfdzr'
)
mail = Mail(app)

# ---------------- DATABASE ---------------- #
db = SQLAlchemy(app)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    last_reminder_sent = db.Column(db.DateTime, nullable=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)

# ---------------- EMAIL FUNCTION ---------------- #
def send_reminder(assignment_title, to_email):
    try:
        msg = Message(
            'Assignment Reminder',
            sender=app.config['MAIL_USERNAME'],
            recipients=[to_email]
        )
        msg.body = f'Reminder: Your assignment "{assignment_title}" is due soon!'
        mail.send(msg)
        print(f"[SUCCESS] Reminder sent to {to_email} for {assignment_title}")
    except Exception as e:
        print(f"[ERROR] Failed to send reminder to {to_email}: {e}")

def send_reminders_async(title, students):
    """Send instant reminders in a separate thread to prevent blocking"""
    for student in students:
        send_reminder(title, student.email)

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
    return "Invalid Credentials"

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']

    existing_user = Student.query.filter(
        (Student.username == username) | (Student.email == email)
    ).first()
    if existing_user:
        return "Error: Username or Email already exists. Try another."

    new_user = Student(username=username, password=password, email=email)
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
        due_date_str = request.form['due_date']

        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")

        new_assignment = Assignment(
            title=title,
            due_date=due_date,
            last_reminder_sent=datetime.now()  # mark as sent immediately
        )
        db.session.add(new_assignment)
        db.session.commit()

        # ---- Send instant reminders asynchronously ----
        #students = Student.query.all()
        #threading.Thread(target=send_reminders_async, args=(title, students)).start()
        # Get all student emails
        students = Student.query.with_entities(Student.email).all()
        emails = [s[0] for s in students]

        # Send emails synchronously (SAFE FOR PRODUCTION)
        for email in emails:
            send_reminder(title, email)
        #threading.Thread(target=send_reminders_async, args=(title, emails)).start()

        return redirect(url_for('dashboard'))

    assignments = Assignment.query.all()
    courses = Course.query.all()

    total = len(assignments)
    today = datetime.today()
    overdue = sum(1 for a in assignments if a.due_date < today)
    upcoming = total - overdue
    week_counts = [0]*7

    for a in assignments:
        weekday = a.due_date.weekday()
        week_counts[weekday] += 1

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

# ---------------- RECURRING REMINDERS ---------------- #
def check_assignments_and_send_reminders():
    """Send reminders for assignments if 6 hours passed since last reminder"""
    with app.app_context():
        now = datetime.now()
        assignments = Assignment.query.all()
        students = Student.query.all()

        for a in assignments:
            if a.due_date <= now:
                continue
            if not a.last_reminder_sent:
                for student in students:
                    send_reminder(a.title, student.email)
                a.last_reminder_sent = now
                db.session.commit()
                continue
            hours_since_last = (now - a.last_reminder_sent).total_seconds() / 3600
            if hours_since_last >= 6:
                for student in students:
                    send_reminder(a.title, student.email)
                a.last_reminder_sent = now
                db.session.commit()

# ---------------- CLOUD CRON JOB ENDPOINT ---------------- #
@app.route('/send_reminders')
def send_reminders_endpoint():
    #threading.Thread(target=check_assignments_and_send_reminders).start()
    return "Reminders checked asynchronously!"

# ---- Send instant reminders asynchronously ----
#def send_reminders_async(title, students):
    #with app.app_context():  # <--- ensure Flask app context is active
        #for student in students:
            #send_reminder(title, student.email)          

# ---------------- RUN APP ---------------- #
#if __name__ == '__main__':
   # with app.app_context():
        #db.create_all()  # Never drop DB, preserves registered users

    #port = 5000
    #app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)