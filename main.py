from flask import Flask, render_template, url_for, request
import database as db
import pandas as pd
from bson import json_util
import re
from cot import format_data_euronext, net_position_euronext, get_cot_from_db_euronext, seasonality_euronext, variation_euronext
import warnings
import requests
from datetime import datetime
import numpy as np

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

jours_feries = [
    (1, 1),  # Nouvel An
    (5, 1),  # Fête du Travail
    (5, 8),  # Victoire des Alliés
    (7, 14),  # Fête Nationale
    (8, 15),  # Assomption
    (11, 1),  # Toussaint
    (11, 11),  # Armistice
    (12, 25)  # Noël
]

def reformat_date(date):
    month_to_number = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }
    month = date[:3]
    year = date[3:]
    return f"20{year}-{month_to_number[month]}-10"

def est_jour_ferie(date):
    # Vérifie si la date est un jour férié en France
    return (date.month, date.day) in jours_feries

def est_jour_ouvre(date):
    # Vérifie si la date est un samedi ou un dimanche
    return date.weekday() < 5

def jour_ouvrable_francais(date):
    # Compte le nombre de jours ouvrés français jusqu'à la date donnée
    debut_annee = datetime(date.year, 1, 1)
    jours_ouvrables = sum(1 for day in pd.date_range(debut_annee, date) if est_jour_ouvre(day) and not est_jour_ferie(day))
    return jours_ouvrables

# Fonction à appliquer sur la colonne des dates
def jour_ouvrable_francais_apply(date):
    return jour_ouvrable_francais(date.to_pydatetime())

