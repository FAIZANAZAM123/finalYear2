import os
from flask import Flask, request, session, render_template, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_pymongo import PyMongo
from flask_session import Session
from functools import wraps
from keras.models import load_model
from PIL import Image
import numpy as np
import cv2

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['SECRET_KEY'] = 'dc25735aee9b7509ceff473e929b08e49f6bdf85'
app.config["MONGO_URI"] = "mongodb+srv://faizanazam6980:gX6Fv5ckklb6AqWk@cluster0.tjketqg.mongodb.net/FypDatabase?retryWrites=true&w=majority&appName=Cluster0"

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

mongodb_client = PyMongo(app)
db = mongodb_client.db

# Load your model using an absolute path
model_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Save-models', 'final.h5')
model = load_model(model_path)
classes = ['NCD', 'Cocci', 'SALMO', 'white_diarrhea', 'HEALTHY']

def preprocess_image(image_path):
    img = cv2.imread(image_path)
    img_resized = cv2.resize(img, (150, 150))
    img_normalized = img_resized / 255.0
    img_expanded = np.expand_dims(img_normalized, axis=0)
    return img_expanded

def predict_image(image_path):
    image = preprocess_image(image_path)
    predictions = model.predict(image)
    predicted_class = np.argmax(predictions, axis=1)[0]
    return classes[predicted_class]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            prediction = predict_image(file_path)
            return redirect(url_for('result', prediction=prediction, file_name=file.filename))
    return 'Failed to upload file'

@app.route('/result')
def result():
    prediction = request.args.get('prediction')
    file_name = request.args.get('file_name')
    return render_template('result.html', prediction=prediction, file_name=file_name)
    
@app.route('/home')
@login_required
def index():
    return render_template('index.html')

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/research')
@login_required
def research():
    return render_template('Research.html')

@app.route('/contact')
@login_required
def contact():
    return render_template('contact.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/')
def signup():
    return render_template('signup.html')

@app.route('/signupuser', methods=['POST'])
def signupuser():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    cnic = data.get('cnic')
    password = data.get('password')

    if name and email and phone and cnic and password:
        if db.users.find_one({"email": email}):
            return jsonify({"error": "Email already exists!"}), 400
        if db.users.find_one({"phone": phone}):
            return jsonify({"error": "Phone number already exists!"}), 400
        if db.users.find_one({"cnic": cnic}):
            return jsonify({"error": "CNIC already exists!"}), 400

        hashed_password = generate_password_hash(password)

        user = {
            "name": name,
            "email": email,
            "phone": phone,
            "cnic": cnic,
            "password": hashed_password
        }

        db.users.insert_one(user)

        return jsonify({"message": "User registered successfully!"}), 201
    else:
        return jsonify({"error": "Missing fields!"}), 400

@app.route('/loginuser', methods=['POST'])
def loginuser():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if email and password:
        user = db.users.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            return jsonify({"message": "Login successful!"}), 200
        else:
            return jsonify({"error": "Invalid email or password!"}), 401
    else:
        return jsonify({"error": "Missing fields!"}), 400

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    email = data.get('email')

    if email:
        if db.subscribe.find_one({"email": email}):
            return jsonify({"error": "Email already exists!"}), 400

        user = {
            "email": email,
        }

        db.subscribe.insert_one(user)

        return jsonify({"message": "User subscribed successfully!"}), 201
    else:
        return jsonify({"error": "Missing fields!"}), 400

@app.route('/connection')
def connection():
    return "MongoDB connection established successfully."

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
