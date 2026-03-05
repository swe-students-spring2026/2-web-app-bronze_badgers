# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
import certifi
from bson.objectid import ObjectId
from datetime import datetime, timezone
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

bcrypt = Bcrypt(app)

client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
db = client[os.getenv("MONGO_DBNAME")]
users_collection = db.users  # we'll store login users here
reviews_collection = db.reviews  # we'll store movie reviews here
notifications_collection = db.notifications # we'll store notifications here



# Home page
@app.route("/")
def home():
    # session.clear()

    if "name" not in session:
        return redirect(url_for("login"))
    movies = list(db.movies.find().sort("year", -1).limit(20))
    return render_template("home.html", movies=movies, query="", sort="recent",
                         selected_genres=[], selected_decades=[],
                         selected_rating="", selected_languages=[])


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
            flash("Invalid name or password", "warning")
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
    
# privacy settings    
@app.route("/privacy-settings")
def privacy_settings():
    if "name" not in session:
        return redirect(url_for("login"))

    user_data = users_collection.find_one({"name": session["name"]})
    is_anonymous = user_data.get("is_anonymous", False)
    private_comment = user_data.get("private_comment", False)

    return render_template(
        "privacy_settings.html",
        user={
            "name": session["name"],
            "is_anonymous": is_anonymous,
            "private_comment": private_comment
        }
    )

@app.route("/api/update-privacy", methods=["POST"])
def update_privacy():
    if "name" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json()
    is_anonymous = data.get("is_anonymous", False)
    private_comment = data.get("private_comment", False)

    users_collection.update_one(
        {"name": session["name"]},
        {"$set": {"is_anonymous": is_anonymous, "private_comment": private_comment}}
    )

    # also updates all reviews of the user on setting change - using denormalisation (better to do it now then when rendering page)
    db.reviews.update_many(
        {"user_name": session["name"]},
        {"$set": {"is_anonymous": is_anonymous, "private_comment": private_comment}}
    )

    return jsonify({"success": True, "message": "Privacy settings updated!"})

# Movie detail page, reviews ratings and comments
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

    # Current user's review (exclude comments)
    user_review = reviews_collection.find_one({
        "user_name": session["name"], "movie_id": oid, "type": {"$ne": "comment"}
    })

    # all reviews with privacy filter
    all_reviews = list(reviews_collection.find({
        "movie_id": oid,
        "type": {"$ne": "comment"},
        "user_name": {"$ne": session["name"]},
        "$or": [
            {"private_comment": {"$ne": True}},
            {"user_name": session["name"]}
        ]
    }).sort("updated_at", -1))

    # all coments with privacy filter
    all_comments = list(reviews_collection.find({
        "movie_id": oid,
        "type": "comment",
        "$or": [
            {"private_comment": {"$ne": True}},
            {"user_name": session["name"]}
        ]
    }).sort("updated_at", 1))

    # group comments by parent id
    comment_map = defaultdict(list)
    for c in all_comments:
        comment_map[c["reply_to"]].append(c)

    star_lookup = {}
    for r in all_reviews:
        star_lookup[r["user_name"]] = r.get("stars")
    if user_review:
        star_lookup[session["name"]] = user_review.get("stars")

    # attach comments to each reviews
    for review in all_reviews:
        review["comments"] = comment_map.get(review["_id"], [])
        if review.get("is_anonymous") and review["user_name"] != session["name"]:
            review["display_name"] = "Anonymous"
        else:
            review["display_name"] = review["user_name"]
        for comment in review["comments"]:
            if comment.get("is_anonymous") and comment["user_name"] != session["name"]:
                comment["display_name"] = "Anonymous"
            else:
                comment["display_name"] = comment["user_name"]
            comment["commenter_stars"] = star_lookup.get(comment["user_name"])

    # Attach comments to user's own review too
    if user_review:
        user_review["comments"] = comment_map.get(user_review["_id"], [])
        for comment in user_review["comments"]:
            if comment.get("is_anonymous") and comment["user_name"] != session["name"]:
                comment["display_name"] = "Anonymous"
            else:
                comment["display_name"] = comment["user_name"]
            comment["commenter_stars"] = star_lookup.get(comment["user_name"])

    return render_template("movie_detail.html", movie=movie, user_review=user_review, reviews=all_reviews)


