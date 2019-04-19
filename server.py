from flask import Flask, render_template, redirect, flash, session, request
from mysqlconnection import connectToMySQL
from flask_bcrypt import Bcrypt
import re
app = Flask(__name__)
app.secret_key = 'shh'
bcrypt = Bcrypt(app)


EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$') 

############################### functions ###############################

# -------------------------------------------------------------- exists_in_database()
def exists_in_database(value, column):
    mysql = connectToMySQL("quotes_dash")

    if column == "password":
        query = "SELECT password FROM users WHERE email = %(v)s;"
        data = { "v": value }
        passLib = mysql.query_db(query, data)
        print("##################################################")
        print(passLib)
        pw = passLib[0]['password']
        return pw
    elif column == "email":
        query = "SELECT * FROM users WHERE email = %(val)s;"
        data = {
            "val": value
        }
        dataLib = mysql.query_db(query, data)
        
        if dataLib == False or len(dataLib) == 0:
            print("empty")
            return False # value does not exist in db
        else:
            return True # value does exist in db
    else:
        flash("An error has occured", 'must_login')
        return redirect('/')

# ---------------------------------------------------------------- hash_pass()
def hash_pass(password):
    password = bcrypt.generate_password_hash(password)
    return password

# ---------------------------------------------------------------- store_user()
def store_user(obj, user_pass):
    mysql = connectToMySQL("quotes_dash")
    query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES(%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW(), NOW());"
    data = {
        "fn": obj['fname'],
        "ln": obj['lname'],
        "em": obj['email'],
        "pw": user_pass
    }
    success = mysql.query_db(query, data)
    if success > 0:
        return True
    else:
        return False

# ---------------------------------------------------------------- get_user()
def get_user(value):
    mysql = connectToMySQL("quotes_dash")
    query = "SELECT * FROM users WHERE email = %(v)s;"
    data = { "v": value }
    user = mysql.query_db(query, data)
    return user

############################### log and reg #################################

# ---------------------------------------------------------------- /
@app.route('/')
def home():
    if not 'user' in session:
        session['user'] = ""

    if not 'quote' in session:
        session['quote'] = ""

    if not 'author' in session:
        session['author'] = ""

    if not 'likes' in session:
        session['likes'] = False

    return render_template("index.html")

# ---------------------------------------------------------------- /validate_reg
@app.route('/validate_reg', methods=['POST'])
def validate_reg():
    is_valid = True # Error toggle
    
    if len(request.form['fname']) < 2 or not str.isalpha(request.form['fname']):
        flash("First name must contain at least two letters and contain only letters", 'fname')
        is_valid = False

    if len(request.form['lname']) < 2 or not str.isalpha(request.form['lname']):
        flash("Last name must contain at least two letters and contain only letters", 'lname')
        is_valid = False

    if not EMAIL_REGEX.match(request.form['email']) or (exists_in_database(request.form['email'], "email")): # or does exist in database
        flash("Invalid email address", 'email')
        is_valid = False

    if len(request.form['pass']) < 8 or len(request.form['pass']) > 15:
        flash("Password must contain a number, a capital letter, and be between 8-15 characters", 'pass')
        is_valid = False

    if len(request.form['pass_confirm']) < 8 or request.form['pass_confirm'] != request.form['pass']:
        flash("Passwords must match", 'pass_confirm')
        is_valid = False

    if is_valid == False:
        return redirect('/')
    else:
        user_pass = hash_pass(request.form['pass'])
        success = store_user(request.form, user_pass)
        if success:
            session['user'] = get_user(request.form['email'])
            flash("Your account has successfully been registered!", 'success')
            return redirect('/home')
        else:
            flash("An error has occurred", 'must_login')
            return redirect('/')

# ---------------------------------------------------------------- /validate_log
@app.route('/validate_log', methods=['POST'])
def validate_log():
    is_valid = True

    if exists_in_database(request.form['email'], 'email') == False:
        flash("Invalid email", 'invalid_email')
        is_valid = False
        return redirect('/')
        

    if not bcrypt.check_password_hash(exists_in_database(request.form['email'], "password"), request.form['pass']):
        flash("Invalid password", 'invalid_pass')
        is_valid = False

    if not is_valid:
        return redirect('/')
    else:
        session['user'] = get_user(request.form['email'])
        return redirect('/home')

# ---------------------------------------------------------------- /home
@app.route('/home')
def success():
    if session['user'] != "":
        mysql = connectToMySQL("quotes_dash")
        query = "SELECT quotes.id, quote, author, first_name, last_name, uploaded_by FROM quotes JOIN users ON quotes.uploaded_by = users.id ORDER BY quotes.updated_at DESC;"
        results = mysql.query_db(query)

        mysql = connectToMySQL("quotes_dash")
        query = "SELECT COUNT(user_id), quote_id FROM likes GROUP BY quote_id;"
        results2 = mysql.query_db(query)


        return render_template("home.html", name = session['user'][0]['first_name'],all_quotes = results, all_likes = results2)
    else:
        flash("User must be logged in to view home page", 'must_login')
        return redirect('/')

