from flask import Flask, render_template
import database as db
import pandas as pd

app = Flask(__name__)

expi = {'Ble tendre' : 'MAR24', 'Mais' : 'MAR24', 'Colza' : 'MAY24'}
listProductFutures = {'Ble tendre':'EBM', 'Mais':'EMA', 'Colza':'ECO'}

cursorPhysique = db.get_database_physical().find({})
dfPhysique = pd.DataFrame(list(cursorPhysique)).sort_values(by='Date', ascending=True)
productPhysique = dfPhysique['Produit'].unique()

cursorFutures = db.get_database_euronext().find({})
dfFutures = pd.DataFrame(list(cursorFutures)).sort_values(by='Date', ascending=True)
productFutures = dfFutures['Ticker'].unique()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/physique")
def physique():
    return render_template('physique.html', data=dfPhysique, listProduct=productPhysique, datafutures=dfFutures, listProductFutures=listProductFutures, expi=expi)

@app.route("/futures")
def futures():
    return render_template('futures.html', listProduct=productFutures, data=dfFutures, listProductFutures=listProductFutures)
    