# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
import certifi

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

bcrypt = Bcrypt(app)

client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
db = client[os.getenv("MONGO_DBNAME")]
users_collection = db.users  # we'll store login users here

# @app.route("/")
# def home():
#     movies = list(db.movies.find())
#     return render_template("home.html", movies=movies)

# Home page
@app.route("/")
def home():
    if "name" in session:
        movies = list(db.movies.find())
        return render_template("home.html", movies=movies)

        # return f"Hello, {session['name']}! <a href='/logout'>Logout</a>"
    return redirect(url_for("login"))


# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("username")   # from the form
        password = request.form.get("password")

        # look up by "name" in MongoDB
        user = users_collection.find_one({"name": name})
        if user and bcrypt.check_password_hash(user["password"], password):
            session["name"] = name  # store in session
            return redirect(url_for("home"))
        else:
            flash("Invalid name or password", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

# Registration 
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if name or email already exists
        if users_collection.find_one({"name": name}):
            flash("Name already exists", "warning")
            return redirect(url_for("register"))
        if users_collection.find_one({"email": email}):
            flash("Email already registered", "warning")
            return redirect(url_for("register"))

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_pw
        })

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# Logout
@app.route("/logout")
def logout():
    session.pop("name", None)
    flash("You have been logged out", "info")
    return redirect(url_for("login"))


@app.route("/settings")
def settings():
    mock_user = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com"
    }
    return render_template("settings.html", user=mock_user)


if __name__ == "__main__":
    app.run(debug=True)