# ---------------------------------------------------------------- /home
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

############################ Quotes Dash ###########################

# ---------------------------------------------------------------- /validate_quote
@app.route('/validate_quote', methods=['POST'])
def validate_quote():
    is_valid = True

    if len(request.form['author']) <= 3 or len(request.form['author']) > 45:
        is_valid = False
        flash("Author must be more than 3 characters and less than 45", 'author')

    if len(request.form['quote']) <= 10:
        is_valid = False
        flash("Quote must be more than 10 characters", 'quote')
    
    if not is_valid:
        return redirect('/home')
    else:
        session['author'] = str(request.form['author'])
        session['quote'] = str(request.form['quote'])
        return redirect('/add_quote')

# ---------------------------------------------------------------- /add_quote
@app.route('/add_quote')
def add_quote():
    mysql = connectToMySQL("quotes_dash")
    query = "INSERT INTO quotes (quote, author, uploaded_by, created_at, updated_at) VALUES(%(q)s, %(a)s, %(id)s, NOW(), NOW());"
    data = {
        "q": session['quote'],
        "a": session['author'],
        "id": session['user'][0]['id'],
    }
    mysql.query_db(query, data)
    flash("Your quote has successfully been added!", 'success')
    return redirect('/home')

# -------------------------------------------------------------- /delete_quote/<id>
@app.route('/delete_quote/<id>')
def delete_quote(id):
    print("Made it to delete quote!")
    mysql = connectToMySQL("quotes_dash")
    query = "DELETE FROM quotes WHERE id = %(id)s;"
    data = { "id": id }
    mysql.query_db(query, data)
    return redirect('/home')

# -------------------------------------------------------------- /show/edit_user
@app.route('/show/edit_user')
def show_edit_user():
    mysql = connectToMySQL("quotes_dash")
    query="SELECT first_name, last_name, email FROM users WHERE id = %(id)s;"
    data = { "id": session['user'][0]['id'] }
    result = mysql.query_db(query, data)
    print(result)
    return render_template("edit_user.html", user_info = result)

# ---------------------------------------------------------- /show/user_uploads/<id>
@app.route('/show/user_uploads/<id>')
def show_user_uploads(id):
    mysql = connectToMySQL("quotes_dash")
    query="SELECT * FROM quotes JOIN users ON uploaded_by = users.id WHERE uploaded_by = %(id)s;"
    data = { "id": id }
    results = mysql.query_db(query, data)
    return render_template("user_uploads.html", all_quotes = results)

# -------------------------------------------------------------- /update_user
@app.route('/update_user', methods=['POST'])
def update_user():
    is_valid = True

    if len(request.form['fname']) <= 0:
        is_valid = False
        flash("First Name field cannot be empty", 'fname')
    
    if len(request.form['lname']) <= 0:
        is_valid = False
        flash("Last Name field cannot be empty", 'lname')

    if not EMAIL_REGEX.match(request.form['email']) or (exists_in_database(request.form['email'], "email")): # or does exist in database
        if not request.form['email'] == session['user'][0]['email']:
            is_valid = False
            flash("Invalid email address", 'email')

    if not is_valid:
        return redirect('/show/edit_user')
    else: 
        mysql = connectToMySQL("quotes_dash")
        query = "UPDATE users SET first_name = %(fn)s, last_name = %(ln)s, email = %(e)s WHERE id = %(id)s;"
        data = {
            "fn": request.form['fname'],
            "ln": request.form['lname'],
            "e": request.form['email'],
            "id": session['user'][0]['id'],
        }
        mysql.query_db(query, data)
        flash("Your Account has been successfully updated!", 'success')
        return redirect('/show/edit_user')

# -------------------------------------------------------------- /like
@app.route('/like/<id>')
def like(id):
    mysql = connectToMySQL("quotes_dash")
    query = "SELECT * FROM likes WHERE user_id = %(uid)s AND quote_id = %(qid)s;"
    data = {
        "uid": session['user'][0]['id'],
        "qid": id
    }
    results = mysql.query_db(query, data)
    print(results)
    if results == ():   
        mysql = connectToMySQL("quotes_dash")
        query = "INSERT INTO likes (user_id, quote_id) VALUES (%(uid)s, %(qid)s);"
        mysql.query_db(query, data)
    else:
        flash("You cannot like a quote more than once!", 'success')

    return redirect('/home')

    
################################ end ###############################
if __name__=="__main__":
    app.run(debug=True)