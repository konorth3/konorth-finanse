# -*- coding: utf-8 -*-
"""
Created on Tue Jul  9 19:53:48 2019

@author: Knorth
"""
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


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if symbol == "":
            return "Вкажіть символ акції"
        if lookup(symbol) is None:
            return "Такого символа неіснує"
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return "Введіть ціле, додатне число"
        if not shares > 0:
            return "Введіть ціле, додатне число"
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()            
            cursor.execute(f"SELECT cash FROM users WHERE id={session['user_id']}")
            
            cash = cursor.fetchall()[0][0]
            action = lookup(symbol)
            left_cash = cash - action["price"] * shares
            
            if left_cash < 0:
                return 'У вас недостатньо коштів для здійснення операції'
            
            cursor.execute(f"INSERT INTO '{session['user_id']}'(symbol, shares, price) VALUES('{action['symbol']}', {shares}, {action['price']})")     
            cursor.execute(f"UPDATE users SET cash = {left_cash} WHERE id = {session['user_id']}")
            db.commit()
            return redirect("/")
    return render_template("buy.html")

    
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        return render_template("quote.html", symbol = lookup(request.form.get("symbol")))
    return render_template("quote.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        
        symbol = request.form.get("symbol")
        if symbol == "":
            return "Вкажіть символ акції"
        
        action = lookup(symbol)
        if action is None:
            return "Такого символа неіснує"
        
        shares = request.form.get("shares")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return "Введіть ціле, додатне число"
        if shares < 0:
            return "Введіть ціле, додатне число"
        
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            
            cursor.execute(f"SELECT SUM(shares) FROM '{session['user_id']}' WHERE symbol=:symbol", {'symbol':action["symbol"]})
            left_shares = cursor.fetchall()[0][0] - shares
            if left_shares < 0:
                return 'У вас недостатньо акцій для здійснення операції'
            cursor.execute(f"SELECT cash FROM users WHERE id={session['user_id']}")
            cash = cursor.fetchall()[0][0]
            cursor.execute(f"UPDATE users SET cash = {cash + action['price'] * shares} WHERE id = {session['user_id']}")
            cursor.execute(f"INSERT INTO '{session['user_id']}'(symbol, shares, price) VALUES('{action['symbol']}', {-shares}, {action['price']})")    
            db.commit()
            return redirect("/")
    return render_template("sell.html")


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
            return "Вкажіть ім'я"
        elif not request.form.get("password"):
            return "Вкажіть пароль"
        elif not request.form.get("password") == request.form.get("confirmation") :
            return "Паролі не співпадають"
        
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            cursor.execute("SELECT id FROM users WHERE name =:name", {"name":request.form.get("name")})
            if cursor.fetchall():
                return "Ім'я вже заняте"
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


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    
    if request.method == "POST":
        if not request.form.get("name"):
            return "Вкажіть ім'я"
        elif not request.form.get("password"):
            return "Вкажіть пароль"
        with sqlite3.connect("finance.db") as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM users WHERE name =:name", {"name":request.form.get("name")})
            rows = cursor.fetchall()
            if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
                return "Вказані ім'я і/або пароль хибні"
            session["user_id"] = rows[0][0]
        return redirect("/")
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


app.run(host = "92.253.248.251", port = 1000)
