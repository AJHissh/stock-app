import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, success

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
# if not os.environ.get("API_KEY"):
#     raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():

    try:
        currentuser = session["user_id"]
        data = db.execute("SELECT symbol, SUM(shares), price FROM portfolio WHERE user = ? GROUP BY symbol", currentuser)
        cash = db.execute("SELECT cash FROM users WHERE id = ?", currentuser)
        purchases = []
        test = []
        for dat in data:
            stock = lookup(dat["symbol"])
            price = (stock["price"])
            shares = dat["SUM(shares)"]
            total = round(price * shares, 2)
            purchases.append({"symbol": stock["symbol"], "price": stock["price"], "name": stock["name"], "shares": shares, "Total": total})
            test.append(total)
    except:
        return render_template("index.html")

    total = sum(test)
    users = db.execute("SELECT username FROM users WHERE id = ?", currentuser)
    user = users[0]["username"].upper()

    return render_template("index.html", purchases=purchases, cash=cash, total=total, user=user)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "POST":

            stocksymbol = request.form.get("symbol").upper()
            stockdata = lookup(stocksymbol)
            if stockdata is not None:
                price = float(stockdata["price"])
                currentuser = session["user_id"]
                currentcash = db.execute("SELECT cash FROM users WHERE id = ?", currentuser)
                currentcash = currentcash[0]["cash"]
                sharequantity = int(request.form.get("shares"))
                buyshares = sharequantity * price
                currentshrs = db.execute("SELECT SUM(shares) FROM portfolio WHERE user = ? AND symbol = ?", currentuser, stocksymbol)
            else:
                return apology("Please enter a valid stock symbol!")
            try:
                if currentcash > buyshares:
                    currentshrs = int(currentshrs[0]["SUM(shares)"])
                    newshares = currentshrs + sharequantity
                    db.execute("DELETE FROM portfolio WHERE symbol = ? AND user = ?", stocksymbol, currentuser)
                    currentcash = currentcash - buyshares
                    db.execute("UPDATE users SET cash = ? WHERE id = ?", currentcash, currentuser)
                    db.execute("INSERT OR REPLACE INTO portfolio(user, symbol, shares, price ) VALUES(?, ?, ?, ?)", currentuser, stocksymbol, newshares, price)
                    db.execute("INSERT INTO history(user, symbol, shares, price ) VALUES(?, ?, ?, ?)", currentuser, stocksymbol, sharequantity, price)
                    return render_template("bought.html", buyshares=buyshares, stocksymbol=stocksymbol, stockdata=stockdata["name"])
            except:
                currentcash = currentcash - buyshares
                db.execute("UPDATE users SET cash = ? WHERE id = ?", currentcash, currentuser)
                db.execute("INSERT OR REPLACE INTO portfolio(user, symbol, shares, price ) VALUES(?, ?, ?, ?)", currentuser, stocksymbol, sharequantity, price)
                db.execute("INSERT INTO history(user, symbol, shares, price ) VALUES(?, ?, ?, ?)", currentuser, stocksymbol, sharequantity, price)
                return render_template("bought.html", buyshares=buyshares, stocksymbol=stocksymbol, stockdata=stockdata["name"])
            else:
                return apology("Not enough cash to purchase stock")

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    currentuser = session["user_id"]
    data = db.execute("SELECT symbol, shares, price FROM history WHERE user = ?", currentuser)

    return render_template("history.html", data=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == "POST":
        try:
            stocksymbol = request.form.get("symbol")
            stockdata = lookup(stocksymbol)
            return render_template("quotequery.html", name=stockdata["name"], symbol=stockdata["symbol"], price=usd(stockdata["price"]))
        except:
            return apology("Invalid Stock Symbol")

    return render_template("quote.html")




@app.route("/register", methods=["GET", "POST"])
def register():

    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)


        username = request.form.get("username")
        userpass = request.form.get("password")
        confirmpass = request.form.get("confirmation")
        if confirmpass != userpass:
            return apology("password mismatch", 400)

        userpass = generate_password_hash(userpass)

        try:
            db.execute("INSERT INTO users(username, hash) VALUES(?, ?)", username, userpass)
            return success("Successfully Registered!")
        except:
            return apology("Username and password already taken", 400)


    return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    user = session["user_id"]
    sym = db.execute("SELECT DISTINCT symbol FROM portfolio WHERE user = ? ORDER BY symbol", user)

    if request.method == "POST":

            currentuser = session["user_id"]
            symbol = request.form.get("symbol").upper()
            shares = int(request.form.get("shares"))
            symb = lookup(symbol)
            price = symb["price"]
            total = price * shares

            portfolio = db.execute("SELECT SUM(shares) FROM portfolio WHERE user = ? AND symbol = ?", currentuser, symbol)
            cash = db.execute("SELECT cash FROM users WHERE id = ?", currentuser)

            csh = int(cash[0]["cash"])
            sold = csh + total
            row = int(portfolio[0]["SUM(shares)"])

            updshares = row - shares
            if updshares >= 0:
                db.execute("UPDATE portfolio SET shares = ? WHERE symbol = ? AND user = ?", updshares, symbol, currentuser)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", sold, currentuser)
                sellshares = '-' + str(shares)
                db.execute("INSERT INTO history(user, symbol, shares, price ) VALUES(?, ?, ?, ?)", currentuser, symbol, sellshares, price)
                return render_template("sold.html", symbol=symbol, symb=symb["name"], total=total, shares=shares, sym=sym)
            elif updshares < 0:
                return apology("Not enough shares to complete transaction")


    return render_template("sell.html", sym=sym)


@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():

    if request.method == "POST":
        try:
            currentuser = session["user_id"]
            csh = int(request.form.get("add"))
            prevcash = db.execute("SELECT SUM(cash) FROM users WHERE id = ?", currentuser)
            newcash = csh + prevcash[0]["SUM(cash)"]
            db.execute("UPDATE users SET cash = ?", newcash)
            return render_template("addedcash.html", csh=csh)

        except:
            return apology("Something went wrong with the transaction, Please try again")

    return render_template("addcash.html")
