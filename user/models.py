from flask import Flask, render_template, jsonify, request, session, redirect
from passlib.hash import pbkdf2_sha256
import uuid
from app import db

class User:

    def start_session(self, user):
        del user['password']
        session['logged_in'] = True
        session['user'] = user
        return jsonify(user), 200


    def signup(self, server_render=False):
        print(request.form)

        #Create the user object
        user={
            "_id":uuid.uuid4().hex,
            "name":request.form.get('name'),
            "email":request.form.get('email'),
            "password":request.form.get('password')
        }

        #encrypt the password
        user['password'] = pbkdf2_sha256.encrypt(user['password'])

        #check if the user already exists
        if db.users.find_one({"email": user['email']}):
            if server_render:
                return {"error": "Email address already exists"}
            return jsonify({"error": "Email address already exists"}), 400

        if db.users.insert_one(user):
            self.start_session(user)
            return None if server_render else (jsonify(user), 200)
    
        if server_render:
            return {"error": "Signup Failed"}
        return jsonify({"error": "Signup Failed"}), 400
    
    def signout(self):
        session.clear()
        return redirect('/')
    

    def login(self, server_render=False):
        user= db.users.find_one({
            "email": request.form.get('email')
        })
        password = request.form.get('password')
        if user and password is not None and pbkdf2_sha256.verify(password, user['password']):
            self.start_session(user)
            return None if server_render else (jsonify(user), 200)
        if server_render:
            return {"error": "Invalid email or password"}
        return jsonify({"error": "Invalid email or password"}), 401