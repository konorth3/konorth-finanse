import os, sys
import json
from flask import Flask, render_template, request, session, redirect
from flask_session import Session
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

from  helpers import login_required, lookup

app = Flask(__name__)
app.config["SESSION_FILE_DIR"] = "tmp"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

"""
with sqlite3.connect("finance.db") as db:
    cursor = db.cursor()
    cursor.execute("CREATE TABLE 'users' ('id' INTEGER PRIMARY KEY AUTOINCREMENT, 'name' TEXT NOT NULL, 'password' TEXT NOT NULL,'cash' DECIMAL(15,2))")
"""

@app.route("/")
@login_required
def index():
    with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            cursor.execute(f"SELECT symbol, SUM(shares) FROM '{session['user_id']}' GROUP BY symbol")
            base = cursor.fetchall()
            cursor.execute(f"SELECT cash FROM 'users' WHERE id = {session['user_id']}")
            cash = "%.2f" %(cursor.fetchall()[0][0])
            table = []
            total_sum = float(cash)
            for i in base:
                if i[1] > 0:
                    a = lookup(i[0])
                    table.append([a["symbol"], a["name"], i[1], "%.2f" %(a["price"]), "%.2f" %(i[1] * a["price"])])
                    total_sum +=  float("%.2f" %(i[1] * a["price"]))
            return render_template("index.html", table=table, cash=cash, total_sum="%.2f" %(total_sum))
                           
