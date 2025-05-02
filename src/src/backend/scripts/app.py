import sys
import os
# Add project root (HRMS_Chatbot/) to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from src.backend.scripts.query_data import query_rag
import psycopg2
from psycopg2 import sql
import bcrypt
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv

app = Flask(__name__, template_folder='../../templates', static_folder='../../frontend')
app.secret_key = secrets.token_hex(16)
load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        dbname=os.getenv('DB_NAME', 'hr_chatbot'),
        user=os.getenv('DB_USER', 'hr_user'),
        password=os.getenv('DB_PASSWORD')
    )

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            employee_id TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            job_title TEXT NOT NULL,
            is_verified BOOLEAN NOT NULL DEFAULT FALSE,
            reset_token TEXT,
            reset_expiry TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

class User(UserMixin):
    def __init__(self, id, email, name, employee_id, department, job_title, is_verified):
        self.id = id
        self.email = email
        self.name = name
        self.employee_id = employee_id
        self.department = department
        self.job_title = job_title
        self.is_verified = is_verified

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, email, name, employee_id, department, job_title, is_verified FROM users WHERE id = %s', (user_id,))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(*user_data)
    return None

def send_email(to_email, subject, body, is_html=False):
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_name = os.getenv('SENDER_NAME', 'GBS HR Assistant')

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = f"{sender_name} <{smtp_user}>"
    msg['To'] = to_email

    if is_html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

