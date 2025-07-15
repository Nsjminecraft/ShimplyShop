# User Login System with Flask and MongoDB

A simple user authentication system built with Flask, MongoDB, and Passlib.  
Users can sign up, log in, and log out. Passwords are securely hashed.

## Features

- User registration (sign up)
- User login and logout
- Password hashing with PBKDF2 (Passlib)
- Session management
- MongoDB for user data storage

## Project Structure

```
commers/
├── run
├── app.py
├── user/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
├── templates/
│   ├── base.html
│   ├── home.html
│   └── dashboard.html
├── static/
│   ├── css/
│   │   ├── normalize.css
│   │   └── styles.css
│   └── js/
│       ├── jquery.js
│       └── scripts.js
└── README.md
```

## Setup Instructions

1. **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd commers
    ```

2. **Create and activate a virtual environment:**
    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

3. **Install dependencies:**
    ```bash
    pip install flask pymongo passlib
    ```

4. **Start MongoDB:**
    - Make sure MongoDB is running on `localhost:27017`.

5. **Run the application:**
    ```bash
    sudo chmod +x run
    ./run
    ```
    or by Flask:
    ```bash
    python app.py
    ```

6. **Open your browser:**
    - Visit [http://localhost:8000] or [http://localhost:5000] (or the port you chose).

## Usage

- **Sign Up:** Fill out the registration form on the home page.
- **Login:** Use your credentials to log in.
- **Dashboard:** View your user info and sign out.

## Notes

- Passwords are hashed using PBKDF2 via Passlib.
- User sessions are managed with Flask's session.
- Make sure to keep your `app.secret_key`