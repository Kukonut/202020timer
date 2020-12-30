from flask import Flask, render_template, request, session, flash, redirect
from flask_session import Session
from tempfile import mkdtemp
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask import g, request, redirect, url_for

app = Flask(__name__)

# connect to a sqlite3 database called timer.db
conn = sqlite3.connect('timer.db')
# cursor called db, we use it to interact with timer.db
db = conn.cursor()

# make a table called users

# here is some code from CS50 finance distribution code to
# stop responses from caching
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# some more code from CS50 finance distribution code to 
# configure session to use filesystem and not signed cookies.
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# default route
@app.route("/")
def about():
    # todo, about page basic info about the website
    return render_template("about.html")

# from http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
# decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/timer", methods=["GET","POST"])
@login_required
def timer():
    # connect to a sqlite3 database called timer.db
    conn = sqlite3.connect('timer.db')
    # cursor called db, we use it to interact with timer.db
    db = conn.cursor()
    # if it's the user needs to pick what time intervals they want 
    db.execute("SELECT * FROM timerload where id = ?", (session['user_id'],))
    # loadlist is all the loadouts the user has in a list of tuples 
    loadlist = db.fetchall()
    # show them the picking page
    if request.method == "GET":
        return  render_template("picktime.html", loadlist = loadlist)
    # timer that goes 20 minutes then 20 seconds and then repeats
    else:
        # check if the user used one of their preset times.
        # preset is what the user selected in the dropdown list(in picktime.html)
        preset = request.form.get("timeloadout")
        if preset == "Default":
            return render_template("timer.html", startmin = 20, startsec = 0, intmin = 0, intsec = 20)
        else:
            # check what loadout the user picked
            # loop through all the loadouts the user has and check which one matches what user selected in dropdown list in picktime.html
            for i in range(len(loadlist)):
                if loadlist[i][1] == preset:
                    current_load = loadlist[i]
            return render_template("timer.html", startmin = current_load[2], startsec = current_load[3], intmin = current_load[4], intsec = current_load[5], current_load = current_load)
            
            

# route to manage the 20 20 20 timer loadouts users may want to have
@app.route("/manage", methods=["GET", "POST"])
def manage():
    # connect to a sqlite3 database called timer.db
    conn = sqlite3.connect('timer.db')
    # cursor called db, we use it to interact with timer.db
    db = conn.cursor()
    if request.method == "GET":  
        db.execute("SELECT * FROM timerload WHERE id = ?", (session['user_id'],))
        # loadlist are all loadouts the user has as a list of tuples 
        loadlist = db.fetchall()
        return render_template("manage.html", loadlist = loadlist)
    else:
        # make a new loadout
        if request.form.get("manageform") == "make":
            # check if the user already has a loadout with the same name
            loadname = request.form.get("loadname")
            db.execute("SELECT * FROM timerload WHERE id = ? AND loadname = ?", (session['user_id'], loadname))
            check = db.fetchone()
            # check should return none if the user doesn't have a loadout by that name already
            if check == None:
                # update the loadout table to have a new loadout
                db.execute("INSERT INTO timerload (id, loadname, startmin, startsec, intmin, intsec) VALUES (?, ?, ?, ?, ?, ?)",
                (session['user_id'], request.form.get("loadname"), request.form.get("startmin"), request.form.get("startsec"),
                request.form.get("intmin"), request.form.get("intsec")))
                conn.commit()
                flash("Created loadout")
                return redirect("/timer")
            else:
                # give an error 
                flash("You already have a loadout by that name")
                return redirect("/timer")
        # delete a new loadout
        elif request.form.get("manageform") == "delete":
            # check if there is something to delete
            loadname = request.form.get("loadname")
            db.execute("DELETE FROM timerload WHERE loadname = ? AND id = ?", (loadname, session['user_id']))
            conn.commit()
            flash("Deleted loadout")
            return redirect("/timer")
        # update a loadout
        else: 
            loadname = request.form.get("updateload")
            # query for the user's loadout in timerload database and update it with new values
            db.execute("UPDATE timerload SET loadname = ?, startmin = ?, startsec = ?, intmin = ?, intsec = ? WHERE loadname = ? AND id = ?", 
            (request.form.get("nloadname"), request.form.get("nstartmin"), request.form.get("nstartsec"), request.form.get ("nintmin"), request.form.get("nintsec"), 
            loadname, session['user_id']))
            conn.commit()
            flash("Updated loadout")
            return redirect("/timer")

    
# register route so users can register for an account
@app.route("/register", methods=["GET","POST"])
def register():
    # connect to a sqlite3 database called timer.db
    conn = sqlite3.connect('timer.db')
    # cursor called db, we use it to interact with timer.db
    db = conn.cursor()
    # show user the register form
    if request.method == "GET":
        return render_template("register.html")
    else:
        # stores user info into variables
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # makes sure username input wasn't empty
        if not username:
            flash("Please enter a username")
            return redirect("/register")
        elif not password:
            flash("Please enter a password")
            return redirect("/register")
        elif not confirmation:
            flash("Please enter password again")
            return redirect("/register")
        elif password != confirmation:
            flash("Passwords don't match")
            return redirect("/register")

        # now we check if the username already exists in the database
        db.execute("SELECT * FROM users WHERE username = ?", (username,))
        check =  db.fetchone()
        # db.fetchone should return None if the username doesn't already exists
        if check == None:
            # we can add the info into the database
            hashed = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hashed))
            conn.commit()
            # then get the new users user_id and log him in
            db.execute("SELECT id FROM users WHERE username = ?", (username,))
            current = db.fetchone()
            session['user_id'] = current[0]
            flash("Registered")
            return redirect("/")
        # else we give an error that the username already exists
        else:
            flash("Username already exits")
            return redirect("/register")


# login route based heavily on CS50 finance.
@app.route("/login", methods=["GET","POST"])
def login():
    # put this here to solve the "sqlite objects created in thread can only be used in that same threat"
    # connect to a sqlite3 database called timer.db
    conn = sqlite3.connect('timer.db')
    # cursor called db, we use it to interact with timer.db
    db = conn.cursor()
    # forget any user_id
    session.clear()

    # if the user clicks on login button to login
    if request.method == "GET":
        # send them to the login form page to enter credentials
        return render_template("login.html")
    else:
        # log user in
        username = request.form.get("username")
        password = request.form.get("password")
        # makes sure username field isn't empty
        if not username:
            flash("Please enter username")
            return render_template("login.html")
        # makes sure password field isn't empty
        elif not password:
            flash("Please enter password")
            return render_template("login.html")

        # check database for username
        db.execute("SELECT * FROM users WHERE username = ?", (username,))
        # if there isn't a matching username or a matching hash
        check = db.fetchone()
        if check == None or not check_password_hash(check[2],password):
            flash("Invalid username or password")
            return render_template("login.html")
        
        # remember which user logged in
        session['user_id'] = check[0]

        # then redirect to about page
        return render_template("about.html")

# route for logging out
@app.route("/logout")
def logout():
    # forget any user_id
    session.clear()
    # return to about page
    return redirect("/")
