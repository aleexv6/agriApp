from flask import Flask, render_template, url_for, request
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


@app.route("/basis", methods=['GET', 'POST'])
def base():
    prod = dict()
    expi = dict()
    basis = dict()
    for produit in productPhysique:
        if produit != 'Ble dur':
            data = {produit : list(dfPhysique[dfPhysique['Produit'] == produit]['Place'].unique())}
            prod.update(data)
    for produit in productPhysique:
        if produit != 'Ble dur':
            ticktick = listProductFutures[produit]
            data = {produit : list(dfFutures[dfFutures['Ticker'] == ticktick]['Expiration'].unique())}
            expi.update(data)       

    return render_template('basis.html', dfFutures=dfFutures, listProductFutures=listProductFutures, productPhysique=productPhysique, dfPhysique=dfPhysique, prod=prod, expi=expi)

@app.route('/process_basis', methods=['POST', 'GET'])
def process_basis():
  if request.method == "POST":
    data = request.get_json()
    df = dfPhysique[(dfPhysique['Produit'] == data[0]['Produit']) & (dfPhysique['Place'] == data[1]['Place'])]
    dfFut = dfFutures[(dfFutures['Ticker'] == listProductFutures[data[0]['Produit']]) & (dfFutures['Expiration'] == data[2]['Expiration'])]

    df = df[['Date', 'Prix']]
    df['Date'] = df['Date'].dt.date
    dfFut = dfFut[['Date', 'Prix']]
    dfFut['Date'] = dfFut['Date'].dt.date
    merged_df = pd.merge(df, dfFut, on='Date', how='inner')
    merged_df['Basis'] = merged_df['Prix_x'] - merged_df['Prix_y']

    json_data = [[row['Date'], row['Basis']] for _, row in merged_df.iterrows()]
    json_string = pd.Series(json_data).to_json(orient='values')

    return json_string
    