from flask import Flask, render_template, session, redirect
from functools import wraps
import pymongo

app=Flask(__name__)

app.secret_key = 'b\t\x8cPGK\x80)\x1b\xa5W.\xc5\x91{\xa2\xdf'   

# Database
client=pymongo.MongoClient('localhost', 27017)
db=client.user_login_system

#Decorators
def login_required(f):
    @wraps(f)
    def wrap(*arg, **kwargs):
        if 'logged_in' in session:
            return f(*arg, **kwargs)
        else:
            return redirect('/')
    return wrap


# Routes
from user import routes

@app.route('/', methods=['GET'])
def landing():
    return render_template('landing.html')

@app.route('/dashboard/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html', signup_error=None, login_error=None)

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html', signup_error=None, login_error=None)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)