#Save Review (add and edit)
@app.route("/api/movie/<movie_id>/review", methods=["POST"])
def save_review(movie_id):
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    oid = ObjectId(movie_id)
    data = request.get_json()
    stars = data.get("stars")
    comment = data.get("comment", "").strip()

    user = users_collection.find_one({"name": session["name"]})

    review_doc = {
        "user_name": session["name"],
        "movie_id": oid,
        "type": "review",
        "stars": stars,
        "comment": comment,
        "is_anonymous": user.get("is_anonymous", False),
        "private_comment": user.get("private_comment", False),
        "updated_at": datetime.now(timezone.utc)
    }
    reviews_collection.update_one(
        {"user_name": session["name"], "movie_id": oid, "type": {"$ne": "comment"}},
        {"$set": review_doc},
        upsert=True
    )

    # update average score - only count reviews, not comments
    pipeline = [
        {"$match": {"movie_id": oid, "type": {"$ne": "comment"}}},
        {"$group": {"_id": None, "avg": {"$avg": "$stars"}, "count": {"$sum": 1}}}
    ]
    result = list(reviews_collection.aggregate(pipeline))
    if result:
        db.movies.update_one(
            {"_id": oid},
            {"$set": {
                "avg_rating": round(result[0]["avg"], 1),
                "review_count": result[0]["count"]
            }}
        )
    return jsonify({"success": True, "message": "Review saved successfully"}), 200


