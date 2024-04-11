from flask import Flask, render_template, url_for, request
import database as db
import pandas as pd
from highcharts_core import highcharts
from bson import json_util
import re
from cot import format_data_euronext, net_position_euronext, get_cot_from_db_euronext, seasonality_euronext, variation_euronext
import warnings

warnings.filterwarnings("ignore")

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
                    result = pd.DataFrame()

                    for i, (nb_contracts, ticker, expiration) in enumerate(data):
                        nb_contracts = int(nb_contracts)
                        # Filter DataFrame based on current ticker and expiration
                        df_temp = dfFutures[(dfFutures['Ticker'] == ticker) & (dfFutures['Expiration'] == expiration)]
                        
                        # Rename the 'Prix' column to avoid conflicts during merge
                        df_temp = df_temp.rename(columns={'Prix': f'Prix_{i}'})
                        df_temp[f'Prix_{i}'] = df_temp[f'Prix_{i}'] * nb_contracts
                        if i == 0:
                            result = df_temp
                        else:
                            # Merge the current DataFrame with the result DataFrame based on the date column
                            result = pd.merge(result, df_temp, on='Date', how='inner')

                    # Perform arithmetic operations based on operands
                    for i in range(1, len(data)):
                        if operators[i - 1] == '+':
                            result[f'Prix_0'] += result[f'Prix_{i}'] * nb_contracts
                        elif operators[i - 1] == '-':
                            result[f'Prix_0'] -= result[f'Prix_{i}'] * nb_contracts
                    results = result[['Date', 'Prix_0']]
                    json_data = []
                    for _, row in results.iterrows():
                        json_data.append([row['Date'], row['Prix_0']])
                    json_string = pd.Series(json_data).to_json(orient='values')

    return json_string

@app.route("/cot", methods=['GET', 'POST'])
def cot():
    #for i in ['EBM', 'EMA', 'ECO']:
    dfEBM = get_cot_from_db_euronext('EBM')
    dfEMA = get_cot_from_db_euronext('EMA')
    dfECO = get_cot_from_db_euronext('ECO')

    dfEuronextEBM = format_data_euronext(dfEBM)
    dfEuronextEMA = format_data_euronext(dfEMA)
    dfEuronextECO = format_data_euronext(dfECO)

    net_euronext_ebm = net_position_euronext(dfEuronextEBM)
    net_euronext_ema = net_position_euronext(dfEuronextEMA)
    net_euronext_eco = net_position_euronext(dfEuronextECO)
    net_euronext_ebm = net_euronext_ebm.reset_index()
    net_euronext_ema = net_euronext_ema.reset_index()
    net_euronext_eco = net_euronext_eco.reset_index()
    net_euronext_ebm = net_euronext_ebm[['Date', 'Ticker', 'Produit', 'CommerceNetPos', 'FondNetPos', 'InvestAndCredit', 'OtherFinancial']]
    net_euronext_eco = net_euronext_eco[['Date', 'Ticker', 'Produit', 'CommerceNetPos', 'FondNetPos', 'InvestAndCredit', 'OtherFinancial']]
    net_euronext_ema = net_euronext_ema[['Date', 'Ticker', 'Produit', 'CommerceNetPos', 'FondNetPos', 'InvestAndCredit', 'OtherFinancial']]


    data_seasonality_euronext_ebm = seasonality_euronext(dfEuronextEBM)
    list = [df.to_dict(orient='records') for df in data_seasonality_euronext_ebm]
    fondsSeasonalityListEBM = [
        [record for record in list_of_dicts if record.get('Type') == "Fonds d'investissement"]
        for list_of_dicts in list
    ]
    seasonality_fonds_euronext_ebm = [lst for lst in fondsSeasonalityListEBM if lst]
    commSeasonalityListEBM = [
        [record for record in list_of_dicts if record.get('Type') == "Entreprises commerciales"]
        for list_of_dicts in list
    ]
    seasonality_comm_euronext_ebm = [lst for lst in commSeasonalityListEBM if lst]

    data_seasonality_euronext_ema = seasonality_euronext(dfEuronextEMA)
    list = [df.to_dict(orient='records') for df in data_seasonality_euronext_ema]
    fondsSeasonalityListEMA = [
        [record for record in list_of_dicts if record.get('Type') == "Fonds d'investissement"]
        for list_of_dicts in list
    ]
    seasonality_fonds_euronext_ema = [lst for lst in fondsSeasonalityListEMA if lst]
    commSeasonalityListEMA = [
        [record for record in list_of_dicts if record.get('Type') == "Entreprises commerciales"]
        for list_of_dicts in list
    ]
    seasonality_comm_euronext_ema = [lst for lst in commSeasonalityListEMA if lst]

    data_seasonality_euronext_eco = seasonality_euronext(dfEuronextECO)
    list = [df.to_dict(orient='records') for df in data_seasonality_euronext_eco]
    fondsSeasonalityListECO = [
        [record for record in list_of_dicts if record.get('Type') == "Fonds d'investissement"]
        for list_of_dicts in list
    ]
    seasonality_fonds_euronext_eco = [lst for lst in fondsSeasonalityListECO if lst]
    commSeasonalityListECO = [
        [record for record in list_of_dicts if record.get('Type') == "Entreprises commerciales"]
        for list_of_dicts in list
    ]
    seasonality_comm_euronext_eco = [lst for lst in commSeasonalityListECO if lst]


    df_variation_ebm = variation_euronext(dfEuronextEBM)
    df_variation_fonds_ebm = df_variation_ebm[df_variation_ebm['Type'] == "Fonds d'investissement"]

    df_variation_ema = variation_euronext(dfEuronextEMA)
    df_variation_fonds_ema = df_variation_ema[df_variation_ema['Type'] == "Fonds d'investissement"]

    df_variation_eco = variation_euronext(dfEuronextECO)
    df_variation_fonds_eco = df_variation_eco[df_variation_eco['Type'] == "Fonds d'investissement"]

    return render_template('cot.html', net_euronext_ebm=net_euronext_ebm.to_dict(orient='records'), net_euronext_ema=net_euronext_ema.to_dict(orient='records'), net_euronext_eco=net_euronext_eco.to_dict(orient='records'), seasonality_fonds_euronext_ebm=seasonality_fonds_euronext_ebm, seasonality_comm_euronext_ebm=seasonality_comm_euronext_ebm, seasonality_fonds_euronext_ema=seasonality_fonds_euronext_ema, seasonality_comm_euronext_ema=seasonality_comm_euronext_ema, seasonality_fonds_euronext_eco=seasonality_fonds_euronext_eco, seasonality_comm_euronext_eco=seasonality_comm_euronext_eco, df_variation_fonds_ebm=df_variation_fonds_ebm.to_dict(orient='records'), df_variation_fonds_eco=df_variation_fonds_eco.to_dict(orient='records'), df_variation_fonds_ema=df_variation_fonds_ema.to_dict(orient='records'))