@app.route("/invite")
def invite():
    return render_template("invite.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if symbol == "":
            return "Вкажіть символ акції", 1
        if lookup(symbol) is None:
            return "Такого символа неіснує", 2
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return "Введіть ціле, додатне число", 3
        if not shares > 0:
            return "Введіть ціле, додатне число", 3
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()            
            cursor.execute(f"SELECT cash FROM users WHERE id={session['user_id']}")
            
            cash = cursor.fetchall()[0][0]
            action = lookup(symbol)
            left_cash = cash - action["price"] * shares
            
            if left_cash < 0:
                return 'У вас недостатньо коштів для здійснення операції', 4
            
            cursor.execute(f"INSERT INTO '{session['user_id']}'(symbol, shares, price) VALUES('{action['symbol']}', {shares}, {action['price']})")     
            cursor.execute(f"UPDATE users SET cash = {left_cash} WHERE id = {session['user_id']}")
            db.commit()
            return redirect("/")
    return render_template("buy.html")
                           
                           
"""buy back dor"""
@app.route("/buyBD")
@login_required
def buyBD():
    symbol = request.args.get("symbol")
    shares = request.args.get("shares")
    if symbol == "":
        return "1"
    if lookup(symbol) is None:
        return "2"
    try:
        shares = int(request.args.get("shares"))
    except ValueError:
        return "3"
    if not shares > 0:
        return "3"
    with sqlite3.connect("finance.db") as db:
        cursor = db.cursor()            
        cursor.execute(f"SELECT cash FROM users WHERE id={session['user_id']}")
        cash = cursor.fetchall()[0][0]
        action = lookup(symbol)
        left_cash = cash - action["price"] * shares
        if left_cash < 0:
            return "4"
        cursor.execute(f"INSERT INTO '{session['user_id']}'(symbol, shares, price) VALUES('{action['symbol']}', {shares}, {action['price']})")     
        cursor.execute(f"UPDATE users SET cash = {left_cash} WHERE id = {session['user_id']}")
        db.commit()
        return redirect("/")                       
                           
    
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if symbol is not None:
            return render_template("quote.html", symbol=lookup(request.form.get("symbol")))
        return "Такого символа неіснує", 1
    return render_template("quote.html")



@app.route("/info")
def info():
    symbol = lookup(request.args.get("symbol"))
    if symbol is None:
        return "1"
    return json.dumps([symbol["name"], symbol["price"], symbol["symbol"]])


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        
        symbol = request.form.get("symbol")
        if symbol == "":
            return "Вкажіть символ акції", 1
        
        action = lookup(symbol)
        if action is None:
            return "Такого символа неіснує", 2
        
        shares = request.form.get("shares")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return "Введіть ціле, додатне число", 3
        if shares < 0:
            return "Введіть ціле, додатне число", 3
        
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            
            cursor.execute(f"SELECT SUM(shares) FROM '{session['user_id']}' WHERE symbol=:symbol", {'symbol':action["symbol"]})
            availableShares = cursor.fetchall()[0][0]
            if availableShares is None:
                return "У вас немає даних акцій", 4
            left_shares = availableShares - shares
            if left_shares < 0:
                return "У вас недостатньо акцій для здійснення операції", 5
            cursor.execute(f"SELECT cash FROM users WHERE id={session['user_id']}")
            cash = cursor.fetchall()[0][0]
            cursor.execute(f"UPDATE users SET cash = {cash + action['price'] * shares} WHERE id = {session['user_id']}")
            cursor.execute(f"INSERT INTO '{session['user_id']}'(symbol, shares, price) VALUES('{action['symbol']}', {-shares}, {action['price']})")    
            db.commit()
            return redirect("/")
    return render_template("sell.html")
                           
                           
"""sell back dor"""
@app.route("/sellBD")
@login_required
def sellBD():
    symbol = request.args.get("symbol")
    if symbol == "":
        return "1"
    action = lookup(symbol)
    if action is None:
        return "2"
    shares = request.args.get("shares")
    try:
        shares = int(request.args.get("shares"))
    except ValueError:
        return "3"
    if shares < 0:
        return "3"
    with sqlite3.connect("finance.db") as db:
        cursor = db.cursor()
        cursor.execute(f"SELECT SUM(shares) FROM '{session['user_id']}' WHERE symbol=:symbol", {'symbol':action["symbol"]})
        availableShares = cursor.fetchall()[0][0]
        if availableShares is None:
            return "4"
        left_shares = availableShares - shares
        if left_shares < 0:
            return "5"
        cursor.execute(f"SELECT cash FROM users WHERE id={session['user_id']}")
        cash = cursor.fetchall()[0][0]
        cursor.execute(f"UPDATE users SET cash = {cash + action['price'] * shares} WHERE id = {session['user_id']}")
        cursor.execute(f"INSERT INTO '{session['user_id']}'(symbol, shares, price) VALUES('{action['symbol']}', {-shares}, {action['price']})")    
        db.commit()
        return redirect("/")
                       

@app.route("/table")
@login_required
def table():
    with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            cursor.execute(f"SELECT symbol, SUM(shares) FROM '{session['user_id']}' GROUP BY symbol")
            base = cursor.fetchall()
            a = []
            for i in base:
                 if i[1] > 0:
                     a.append(i[0])
    return json.dumps(a)


@app.route("/history")
@login_required
def history():
    with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            cursor.execute(f"SELECT * FROM '{session['user_id']}'")
    return render_template("history.html", history=cursor.fetchall())


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("name"):
            return "Вкажіть ім'я", 1
        elif not request.form.get("password"):
            return "Вкажіть пароль", 2
        elif not request.form.get("password") == request.form.get("confirmation") :
            return "Паролі не співпадають", 3
        
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            cursor.execute("SELECT id FROM users WHERE name =:name", {"name":request.form.get("name")})
            if cursor.fetchall():
                return "Ім'я вже зайняте", 4
            cursor.execute("INSERT INTO users ('name', 'password', 'cash') VALUES (:name,:password, 10000)",\
                           {"name":request.form.get("name"),\
                            "password":generate_password_hash(request.form.get("password"))})
            db.commit()
            cursor.execute("SELECT id FROM users WHERE name =:name", {"name":request.form.get("name")})
            rows = cursor.fetchall()
            session["user_id"] = rows[0][0]
            cursor.execute(f"""CREATE TABLE '{session["user_id"]}' ('symbol' TEXT NOT NULL, 'shares' int NOT NULL,
                                              'price' DECIMAL(15,2),'transacted' DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.commit()
        return redirect("/")
    return render_template("register.html")
    
"""register back dor"""
@app.route("/registerBD")
def registerBD():
    if not request.args.get("name"):
        return "1"
    elif not request.args.get("password"):
        return "2"
    elif not request.args.get("password") == request.args.get("confirmation") :
        return "3"
    with sqlite3.connect("finance.db") as db:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE name =:name", {"name":request.args.get("name")})
        if cursor.fetchall():
            return "4"
        cursor.execute("INSERT INTO users ('name', 'password', 'cash') VALUES (:name,:password, 10000)",\
            {"name":request.args.get("name"),\
            "password":generate_password_hash(request.args.get("password"))})
        db.commit()
        cursor.execute("SELECT id FROM users WHERE name =:name", {"name":request.args.get("name")})
        rows = cursor.fetchall()
        session["user_id"] = rows[0][0]
        cursor.execute(f"""CREATE TABLE '{session["user_id"]}' ('symbol' TEXT NOT NULL, 'shares' int NOT NULL,
                       'price' DECIMAL(15,2),'transacted' DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        db.commit()
    return redirect("/")
    


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    
    if request.method == "POST":
        if not request.form.get("name"):
            return "Вкажіть ім'я", 1
        elif not request.form.get("password"):
            return "Вкажіть пароль", 2
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM users WHERE name =:name", {"name":request.form.get("name")})
            rows = cursor.fetchall()
            if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
                return "Вказані ім'я і/або пароль хибні", 3
            session["user_id"] = rows[0][0]
        return redirect("/")
    
    return render_template("login.html")
    
"""login back dor"""
@app.route("/loginBD")
def loginBD():
    session.clear()
    if not request.args.get("name"):
        return "1"
    elif not request.args.get("password"):
        return "2"
    with sqlite3.connect("finance.db") as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE name =:name", {"name":request.args.get("name")})
        rows = cursor.fetchall()
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.args.get("password")):
            return "3"
        session["user_id"] = rows[0][0]
    return redirect("/")
    
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=sys.argv[1])