# Reply (a comment) to a review
@app.route("/api/movie/<movie_id>/comment", methods=["POST"])
def post_comment(movie_id):
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    oid = ObjectId(movie_id)
    data = request.get_json()
    comment_text = data.get("comment", "").strip()
    reply_to = data.get("reply_to")

    if not comment_text:
        return jsonify({"success": False, "message": "Comment cannot be empty"}), 400

    user = users_collection.find_one({"name": session["name"]})

    comment_doc = {
        "user_name": session["name"],
        "movie_id": oid,
        "type": "comment",
        "stars": None,
        "comment": comment_text,
        "reply_to": ObjectId(reply_to),
        "is_anonymous": user.get("is_anonymous", False),
        "private_comment": user.get("private_comment", False),
        "updated_at": datetime.now(timezone.utc)
    }
    result = reviews_collection.insert_one(comment_doc)

    # Create notification for the review owner (don't notify yourself)
    parent_review = reviews_collection.find_one({"_id": ObjectId(reply_to)})
    if parent_review and parent_review["user_name"] != session["name"]:
        notifications_collection.insert_one({
            "recipient": parent_review["user_name"],
            "sender": session["name"],
            "review_id": ObjectId(reply_to),
            "movie_id": oid,
            "comment_id": result.inserted_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    return jsonify({"success": True, "message": "Comment posted!"}), 200

# Edit a reply / comment
@app.route("/api/comment/<comment_id>/edit", methods=["POST"])
def edit_comment(comment_id):
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json()
    new_text = data.get("comment", "").strip()

    if not new_text:
        return jsonify({"success": False, "message": "Comment cannot be empty"}), 400

    result = reviews_collection.update_one(
        {"_id": ObjectId(comment_id), "user_name": session["name"], "type": "comment"},
        {"$set": {"comment": new_text, "updated_at": datetime.now(timezone.utc)}}
    )

    if result.modified_count > 0:
        return jsonify({"success": True, "message": "Comment updated!"}), 200
    return jsonify({"success": False, "message": "Comment not found or not yours"}), 404

# Delete a comment / reply
@app.route("/api/comment/<comment_id>/delete", methods=["POST"])
def delete_comment(comment_id):
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    result = reviews_collection.delete_one(
        {"_id": ObjectId(comment_id), "user_name": session["name"], "type": "comment"}
    )

    if result.deleted_count > 0:
        return jsonify({"success": True, "message": "Comment deleted!"}), 200
    return jsonify({"success": False, "message": "Comment not found or not yours"}), 404


# Delete a review
## delete all of its reply and recalculate movie average rating
@app.route("/api/review/<review_id>/delete", methods=["POST"])
def delete_review(review_id):
    if "name" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    oid = ObjectId(review_id)
    review = reviews_collection.find_one({"_id": oid, "user_name": session["name"], "type": {"$ne": "comment"}})

    if not review:
        return jsonify({"success": False, "message": "Review not found or not yours"}), 404

    movie_id = review["movie_id"]

    # delete all replies
    reviews_collection.delete_many({"reply_to": oid})
    reviews_collection.delete_one({"_id": oid})

    # recalculate average
    pipeline = [
        {"$match": {"movie_id": movie_id, "type": {"$ne": "comment"}}},
        {"$group": {"_id": None, "avg": {"$avg": "$stars"}, "count": {"$sum": 1}}}
    ]
    result = list(reviews_collection.aggregate(pipeline))
    if result:
        db.movies.update_one(
            {"_id": movie_id},
            {"$set": {"avg_rating": round(result[0]["avg"], 1), "review_count": result[0]["count"]}}
        )
    else:
        # last review deleted
        db.movies.update_one(
            {"_id": movie_id},
            {"$set": {"avg_rating": None, "review_count": 0}}
        )

    return jsonify({"success": True, "message": "Review deleted!"}), 200

# My Reviews
@app.route("/my-reviews")
def my_reviews():
    if "name" not in session:
        return redirect(url_for("login"))
    user_entries = list(reviews_collection.find({"user_name": session["name"]}).sort("updated_at", -1))
    movie_ids = {r["movie_id"] for r in user_entries}
    movies_byid = {m["_id"]: m for m in db.movies.find({"_id": {"$in": list(movie_ids)}})}
    # For replies, look up the parent review to get the original reviewer's name
    reply_to_ids = [r["reply_to"] for r in user_entries if r.get("type") == "comment" and r.get("reply_to")]
    parents_byid = {}
    if reply_to_ids:
        parents_byid = {p["_id"]: p for p in reviews_collection.find({"_id": {"$in": reply_to_ids}})}
    for r in user_entries:
        r["movie"] = movies_byid.get(r["movie_id"])
        if r.get("type") == "comment" and r.get("reply_to"):
            parent = parents_byid.get(r["reply_to"])
            r["parent_user"] = parent["user_name"] if parent else "Unknown"
    return render_template("my_reviews.html", reviews=user_entries)

# Notifications
@app.route("/notifications")
def notifications():
    if "name" not in session:
        return redirect(url_for("login"))
    notifs = list(notifications_collection.find({"recipient": session["name"]}).sort("created_at", -1).limit(50))
    movie_ids = {n["movie_id"] for n in notifs}
    movies_byid = {m["_id"]: m for m in db.movies.find({"_id": {"$in": list(movie_ids)}})}
    for n in notifs:
        n["movie"] = movies_byid.get(n["movie_id"])
    # Mark all as read
    notifications_collection.update_many(
        {"recipient": session["name"], "is_read": False},
        {"$set": {"is_read": True}}
    )
    return render_template("notifications.html", notifications=notifs)

@app.route("/api/notifications/count")
def notifications_count():
    if "name" not in session:
        return jsonify({"count": 0})
    count = notifications_collection.count_documents({"recipient": session["name"], "is_read": False})
    return jsonify({"count": count})

# Search
@app.route("/search")
def search():
    if "name" not in session:
        return redirect(url_for("login"))
    
    query = request.args.get("q", "")
    sort = request.args.get("sort", "recent")
    genres = request.args.getlist("genre")
    decades = request.args.getlist("decade")
    rating = request.args.get("rating", "")
    languages = request.args.getlist("language")
    
    filter_query = {}
    if query:
        filter_query["title"] = {"$regex": query, "$options": "i"}
    if genres:
        filter_query["genres"] = {"$in": genres}
    if languages:
        filter_query["languages"] = {"$in": languages}
    if decades:
        year_conditions = []
        for d in decades:
            if d == "Classic":
                year_conditions.append({"year": {"$lt": 1980}})
            else:
                start = int(d[:4])
                year_conditions.append({"year": {"$gte": start, "$lt": start + 10}})
        if year_conditions:
            filter_query["$or"] = year_conditions
    if rating and rating != "All":
        min_rating = int(rating[0])
        filter_query["avg_rating"] = {"$gte": min_rating}
    
    if sort == "rating":
        sort_key = [("avg_rating", -1)]
    elif sort == "popular":
        sort_key = [("review_count", -1)]
    else:
        sort_key = [("year", -1)]
    
    movies = list(db.movies.find(filter_query).sort(sort_key).limit(20))
    return render_template("home.html", movies=movies, query=query, sort=sort)


if __name__ == "__main__":
    app.run(debug=True)

