# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
import certifi
from bson.objectid import ObjectId
from datetime import datetime, timezone

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

bcrypt = Bcrypt(app)

client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
db = client[os.getenv("MONGO_DBNAME")]
users_collection = db.users  # we'll store login users here
reviews_collection = db.reviews  # we'll store movie reviews here



# Home page
@app.route("/")
def home():
    # session.clear()
    if "name" in session:
        movies = list(db.movies.find())
        return render_template("home.html", movies=movies)


        # return f"Hello, {session['name']}! <a href='/logout'>Logout</a>"

    return redirect(url_for("login"))
    if "name" not in session:
        return redirect(url_for("login"))
    movies = list(db.movies.find().sort("year", -1).limit(20))
    return render_template("home.html", movies=movies, query="", sort="recent")


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
    if "name" not in session:
        flash("Please log in to access settings", "warning")
        return redirect(url_for("login"))
    
    # Fetch user from database
    user = users_collection.find_one({"name": session["name"]})
    if not user:
        flash("User not found", "danger")
        session.pop("name", None)
        return redirect(url_for("login"))
    
    # Prepare user data for template (using single name field)
    user_data = {
        "name": user.get("name", ""),
        "email": user.get("email", "")
    }
    return render_template("settings.html", user=user_data)


# API endpoint to update user name
@app.route("/api/update-name", methods=["POST"])
def update_name():
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    data = request.get_json()
    new_name = data.get("name", "").strip()
    
    if not new_name:
        return jsonify({"success": False, "message": "Name cannot be empty"}), 400
    
    # Check if new name already exists (and it's not the current user)
    existing_user = users_collection.find_one({"name": new_name})
    if existing_user and existing_user.get("name") != session["name"]:
        return jsonify({"success": False, "message": "Name already taken"}), 400
    
    # Update the user's name in database
    result = users_collection.update_one(
        {"name": session["name"]},
        {"$set": {"name": new_name}}
    )
    
    if result.modified_count > 0:
        # Update session with new name
        session["name"] = new_name
        return jsonify({"success": True, "message": "Name updated successfully"}), 200
    else:
        return jsonify({"success": False, "message": "Failed to update name"}), 500


# API endpoint to update user email
@app.route("/api/update-email", methods=["POST"])
def update_email():
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    data = request.get_json()
    new_email = data.get("email", "").strip()
    
    if not new_email:
        return jsonify({"success": False, "message": "Email cannot be empty"}), 400
    
    # Check if new email already exists (and it's not the current user)
    existing_user = users_collection.find_one({"email": new_email})
    if existing_user and existing_user.get("name") != session["name"]:
        return jsonify({"success": False, "message": "Email already registered"}), 400
    
    # Update the user's email in database
    result = users_collection.update_one(
        {"name": session["name"]},
        {"$set": {"email": new_email}}
    )
    
    if result.modified_count > 0:
        return jsonify({"success": True, "message": "Email updated successfully"}), 200
    else:
        return jsonify({"success": False, "message": "Failed to update email"}), 500


# API endpoint to update user password
@app.route("/api/update-password", methods=["POST"])
def update_password():
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    data = request.get_json()
    current_password = data.get("currentPassword", "")
    new_password = data.get("newPassword", "")
    confirm_password = data.get("confirmPassword", "")
    
    if not current_password or not new_password or not confirm_password:
        return jsonify({"success": False, "message": "All password fields are required"}), 400
    
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "New passwords do not match"}), 400
    
    if len(new_password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long"}), 400
    
    # Fetch current user
    user = users_collection.find_one({"name": session["name"]})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    # Verify current password
    if not bcrypt.check_password_hash(user["password"], current_password):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 400
    
    # Hash new password and update
    hashed_pw = bcrypt.generate_password_hash(new_password).decode("utf-8")
    result = users_collection.update_one(
        {"name": session["name"]},
        {"$set": {"password": hashed_pw}}
    )
    
    if result.modified_count > 0:
        return jsonify({"success": True, "message": "Password updated successfully"}), 200
    else:
        return jsonify({"success": False, "message": "Failed to update password"}), 500


# API endpoint to delete user account
@app.route("/api/delete-account", methods=["POST"])
def delete_account():
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    # Delete the user from database
    result = users_collection.delete_one({"name": session["name"]})
    
    if result.deleted_count > 0:
        # Clear the session
        session.pop("name", None)
        return jsonify({"success": True, "message": "Account deleted successfully"}), 200
    else:
        return jsonify({"success": False, "message": "Failed to delete account"}), 500



# Movie detail page (rate and comment)
@app.route("/movie/<movie_id>")
def movie_detail(movie_id):
    if "name" not in session:
        flash("Please log in to view this page", "warning")
        return redirect(url_for("login"))
    try:
        oid = ObjectId(movie_id)
    except:
        flash("Movie not found", "danger")
        return redirect(url_for("home"))
    movie = db.movies.find_one({"_id": oid})
    if not movie:
        flash("Movie not found", "danger")
        return redirect(url_for("home"))
    user_review = reviews_collection.find_one({"user_name": session["name"], "movie_id": oid})
    return render_template("movie_detail.html", movie=movie, user_review=user_review)


#Save Review + Comment
@app.route("/api/movie/<movie_id>/review", methods=["POST"])
def save_review(movie_id):
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    else:
        oid = ObjectId(movie_id)
        data = request.get_json()
        stars = data.get("stars")
        comment = data.get("comment", "").strip()
        review_doc = {
            "user_name": session["name"],
            "movie_id": oid,
            "stars": stars,
            "comment": comment,
            "updated_at": datetime.now(timezone.utc)
        }
        reviews_collection.update_one(
            {"user_name": session["name"], "movie_id": oid},
            {"$set": review_doc},
            upsert=True
        )
        return jsonify({"success": True, "message": "Review saved successfully"}), 200

#Display reviews/comments for a movie
@app.route("/api/movie/<movie_id>", methods=["GET"])
def get_movie_reviews(movie_id):
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    try:
        oid = ObjectId(movie_id)
        reviews_cursor = reviews_collection.find({"movie_id": oid})
        reviews = []
        for r in reviews_cursor:
            reviews.append({
                "user_name": r.get("user_name"),
                "movie_id": str(r["movie_id"]),
                "stars": r.get("stars"),
                "comment": r.get("comment", ""),
                "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None
            })
        return jsonify({"success": True, "reviews": reviews}), 200
    except:
        return jsonify({"success": False, "message": "Invalid movie ID"}), 404

# My Reviews
@app.route("/my-reviews")
def my_reviews():
    if "name" not in session:
        return redirect(url_for("login"))
    reviews = list(reviews_collection.find({"user_name": session["name"]}))
    return render_template("my_reviews.html", reviews=reviews)


# Search

@app.route("/search")
def search():
    if "name" not in session:
        return redirect(url_for("login"))
    
    query = request.args.get("q", "")
    sort = request.args.get("sort", "recent")
    
    # Build filter
    filter_query = {}
    if query:
        filter_query["title"] = {"$regex": query, "$options": "i"}
    
    # Build sort
    if sort == "rating":
        sort_key = [("tomatoes.viewer.rating", -1)]
    elif sort == "popular":
        sort_key = [("tomatoes.viewer.numReviews", -1)]
    else:  # recent
        sort_key = [("year", -1)]
    
    movies = list(db.movies.find(filter_query).sort(sort_key).limit(20))
    return render_template("home.html", movies=movies, query=query, sort=sort)


if __name__ == "__main__":
    app.run(debug=True)

