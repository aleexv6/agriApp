from flask import Flask
import database as db

app = Flask(__name__)

physique = db.get_database_physical()
euronext = db.get_database_euronext()


@app.route("/")
def hello_world():
    return f"<p>Hello, World !</p>"
    