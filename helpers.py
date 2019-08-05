import requests
from flask import session, redirect
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs) :
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    try:
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{symbol}/quote?token=sk_b788d92f696a4b178e516dd9dd84c1a5")
        response.raise_for_status()
    except requests.RequestException:
        return None
    
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None