@app.route('/')
def index():
    if current_user.is_authenticated and current_user.is_verified:
        return redirect(url_for('chat_page'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email').strip().lower()
    password = request.form.get('password').strip()

    if not email or not password:
        flash('All fields are required!', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, email, password_hash, name, employee_id, department, job_title, is_verified FROM users WHERE email = %s', (email,))
    user_data = c.fetchone()
    conn.close()

    if user_data:
        if bcrypt.checkpw(password.encode('utf-8'), user_data[2].encode('utf-8')):
            if user_data[7]:
                user = User(user_data[0], user_data[1], user_data[3], user_data[4], user_data[5], user_data[6], user_data[7])
                login_user(user)
                return redirect(url_for('chat_page'))
            else:
                flash('Please verify your email first.', 'error')
                return redirect(url_for('index') + '#verify')
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid email or password.', 'error')
        return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name').strip()
    email = request.form.get('email').strip().lower()
    password = request.form.get('password').strip()
    employee_id = request.form.get('employee_id').strip()
    department = request.form.get('department').strip()
    job_title = request.form.get('job_title').strip()

    if not all([name, email, password, employee_id, department, job_title]):
        flash('All fields are required!', 'error')
        return redirect(url_for('index') + '#register')

    if len(password) < 8:
        flash('Password must be at least 8 characters long.', 'error')
        return redirect(url_for('index') + '#register')
    if '@' not in email or '.' not in email:
        flash('Invalid email format.', 'error')
        return redirect(url_for('index') + '#register')

    valid_departments = ['HR', 'IT', 'Finance', 'Marketing', 'Operations']
    if department not in valid_departments:
        flash('Invalid department selected.', 'error')
        return redirect(url_for('index') + '#register')

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO users (email, password_hash, name, employee_id, department, job_title)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (email, password_hash, name, employee_id, department, job_title))
        conn.commit()

        token = secrets.token_urlsafe(32)
        c.execute('UPDATE users SET reset_token = %s, reset_expiry = %s WHERE email = %s',
                  (token, datetime.now() + timedelta(hours=1), email))
        conn.commit()
        conn.close()

        verify_url = f"http://{request.host}/verify_email?token={token}"
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Welcome to GBS HR Assistant!</h2>
                <p>Please verify your email to activate your account.</p>
                <a href="{verify_url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 5px;">Verify Email</a>
                <p>Or copy this link: {verify_url}</p>
                <p>This link expires in 1 hour.</p>
                <p>Best regards,<br>GBS HR Assistant Team</p>
            </body>
        </html>
        """
        if send_email(email, 'Verify Your GBS HR Assistant Account', email_body, is_html=True):
            flash('Registration successful! Please verify your email.', 'info')
            return redirect(url_for('index') + '#verify')
        else:
            flash('Failed to send verification email. Please try again.', 'error')
            return redirect(url_for('index') + '#register')

    except psycopg2.IntegrityError:
        conn.close()
        flash('Email or Employee ID already registered.', 'error')
        return redirect(url_for('index') + '#register')

@app.route('/verify_email', methods=['GET'])
def verify_email():
    token = request.args.get('token')
    if not token:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT email, reset_expiry FROM users WHERE reset_token = %s', (token,))
    user_data = c.fetchone()

    if user_data and user_data[1] > datetime.now():
        c.execute('UPDATE users SET is_verified = TRUE, reset_token = NULL, reset_expiry = NULL WHERE reset_token = %s', (token,))
        conn.commit()
        flash('Email verified successfully! Please log in.', 'info')
    else:
        flash('Verification link is invalid or expired.', 'error')

    conn.close()
    return redirect(url_for('index'))

@app.route('/resend_verification', methods=['POST'])
def resend_verification():
    email = request.form.get('email').strip().lower()
    if not email:
        flash('Email is required!', 'error')
        return redirect(url_for('index') + '#verify')

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT is_verified FROM users WHERE email = %s', (email,))
    user_data = c.fetchone()

    if user_data:
        if user_data[0]:
            flash('This email is already verified.', 'error')
        else:
            token = secrets.token_urlsafe(32)
            c.execute('UPDATE users SET reset_token = %s, reset_expiry = %s WHERE email = %s',
                      (token, datetime.now() + timedelta(hours=1), email))
            conn.commit()

            verify_url = f"http://{request.host}/verify_email?token={token}"
            email_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>GBS HR Assistant</h2>
                    <p>We’ve resent your verification link.</p>
                    <a href="{verify_url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 5px;">Verify Email</a>
                    <p>Or copy this link: {verify_url}</p>
                    <p>This link expires in 1 hour.</p>
                    <p>Best regards,<br>GBS HR Assistant Team</p>
                </body>
            </html>
            """
            if send_email(email, 'Verify Your GBS HR Assistant Account', email_body, is_html=True):
                flash('Verification email resent! Check your inbox.', 'info')
            else:
                flash('Failed to resend verification email.', 'error')
    else:
        flash('Email not found.', 'error')

    conn.close()
    return redirect(url_for('index') + '#verify')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('new_password', '').strip()

        if email:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = %s', (email,))
            user_data = c.fetchone()

            if user_data:
                token = secrets.token_urlsafe(32)
                c.execute('UPDATE users SET reset_token = %s, reset_expiry = %s WHERE email = %s',
                          (token, datetime.now() + timedelta(hours=1), email))
                conn.commit()

                reset_url = f"http://{request.host}/reset_password?token={token}"
                email_body = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <h2>GBS HR Assistant Password Reset</h2>
                        <p>Click below to reset your password.</p>
                        <a href="{reset_url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 5px;">Reset Password</a>
                        <p>Or copy this link: {reset_url}</p>
                        <p>This link expires in 1 hour.</p>
                        <p>Best regards,<br>GBS HR Assistant Team</p>
                    </body>
                </html>
                """
                if send_email(email, 'GBS HR Assistant Password Reset', email_body, is_html=True):
                    flash('Password reset email sent! Check your inbox.', 'info')
                else:
                    flash('Failed to send reset email.', 'error')
            else:
                flash('Email not found.', 'error')

            conn.close()
            return redirect(url_for('index'))

        elif new_password:
            token = request.args.get('token')
            if not token:
                flash('Invalid reset link.', 'error')
                return redirect(url_for('index'))

            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT email, reset_expiry FROM users WHERE reset_token = %s', (token,))
            user_data = c.fetchone()

            if user_data and user_data[1] > datetime.now():
                if len(new_password) < 8:
                    flash('Password must be at least 8 characters long.', 'error')
                    conn.close()
                    return redirect(url_for('reset_password') + f'?token={token}')

                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                c.execute('UPDATE users SET password_hash = %s, reset_token = NULL, reset_expiry = NULL WHERE reset_token = %s',
                          (password_hash, token))
                conn.commit()
                flash('Password reset successfully! Please log in.', 'info')
            else:
                flash('Reset link is invalid or expired.', 'error')

            conn.close()
            return redirect(url_for('index'))

    token = request.args.get('token')
    if token:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT email, reset_expiry FROM users WHERE reset_token = %s', (token,))
        user_data = c.fetchone()
        conn.close()

        if user_data and user_data[1] > datetime.now():
            return render_template('reset_password.html', token=token)
        else:
            flash('Reset link is invalid or expired.', 'error')
            return redirect(url_for('index'))

    return render_template('reset_password.html')

@app.route('/chat_page')
@login_required
def chat_page():
    if not current_user.is_verified:
        logout_user()
        flash('Please verify your email to access the chatbot.', 'error')
        return redirect(url_for('index') + '#verify')
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = data.get('question')
    try:
        answer = query_rag(question)
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'answer': 'Sorry, I encountered an error. Please try again.'}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)