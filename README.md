# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

A simple, fast movie rating system where users search for movies, rate them out of 1-5 stars, and can write a short review. 

## User stories

[Link to user stories issues](https://github.com/swe-students-spring2026/2-web-app-bronze_badgers/issues)

1. As a user, I want to search for a movie and view its ratings.

2. As a user, I want to rate a movie on a scale of 1–5 stars.

3. As a user, I want to filter movies by rating so that I can discover highly rated movies.

4. As a user, I want to edit my rating so that I can update my opinion after rewatching a movie.

5. As a user, I want to create an account and log in so that my ratings are associated with my profile.

6. As a user, I want to view my profile page with all my past ratings so that I can track what I have reviewed.

7. As a user, I want to leave comments or thoughts after watching a movie.

8. As a user, I want to edit or delete my comment if I make a typo or change my mind.

9. As a user, I want to see the average rating and total number of ratings for each movie so that I can quickly judge its overall popularity and quality.

10. As a user, I want to sort movies by newest releases, highest rated, or most reviewed so that I can discover movies more efficiently.


## Steps necessary to run the software

### Step 0

Before running the application, ensure you have the following installed on your local machine:

- **Python 3** 
- **MongoDB connection credentials** (MongoDB URI and database name)

### Step 1: Clone the Repository

Clone this repository to your local machine using Git:

```bash
git clone https://github.com/swe-students-spring2026/2-web-app-bronze_badgers.git
cd 2-web-app-bronze_badgers
```

### Step 2: Set Up a Python Virtual Environment

It is recommended to use a virtual environment to isolate project dependencies. Create and activate a virtual environment:

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

Install all required Python packages using pip:

```bash
pip install -r requirements.txt
```

This will install the following packages:
- `flask` - Web framework
- `pymongo[srv]` - MongoDB driver
- `python-dotenv` - Environment variable management
- `flask-login` - User session management
- `flask-bcrypt` - Password hashing
- `certifi` - SSL certificate bundle

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory of the project. This file contains sensitive credentials and should **not** be committed to version control.

Create the `.env` file with the following variables:

```env
SECRET_KEY=your_secret_key_here
MONGO_URI=your_mongodb_connection_string_here
MONGO_DBNAME=your_database_name_here
```

**Important notes:**
- Replace `your_secret_key_here` with a secure random string (used for Flask session encryption)
- Replace `your_mongodb_connection_string_here` with your MongoDB connection URI (e.g., `mongodb+srv://username:password@cluster.mongodb.net/`)
- Replace `your_database_name_here` with the name of your MongoDB database
- If an `env.example` file exists in the repository, you can use it as a template
- **Do not commit the `.env` file to Git** - it is already excluded via `.gitignore`

### Step 5: Run the Application

Start the Flask development server:

```bash
python app.py
```

Alternatively, you can use:

```bash
flask run
```

The application will start running on `http://127.0.0.1:5000` (or `http://localhost:5000`).

### Step 6: Access the Application

Open your web browser and navigate to:

```
http://127.0.0.1:5000
```

You will be redirected to the login page. If you don't have an account yet, you can register a new account through the registration page.

### Troubleshooting
- **MongoDB connection errors**: Verify your `MONGO_URI` in the `.env` file is correct and that your MongoDB cluster allows connections from your IP address
- **Port already in use**: If port 5000 is already in use, you can specify a different port by setting the `FLASK_RUN_PORT` environment variable or modifying `app.py`
- **Module not found**: Ensure you're running the application from the project root directory where `app.py` is located

## Task boards

[Link to Sprint 1 Task Board](https://github.com/orgs/swe-students-spring2026/projects/16)
