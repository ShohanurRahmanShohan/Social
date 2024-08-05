from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import random
import string

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'uploads'
STATUS_FOLDER = 'statuses'
USERS_FILE = 'users.json'
LOG_FILE = 'status_log.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATUS_FOLDER, exist_ok=True)

# Load or initialize users
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'r') as f:
        USERS = json.load(f)
else:
    USERS = {}

# Load or initialize status log
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        STATUS_LOG = json.load(f)
else:
    STATUS_LOG = {}

def generate_random_id(length=5):
    """Generate a random 5-digit string."""
    characters = string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename.endswith('.txt'):
            continue
        metadata_file = os.path.join(UPLOAD_FOLDER, filename + '.txt')
        uploader = ''
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                uploader = f.read().strip()
        files.append((filename, uploader))
    
    return render_template('index.html', files=files, username=session['username'])

@app.route('/statuses')
def statuses():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    statuses = []
    for status_id, data in STATUS_LOG.items():
        file_path = os.path.join(STATUS_FOLDER, data['filename'])
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read().strip()
                statuses.append((data['user'], content, status_id))
    
    return render_template('statuses.html', statuses=statuses, username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS and check_password_hash(USERS[username]['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS:
            return 'Username already exists'
        USERS[username] = {
            'password': generate_password_hash(password)
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(USERS, f)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        username = session['username']
        
        if check_password_hash(USERS[username]['password'], current_password):
            USERS[username]['password'] = generate_password_hash(new_password)
            with open(USERS_FILE, 'w') as f:
                json.dump(USERS, f)
            return redirect(url_for('index'))
        else:
            return 'Current password is incorrect'
    
    return render_template('change_password.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        with open(file_path + '.txt', 'w') as f:
            f.write(session['username'])
        return redirect(url_for('index'))

@app.route('/upload_status', methods=['POST'])
def upload_status():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    status_content = request.form.get('status')
    if status_content:
        status_id = generate_random_id()
        status_filename = f"{status_id}.txt"
        status_path = os.path.join(STATUS_FOLDER, status_filename)
        
        # Save the status content
        with open(status_path, 'w') as f:
            f.write(status_content)
        
        # Log the status
        STATUS_LOG[status_id] = {'filename': status_filename, 'user': session['username']}
        with open(LOG_FILE, 'w') as f:
            json.dump(STATUS_LOG, f)
        
        return redirect(url_for('statuses'))
    return 'Status content is empty'

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/delete_status/<status_id>', methods=['GET'])
def delete_status(status_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if status_id in STATUS_LOG:
        status_info = STATUS_LOG[status_id]
        file_path = os.path.join(STATUS_FOLDER, status_info['filename'])
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                del STATUS_LOG[status_id]
                with open(LOG_FILE, 'w') as f:
                    json.dump(STATUS_LOG, f)
                return redirect(url_for('statuses'))
            else:
                return 'File not found', 404
        except Exception as e:
            return str(e), 500
    else:
        return 'Status not found', 404

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
