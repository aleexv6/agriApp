from flask import Flask, render_template, url_for, request
import database as db
import pandas as pd
from highcharts_core import highcharts
from bson import json_util
import re

app = Flask(__name__)

expi = {'Ble tendre' : 'MAY24', 'Mais' : 'JUN24', 'Colza' : 'MAY24'}
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
    expiAll = dict()
    for produit in productPhysique:
        if produit != 'Ble dur':
            data = {produit : list(dfPhysique[dfPhysique['Produit'] == produit]['Place'].unique())}
            prod.update(data)
    for produit in productPhysique:
        if produit != 'Ble dur':
            ticktick = listProductFutures[produit]
            data = {produit : list(dfFutures[(dfFutures['Ticker'] == ticktick) & (dfFutures['Expired'] == False)]['Expiration'].unique())}
            expi.update(data)    
    for produit in productPhysique:
        if produit != 'Ble dur':
            ticktick = listProductFutures[produit]
            data = {produit : list(dfFutures[dfFutures['Ticker'] == ticktick]['Expiration'].unique())}
            expiAll.update(data)

    return render_template('basis.html', dfFutures=dfFutures, listProductFutures=listProductFutures, productPhysique=productPhysique, dfPhysique=dfPhysique, prod=prod, expi=expi, expiAll=expiAll)

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
  
@app.route("/spread", methods=['GET', 'POST'])
def spread():
    fut = []
    expi = dict()
    expiAll = dict()
    for key, values in listProductFutures.items():
        fut.append(values)
        
    for produit in productPhysique:
        if produit != 'Ble dur':
            ticktick = listProductFutures[produit]
            data = {produit : list(dfFutures[(dfFutures['Ticker'] == ticktick) & (dfFutures['Expired'] == False)]['Expiration'].unique())}
            expi.update(data)    
    for produit in productPhysique:
        if produit != 'Ble dur':
            ticktick = listProductFutures[produit]
            data = {produit : list(dfFutures[dfFutures['Ticker'] == ticktick]['Expiration'].unique())}
            expiAll.update(data)
    return render_template('spread.html', dfFutures=dfFutures, listProductFutures=list(listProductFutures.keys()), productPhysique=productPhysique, dfPhysique=dfPhysique, fut=fut, expi=expi, expiAll=expiAll)
    
@app.route('/process_spread', methods=['POST', 'GET'])
def process_spread():
    json_string = dict()
    if request.method == 'POST':
        string1 = request.get_json()[0]['Leg1'].split('_')
        df1 = dfFutures[(dfFutures['Ticker'] == string1[0]) & (dfFutures['Expiration'] == string1[1])]
        string2 = request.get_json()[0]['Leg2'].split('_')
        df2 = dfFutures[(dfFutures['Ticker'] == string2[0]) & (dfFutures['Expiration'] == string2[1])]
        string3 = request.get_json()[0]['Leg3'].split('_')
        df3 = dfFutures[(dfFutures['Ticker'] == string3[0]) & (dfFutures['Expiration'] == string3[1])]
        string4 = request.get_json()[0]['Leg4'].split('_')
        df4 = dfFutures[(dfFutures['Ticker'] == string4[0]) & (dfFutures['Expiration'] == string4[1])]

        if request.get_json()[0]['Type'] == 'SP':
            merged = pd.merge(df1, df2, on='Date', how='inner')
            merged['Spread'] = merged['Prix_x'] - merged['Prix_y']
            json_data = [[row['Date'], row['Spread']] for _, row in merged.iterrows()]
            json_string = pd.Series(json_data).to_json(orient='values')

        elif request.get_json()[0]['Type'] == 'BF': 
            merged = pd.merge(df1, df2, on='Date', how='inner')
            fmerged = pd.merge(merged, df3, on='Date', how='inner')
            fmerged['Spread'] = fmerged['Prix_x'] + (-2 * fmerged['Prix_y']) + fmerged['Prix']
            json_data = [[row['Date'], row['Spread']] for _, row in fmerged.iterrows()]
            json_string = pd.Series(json_data).to_json(orient='values')
        
        elif request.get_json()[0]['Type'] == 'CF': 
            merged = pd.merge(df1, df2, on='Date', how='inner')
            merged = merged.rename(columns={'Prix_x':'Prix1', 'Prix_y':'Prix2'})
            merged = pd.merge(merged, df3, on='Date', how='inner')
            merged = merged.rename(columns={'Prix':'Prix3'})
            fmerged = pd.merge(merged, df4, on='Date', how='inner')
            print(fmerged.columns)
            fmerged['Spread'] = fmerged['Prix1'] - fmerged['Prix2'] - fmerged['Prix3'] + fmerged['Prix']
            json_data = [[row['Date'], row['Spread']] for _, row in fmerged.iterrows()]
            json_string = pd.Series(json_data).to_json(orient='values')
        
        elif request.get_json()[0]['Type'] == 'OT':
            if request.method == 'POST':
                data = request.get_json()[0]['OtherSpread']
                if data is not None:
                    data = data.upper()
                    data = data.replace(' ', '')
                    operators = re.findall(r'[-+*/]', data)
                    data = re.split(r'[-+*/]', data)
                    data = [item.split('_') for item in data]
                    for i in range(len(data)):
                        df = dfFutures[(dfFutures['Ticker'] == data[i][0]) & (dfFutures['Expiration'] == data[i][1])]
                        df = df.reset_index()
                        if i > 0:
                            merged = pd.merge(df, tmp, on='Date', how='inner')
                            print(merged)
                            if operators[i-1] == '+':
                                merged['Spread'] = merged['Prix_y'] + merged['Prix_x']
                            elif operators[i-1] == '-':
                                merged['Spread'] = merged['Prix_y'] - merged['Prix_x']
                            elif operators[i-1] == '*':
                                merged['Spread'] = merged['Prix_y'] * merged['Prix_x']
                            elif operators[i-1] == '/':
                                merged['Spread'] = merged['Prix_y'] / merged['Prix_x']
                            else:
                                print("Invalid operand")
                            print(merged['Spread'])
                        tmp = dfFutures[(dfFutures['Ticker'] == data[i][0]) & (dfFutures['Expiration'] == data[i][1])]
                        tmp = tmp.reset_index()
                    json_data = [[row['Date'], row['Spread']] for _, row in merged.iterrows()]
                    json_string = pd.Series(json_data).to_json(orient='values')

    return json_string