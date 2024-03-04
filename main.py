from flask import Flask, render_template
import database as db
import pandas as pd
from highcharts_core import highcharts
from bson import json_util

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


@app.route("/basis")
def base():
    prod = dict()
    expi = dict()
    for produit in productPhysique:
        if produit != 'Ble dur':
            data = {produit : list(dfPhysique[dfPhysique['Produit'] == produit]['Place'].unique())}
            prod.update(data)
    for produit in productPhysique:
        if produit != 'Ble dur':
            ticktick = listProductFutures[produit]
            data = {produit : list(dfFutures[dfFutures['Ticker'] == ticktick]['Expiration'].unique())}
            expi.update(data)       

    dfPhysiqueEBM = dfPhysique[(dfPhysique['Produit'] == 'Ble tendre') & (dfPhysique['Place'] == 'La Pallice Rendu')]
    dfPhysiqueEBM = dfPhysiqueEBM[['Date', 'Prix']]
    dfPhysiqueEBM = dfPhysiqueEBM[dfPhysiqueEBM['Date'].dt.year > 2023]
    json_data = [[row['Date'], row['Prix']] for _, row in dfPhysiqueEBM.iterrows()]
    json_string = pd.Series(json_data).to_json(orient='values')

    return render_template('basis.html', dfFutures=dfFutures, listProductFutures=listProductFutures, productPhysique=productPhysique, dfPhysique=dfPhysique, prod=prod, expi=expi, PhysiqueJson=json_string)