import os
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

# client = MongoClient(os.getenv("MONGO_URI"))
# db = client[os.getenv("MONGO_DBNAME")]
db = None  # Set to None for frontend-only development


@app.route("/")
def home():
    if db:
        movies = list(db.movies.find())
    else:
        # Mock data for frontend development
        movies = []
    return render_template("home.html", movies=movies)


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