def get_fr_agr_mer_cotations():
        url = 'https://visionet.franceagrimer.fr/Pages/OpenDocument.aspx?fileurl=SeriesChronologiques%2fproductions%20vegetales%2fgrandes%20cultures%2fcotations%2fSCR-COT-CER_FR-A23.xls&telechargersanscomptage=oui'
        try:
            r = requests.get(url)
            r.raise_for_status()
            with open("cotations.xls", "wb") as f:
                f.write(r.content)

        except requests.exceptions.RequestException as e:
            print(f"Error downloading the file: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        dfBle = pd.read_excel('cotations.xls', sheet_name='cotations blé tendre')
        dfBle['Date'] = pd.to_datetime(dfBle['Date'])
        dfBlePalice = dfBle[['Date', 'Blé tendre Rendu Pallice Supérieur (A2)\nBase juillet']]
        dfMais = pd.read_excel('cotations.xls', sheet_name='cotations maïs')
        dfMais['Date'] = pd.to_datetime(dfMais['Date'])
        dfMaisPalice = dfMais[['Date', 'Maïs\nFob Atlantique\nBase juillet']]
        return dfBlePalice[1:], dfMaisPalice[1:]

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

@app.route("/cot")
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

@app.route("/futures_curve")
def curve():
    df = dfFutures[dfFutures['Expired'] == False]
    df = df[['Date', 'Ticker', 'Expiration', 'Prix']]
    lastDfFuturesEBM = df[df['Ticker'] == 'EBM'].tail(5)
    lastDfFuturesEBM['SortedExpi'] = lastDfFuturesEBM['Expiration'].apply(reformat_date)
    lastDfFuturesEBM = lastDfFuturesEBM.sort_values(by='SortedExpi')
    lastDfFuturesEMA = df[df['Ticker'] == 'EMA'].tail(5)
    lastDfFuturesEMA['SortedExpi'] = lastDfFuturesEMA['Expiration'].apply(reformat_date)
    lastDfFuturesEMA = lastDfFuturesEMA.sort_values(by='SortedExpi')
    lastDfFuturesECO = df[df['Ticker'] == 'ECO'].tail(5)
    lastDfFuturesECO['SortedExpi'] = lastDfFuturesECO['Expiration'].apply(reformat_date)
    lastDfFuturesECO = lastDfFuturesECO.sort_values(by='SortedExpi')
    
    return render_template('curve.html', curve_ebm=lastDfFuturesEBM.to_dict(orient='records'), curve_ema=lastDfFuturesEMA.to_dict(orient='records'), curve_eco=lastDfFuturesECO.to_dict(orient='records'))

@app.route("/saisonnalite")
def saisonnalite():
    dfBle, dfMais = get_fr_agr_mer_cotations()
    dfBle = dfBle.rename(columns={'Blé tendre Rendu Pallice Supérieur (A2)\nBase juillet': 'Prix'})
    dfBle = dfBle.dropna()
    dfBle = dfBle[~(dfBle == 0).any(axis=1)]
    dfBle = dfBle.drop_duplicates(subset=['Date'])
    dfBle['JourOuvrableFrancais'] = dfBle['Date'].apply(jour_ouvrable_francais_apply)    
    dfBle["Percentage Change"] = dfBle["Prix"].pct_change() * 100
    dfBle["Year"] = dfBle['Date'].dt.year
    yearly_cumulative_percentage_changeBle = dfBle.groupby("Year")["Percentage Change"].cumsum()
    median_cumulative_percentage_changeBle = yearly_cumulative_percentage_changeBle.groupby(dfBle['JourOuvrableFrancais']).median()

    dfMais = dfMais.rename(columns={'Maïs\nFob Atlantique\nBase juillet': 'Prix'})
    dfMais = dfMais.dropna()
    dfMais = dfMais[~(dfMais == 0).any(axis=1)]
    dfMais = dfMais[dfMais['Prix'] != 'Trêve des confiseurs']
    dfMais = dfMais.drop_duplicates(subset=['Date'])
    dfMais['JourOuvrableFrancais'] = dfMais['Date'].apply(jour_ouvrable_francais_apply)    
    dfMais["Percentage Change"] = dfMais["Prix"].pct_change() * 100
    dfMais["Year"] = dfMais['Date'].dt.year
    yearly_cumulative_percentage_changeMais = dfMais.groupby("Year")["Percentage Change"].cumsum()
    median_cumulative_percentage_changeMais = yearly_cumulative_percentage_changeMais.groupby(dfMais['JourOuvrableFrancais']).median()
    return render_template('saisonnalite.html', dataBle=median_cumulative_percentage_changeBle[:247].to_dict(), dataMais=median_cumulative_percentage_changeMais[:247].to_dict())

@app.route("/production")
def production():
    dataEBM = []
    dataEMA = []
    dataECO = []
    cursorProd = db.get_database_production().find({})
    dfProd = pd.DataFrame(list(cursorProd)).sort_values(by='Date', ascending=True) 
    dfProd = dfProd.drop('Expired', axis=1)
    dfEBM = dfProd[dfProd['ESPECES'] == 'Blé tendre']
    for i, j in dfEBM.groupby('Date'):
        max_collecte = j['TOTAL_COLLECTE'].max()
        dataEBM.append(j[j['TOTAL_COLLECTE'] == max_collecte])
    finalEBM = pd.concat(dataEBM).drop('_id', axis=1)

    dfEMA = dfProd[dfProd['ESPECES'] == 'Maïs']
    for i, j in dfEMA.groupby('Date'):
        max_collecte = j['TOTAL_COLLECTE'].max()
        dataEMA.append(j[j['TOTAL_COLLECTE'] == max_collecte])
    finalEMA = pd.concat(dataEMA).drop('_id', axis=1)

    dfECO = dfProd[dfProd['ESPECES'] == 'Colza']
    for i, j in dfECO.groupby('Date'):
        max_collecte = j['TOTAL_COLLECTE'].max()
        dataECO.append(j[j['TOTAL_COLLECTE'] == max_collecte])
    finalECO = pd.concat(dataECO).drop('_id', axis=1)
    return render_template('production.html', dataEBM=finalEBM.to_dict(orient='records'), dataEMA=finalEMA.to_dict(orient='records'), dataECO=finalECO.to_dict(orient='records'))

@app.route("/developpement")
def developpement():
    
    return render_template('developpement.html')

@app.route('/process_dev', methods=['POST', 'GET'])
def process_dev():
    if request.method == "POST":
        data = request.get_json()
        dates = data['Marketing_year'].split('_')
        int_dates = [int(year) for year in dates]
    cursorDev = db.get_database_dev().find({
        "Year": {
        "$gte": int_dates[0] - 6,
        "$lte": int_dates[1]
    }
    })
    df = pd.DataFrame(list(cursorDev)).sort_values(by='Date', ascending=True) 
    df = df.drop('_id', axis=1)
    dfMoy = df[df['Year'] < int_dates[0]]
    dfDev = df[df['Year'].isin(int_dates)]

    dfDevBleTendre = dfDev[(dfDev['Culture'] == 'Blé tendre') & (dfDev['Région'] == 'Moyenne France')]
    bleTendreStart = dfDevBleTendre[dfDevBleTendre['Semis'] == 0]['Date'].iloc[0]
    if int_dates[1] == datetime.now().year: 
        dfBleTendreMY = dfDevBleTendre[(dfDevBleTendre['Date'] > bleTendreStart) & (dfDevBleTendre['Year'] <= datetime.now().year)]
    else:
        bleTendreEnd = dfDevBleTendre[(dfDevBleTendre['Year'] == int_dates[1]) & (dfDevBleTendre['Récolte'] > 90)]['Date'].iloc[-1]
        dfBleTendreMY = dfDevBleTendre[(dfDevBleTendre['Date'] >= bleTendreStart) & (dfDevBleTendre['Date'] <= bleTendreEnd)]

    dfDevBleDur = dfDev[(dfDev['Culture'] == 'Blé dur') & (dfDev['Région'] == 'Moyenne France')]
    bleDurStart = dfDevBleDur[dfDevBleDur['Semis'] == 0]['Date'].iloc[0]
    if int_dates[1] == datetime.now().year: 
        dfBleDurMY = dfDevBleDur[(dfDevBleDur['Date'] > bleDurStart) & (dfDevBleDur['Year'] <= datetime.now().year)]
    else:
        bleDurEnd = dfDevBleDur[(dfDevBleDur['Year'] == int_dates[1]) & (dfDevBleDur['Récolte'] > 90)]['Date'].iloc[-1]
        dfBleDurMY = dfDevBleDur[(dfDevBleDur['Date'] >= bleDurStart) & (dfDevBleDur['Date'] <= bleDurEnd)]

    dfDevMais = dfDev[(dfDev['Culture'] == 'Maïs grain') & (dfDev['Région'] == 'Moyenne France')].reset_index()
    maisStart = dfDevMais[(dfDevMais['Semis'] > 0) & (dfDevMais['Year'] == int_dates[1])].index[0] - 1
    if int_dates[1] == datetime.now().year: 
        dfMaisMY = dfDevMais[(dfDevMais.index >= maisStart) & (dfDevMais['Year'] <= datetime.now().year)]
    else: 
        maisEnd = dfDevMais[(dfDevMais['Year'] == int_dates[1]) & (dfDevMais['Récolte'] > 90)]['Date'].iloc[-1]
        dfMaisMY = dfDevMais[(dfDevMais.index >= maisStart) & (dfDevMais['Date'] <= maisEnd)]
    df = pd.concat([dfBleTendreMY, dfMaisMY, dfBleDurMY])

    dfMoy = dfMoy[dfMoy['Région'] == 'Moyenne France']
    aggregated_stats = dfMoy.groupby(['Culture', 'Week']).agg({
        'Semis': ['mean', 'min', 'max'],
        'Levée': ['mean', 'min', 'max'],
        'Début tallage': ['mean', 'min', 'max'],
        'Épi 1 cm': ['mean', 'min', 'max'],
        '2 noeuds': ['mean', 'min', 'max'],
        'Épiaison': ['mean', 'min', 'max'],
        '6/8 feuilles visibles': ['mean', 'min', 'max'],
        'Floraison femelle': ['mean', 'min', 'max'],
        'Début tallage': ['mean', 'min', 'max'],
        'Humidité du grain 50%': ['mean', 'min', 'max'],
        'Récolte': ['mean', 'min', 'max'],
    }).reset_index()
    aggregated_stats.columns = ['_'.join(col).strip() if col[1] else col[0] for col in aggregated_stats.columns.values]
    merged = pd.merge(df, aggregated_stats, on=['Culture', 'Week'], how='inner')
    return merged.to_json(orient='values')