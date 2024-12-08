from flask import Flask, render_template, request, jsonify, send_from_directory
import database as db
import pandas as pd
import re
from cot import format_data_euronext, net_position_euronext, get_cot_from_db_euronext, seasonality_euronext, variation_euronext
import warnings
import requests
from datetime import datetime, date, timedelta
import numpy as np
import folium
import os
from collections import defaultdict
import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import matplotlib as mpl


warnings.filterwarnings("ignore")

app = Flask(__name__)

def EBM_current_futures_month(current_date=None):
    if current_date is None:
        current_date = date.today()
    
    # Mois d'expiration : mars, mai, septembre, décembre
    expiration_months = [3, 5, 9, 12]
    month_to_str = {3: "MAR", 5: "MAY", 9: "SEP", 12: "DEC"}

    # Fonction pour trouver le 10e jour ouvré du mois (ou le jour ouvré suivant)
    def get_expiration_date(year, month):
        expiration_date = date(year, month, 10)
        # Si le 10e jour est un week-end, avancer au prochain jour ouvré
        while expiration_date.weekday() >= 5:  # 5 = samedi, 6 = dimanche
            expiration_date += timedelta(days=1)
        return expiration_date

    # Parcourir les mois d'expiration pour trouver le contrat actif
    for month in expiration_months:
        expiration_date = get_expiration_date(current_date.year, month)
        if current_date <= expiration_date:
            return f"{month_to_str[month]}{str(current_date.year)[-2:]}"
    
    # Si on dépasse tous les mois de l'année courante, retourner le premier contrat de l'année suivante
    next_year = current_date.year + 1
    return f"{month_to_str[expiration_months[0]]}{str(next_year)[-2:]}"

def EMA_current_futures_month(current_date=None):
    if current_date is None:
        current_date = date.today()
    
    # Mois d'expiration : mars, mai, septembre, décembre
    expiration_months = [3, 6, 8, 11]
    month_to_str = {3: "MAR", 6: "JUN", 8: "AUG", 11: "NOV"}

    # Fonction pour trouver le 10e jour ouvré du mois (ou le jour ouvré suivant)
    def get_expiration_date(year, month):
        expiration_date = date(year, month, 5)
        # Si le 10e jour est un week-end, avancer au prochain jour ouvré
        while expiration_date.weekday() >= 5:  # 5 = samedi, 6 = dimanche
            expiration_date += timedelta(days=1)
        return expiration_date

    # Parcourir les mois d'expiration pour trouver le contrat actif
    for month in expiration_months:
        expiration_date = get_expiration_date(current_date.year, month)
        if current_date <= expiration_date:
            return f"{month_to_str[month]}{str(current_date.year)[-2:]}"
    
    # Si on dépasse tous les mois de l'année courante, retourner le premier contrat de l'année suivante
    next_year = current_date.year + 1
    return f"{month_to_str[expiration_months[0]]}{str(next_year)[-2:]}"

def ECO_current_futures_month(current_date=None):
    if current_date is None:
        current_date = date.today()
    
    # Mois d'expiration : mars, mai, septembre, décembre
    expiration_months = [1, 4, 7, 10]
    month_to_str = {1: "FEB", 4: "MAY", 7: "AUG", 10: "NOV"}

    # Fonction pour trouver le 10e jour ouvré du mois (ou le jour ouvré suivant)
    def get_expiration_date(year, month):
        expiration_date = date(year, month, 28)
        # Si le 10e jour est un week-end, avancer au prochain jour ouvré
        while expiration_date.weekday() >= 5:  # 5 = samedi, 6 = dimanche
            expiration_date += timedelta(days=1)
        return expiration_date

    # Parcourir les mois d'expiration pour trouver le contrat actif
    for month in expiration_months:
        expiration_date = get_expiration_date(current_date.year, month)
        if current_date <= expiration_date:
            return f"{month_to_str[month]}{str(current_date.year)[-2:]}"
    
    # Si on dépasse tous les mois de l'année courante, retourner le premier contrat de l'année suivante
    next_year = current_date.year + 1
    return f"{month_to_str[expiration_months[0]]}{str(next_year)[-2:]}"

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

def get_market_year(row):
    year = row['Year']
    week = row['Week']
    culture = row['Culture']
    if culture in ['Blé tendre', 'Blé dur']:
        if week >= 36:
            market_year = f"{year}/{year + 1}"
        else:
            market_year = f"{year - 1}/{year}"
    else:
        if 9 <= week <= 49:
            market_year = f"{year - 1}/{year}"
        else:
            market_year = f"{year - 1}/{year}"
    return market_year

def full_expiration_date(row):
    # Define month mapping
    month_map = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 
        'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8, 
        'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    
    # Extract month and year
    month_str = row['Expiration'][:3]
    year_str = row['Expiration'][3:]
    
    # Convert to full year assuming no year < 2000
    full_year = 2000 + int(year_str)

    if row['Ticker'] == 'EBM':
        fulldate = date(full_year, month_map[month_str], 10)
    elif row['Ticker'] == 'EMA':
        fulldate = date(full_year, month_map[month_str], 5)
    elif row['Ticker'] == 'ECO':
        fulldate = date(full_year, month_map[month_str], 1)
    else:
        fulldate = 0
    
    # Create datetime object (using first of the month for sorting)
    return fulldate

listProductFutures = {'Ble tendre':'EBM', 'Mais':'EMA', 'Colza':'ECO', 'Ble dur':'EDW'} #set a futures ticker for every product name

#initalize data that we use in a lot of pages here
cursorPhysique = db.get_database_physical().find({}, {'_id': 0})#get data from db removing id column
dfPhysique = pd.DataFrame(list(cursorPhysique)).sort_values(by='Date', ascending=True).reset_index(drop=True)#put data in df for sorting on date and reindexing
cursorFutures = db.get_database_new_euronext().find({}, {'_id': 0})#get data from db removing id column
dfFutures = pd.DataFrame(list(cursorFutures)).sort_values(by='Date', ascending=True).reset_index(drop=True)#put data in df for sorting on date and reindexing
dfFutures['Expiration Full Date'] = dfFutures[['Ticker', 'Expiration']].apply(full_expiration_date, axis=1)
sampleFutures = dfFutures.tail(100).sort_values(by='Expiration Full Date') #sample 100 last values (to avoid sorting full df) to sort expiration date by date

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

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/physique")
def physique(dfPhysique=dfPhysique):
    dfPhysique = dfPhysique[dfPhysique['Produit'] != 'Ble dur'] #remove ble dur product because we do not have quality futures for it
    uniqueDates = dfPhysique['Date'].unique() #get unique dates
    lastTwoDates = uniqueDates[-2:] #get last two dates 
    lastTwoDays= dfPhysique[dfPhysique['Date'].isin(lastTwoDates)] #get data from last two dates
    uniqueProduct = sorted(lastTwoDays['Produit'].unique()) #get unique product sorted alphabeticaly

    currenData = lastTwoDays[lastTwoDays['Date'] == lastTwoDates[1]] #get very last daily data
    previousData = lastTwoDays[lastTwoDays['Date'] == lastTwoDates[0]] #get currentData -1 trading day
    currenData['Expiration'] = currenData['Produit'].apply( #auto set the expiration date of contract
        lambda x: EBM_current_futures_month() if x == "Ble tendre" 
        else EMA_current_futures_month() if x == "Mais" 
        else ECO_current_futures_month() if x == "Colza" 
        else '-'
    )
    currenData['Ticker'] = currenData['Produit'].map(listProductFutures) #map futures ticker to product name in df
    cursorFutures = db.get_database_new_euronext().find({'Date': {'$gte': str(lastTwoDates[1].date())}}, {'_id': 0}) #get futures data from db (only the daily data) without id
    dfFutures = pd.DataFrame(list(cursorFutures)) #make it a df
    dfFutures['Date'] = pd.to_datetime(dfFutures['Date']) #set as pd datetime

    tableData = pd.merge(currenData, dfFutures, on=['Date', 'Ticker', 'Expiration'], how='inner') #merge physical data and futures data with inner join for basis calculation

    tableData['Base'] = round(tableData['Prix'] - tableData['Close'], 2) #basis calculation

    calculateChange = pd.merge(currenData, previousData, on=['Produit', 'Place'], how='outer') #merge current and prev physical data with outer join for % change | x is current, y is previous

    calculateChange['Change'] = round(((calculateChange['Prix_x'] - calculateChange['Prix_y']) / calculateChange['Prix_y']) * 100, 2).fillna('-') #make % change calculation

    tableData = tableData.merge(calculateChange[['Produit', 'Place', 'Change']], on=['Produit', 'Place'], how='inner') #merge data to put each change with valid product and place

    return render_template('physique.html', data=dfPhysique.to_dict('records'), produits=uniqueProduct, tableData=tableData.to_dict('records'))

@app.route("/futures")
def futures(dfFutures=dfFutures):
    dfFutures['Date'] = pd.to_datetime(dfFutures['Date'])
    dfFutures = dfFutures.fillna(0)
    uniqueDates = dfFutures['Date'].unique() #get unique dates
    lastTwoDates = uniqueDates[-2:] #get last two dates 
    lastTwoDays= dfFutures[dfFutures['Date'].isin(lastTwoDates)] #get data from last two dates
    uniqueTicker = sorted(lastTwoDays['Ticker'].unique()) #get unique product sorted alphabeticaly

    currenData = lastTwoDays[lastTwoDays['Date'] == lastTwoDates[1]] #get very last daily data
    previousData = lastTwoDays[lastTwoDays['Date'] == lastTwoDates[0]] #get currentData -1 trading day

    tableData = pd.merge(currenData, previousData, on=['Ticker', 'Expiration'], how='outer') #merge current and prev physical data with outer join for % change | x is current, y is previous
    tableData['Change'] = round(((tableData['Close_x'] - tableData['Close_y']) / tableData['Close_y']) * 100, 2)
    tableData = tableData.rename(columns={'Date_x': 'Date', 'Open_x': 'Open', 'High_x': 'High', 'Low_x': 'Low', 'Close_x': 'Close', 'Volume_x': 'Volume', 'Open Interest_x': 'Open Interest', 'Expiration Full Date_x': 'Expiration Full Date'})
    tableData['Volume'] = tableData['Volume'].astype(int)
    tableData['Open Interest'] = tableData['Open Interest'].astype(int)
    tableData = tableData.fillna('-')
    tableData = tableData.replace(0, '-')

    tableData = tableData.sort_values(by='Expiration Full Date') #sort by date
    
    return render_template('futures.html', data=dfFutures.to_dict('records'), tickers=uniqueTicker, tableData=tableData.to_dict('records'))

@app.route("/basis", methods=['GET', 'POST'])
def base(dfPhysique=dfPhysique, dfFutures=dfFutures, sampleFutures=sampleFutures):    
    baseSelector = []
    for produit in sorted(dfPhysique['Produit'].unique()): #sort product to have always same order
        if produit != 'Ble dur': #remove ble dur we do not have futures
            place = sorted(list(dfPhysique[dfPhysique['Produit'] == produit]['Place'].unique())) #keep unique places for this product, sorted to always have same order
            ticker = listProductFutures[produit] #use dict to get futures ticker from product
            expi = list(sampleFutures[(sampleFutures['Ticker'] == ticker) & (sampleFutures['Expiration Full Date'] > date.today())]['Expiration'].unique()) #get expiration for the productn sorted by expiration date
            baseSelector.append({'Produit': produit, 'Place':place, 'Expi':expi})

    return render_template('basis.html', dfFutures=dfFutures, baseSelector=baseSelector)

@app.route('/process_basis', methods=['POST', 'GET'])
def process_basis():
  if request.method == "POST": # if we get a POST from front
    data = request.get_json() #get data from front (Produit, Place, Expiration)
    physique = dfPhysique[(dfPhysique['Produit'] == data['Produit']) & (dfPhysique['Place'] == data['Place'])] #search physical price for current product and place
    futures = dfFutures[(dfFutures['Ticker'] == listProductFutures[data['Produit']]) & (dfFutures['Expiration'] == data['Expiration'])] #search futures price for current contract
    futures['Date'] = pd.to_datetime(futures['Date'])
    df = pd.merge(physique, futures, on='Date', how='inner') #merge on dates
    df['Basis'] = df['Prix'] - df['Close'] #basis calculation
    df = df[['Date', 'Basis']]

    json_string = df.to_json(orient='values') #df to json for sending data

    return json_string
  
@app.route("/spread", methods=['GET', 'POST'])
def spread(dfFutures=dfFutures, sampleFutures=sampleFutures):
    spreadSelector = []
    for ticker in sorted(dfFutures['Ticker'].unique()): #loop throught unique tickers in df sorted alphabeticaly
        expi = list(sampleFutures[(sampleFutures['Ticker'] == ticker) & (sampleFutures['Expiration Full Date'] > date.today())]['Expiration'].unique()) #get expiration for the product sorted by expiration date
        spreadSelector.append({'Ticker': ticker, 'Expi': expi})
    return render_template('spread.html', dfFutures=dfFutures, spreadSelector=spreadSelector)
    
@app.route('/process_spread', methods=['POST', 'GET'])
def process_spread(dfFutures=dfFutures):
    json_string = None
    if request.method == 'POST':
        response = request.get_json()
        if response['Type'] == 'SP':
            firstLeg = dfFutures[(dfFutures['Ticker'] == response['Leg1'].split('_')[0]) & (dfFutures['Expiration'] == response['Leg1'].split('_')[1])][['Date', 'Ticker', 'Expiration', 'Close']] #getting data from df
            secondLeg = dfFutures[(dfFutures['Ticker'] == response['Leg2'].split('_')[0]) & (dfFutures['Expiration'] == response['Leg2'].split('_')[1])][['Date', 'Ticker', 'Expiration', 'Close']]
            spreadDf = pd.merge(firstLeg, secondLeg, on=['Date', 'Ticker'], how='inner') #x is firstleg, y is second leg
            spreadDf['Spread'] = spreadDf['Close_x'] - spreadDf['Close_y'] #spread calculation
            spreadDf = spreadDf[['Date', 'Spread']] #keep interesting values
            json_string = spreadDf.to_json(orient='values') #return json string
        elif response['Type'] == 'BF': 
            firstLeg = dfFutures[(dfFutures['Ticker'] == response['Leg1'].split('_')[0]) & (dfFutures['Expiration'] == response['Leg1'].split('_')[1])][['Date', 'Ticker', 'Expiration', 'Close']] #getting data from df
            secondLeg = dfFutures[(dfFutures['Ticker'] == response['Leg2'].split('_')[0]) & (dfFutures['Expiration'] == response['Leg2'].split('_')[1])][['Date', 'Ticker', 'Expiration', 'Close']]
            thirdLeg = dfFutures[(dfFutures['Ticker'] == response['Leg3'].split('_')[0]) & (dfFutures['Expiration'] == response['Leg3'].split('_')[1])][['Date', 'Ticker', 'Expiration', 'Close']]
            spreadDf = firstLeg.merge(secondLeg, on=['Date', 'Ticker'], how='inner').merge(thirdLeg, on=['Date', 'Ticker'], how='inner') #x is firstleg, y is secondleg and no letters is thirdleg
            spreadDf['Spread'] = spreadDf['Close_x'] + (-2 * spreadDf['Close_y']) + spreadDf['Close'] #spread calculation
            spreadDf = spreadDf[['Date', 'Spread']] #keep interesting values
            json_string = spreadDf.to_json(orient='values') #return json string
        else:
            json_string = {'response': 'error', 'message': 'Wrong type, please select valid spread type'} #if bad response type set message

        # TODO : Make the spread string allow a lot of calculation (stops at 3 with the merge) and secure the string against injections
        # elif response['Type'] == 'OT':
        #         data = request.get_json()['OtherSpread']
        #         if data is not None:
        #             data = data.upper()
        #             data = data.replace(' ', '')
        #             operators = re.findall(r'[-+*/]', data)
        #             data = re.split(r'[-+*/]', data)
        #             data = [item.split('_') for item in data]
        #             result = pd.DataFrame()

        #             for i, (nb_contracts, ticker, expiration) in enumerate(data):
        #                 nb_contracts = int(nb_contracts)
        #                 df_temp = dfFutures[(dfFutures['Ticker'] == ticker) & (dfFutures['Expiration'] == expiration)]
        #                 df_temp = df_temp.rename(columns={'Close': f'Close {i}'})
        #                 df_temp[f'Close {i}'] = df_temp[f'Close {i}'] * nb_contracts
        #                 if i == 0:
        #                     result = df_temp
        #                 else:
        #                     result = pd.merge(result, df_temp, on='Date', how='inner')
        #                 print(result.columns)

        #             for i in range(1, len(data)):
        #                 if operators[i - 1] == '+':
        #                     result[f'Close 0'] += result[f'Close {i}']
        #                 elif operators[i - 1] == '-':
        #                     result[f'Close 0'] -= result[f'Close {i}'] 
        #                 else:
        #                     json_string = {'result': 'Wrong operand used, please use only + and - operands'}
        #             results = result[['Date', 'Close 0']]
        #             json_string = results.to_json(orient='values')
        #             return json_string

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

@app.route("/futures-curve")
def curve(dfFutures=dfFutures):
    curveData = []
    lastFuturesDate = dfFutures.iloc[-1]['Date'] #get last date from df
    lastFutures = dfFutures[dfFutures['Date'] == lastFuturesDate] #filter on last date
    lastFutures = lastFutures.sort_values(by='Expiration Full Date').reset_index(drop=True) #sort by expiration date
    for ticker in lastFutures['Ticker'].unique(): #loop through unique tickers 
        data = {'Ticker': ticker, 'Expirations': list(lastFutures[lastFutures['Ticker'] == ticker]['Expiration']), 'Prix': list(lastFutures[lastFutures['Ticker'] == ticker]['Close'])} #create data for ticker, expis and prices
        curveData.append(data)    
    return render_template('curve.html', curveData=curveData)

@app.route("/saisonnalite")
def saisonnalite():
    dfBle = pd.read_csv("EBM.txt", index_col='Date', parse_dates=['Date'])
    dfBleDaily = dfBle.resample('1D').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'
    })
    dfBleDaily = dfBleDaily.dropna()
    dfBleDaily = dfBleDaily.reset_index()
    dfBleDaily['JourOuvrableFrancais'] = dfBleDaily['Date'].apply(jour_ouvrable_francais_apply)    
    dfBleDaily["Percentage Change"] = dfBleDaily['Close'].pct_change() * 100
    dfBleDaily["Year"] = dfBleDaily['Date'].dt.year
    dfBleDaily['Yearly cumulative'] = dfBleDaily.groupby("Year")['Percentage Change'].cumsum()
    median_cumulative = dfBleDaily.groupby('JourOuvrableFrancais')['Yearly cumulative'].median()
    return render_template('saisonnalite.html', dfBle=median_cumulative[:250].to_dict())

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
    cursorDev = db.get_database_dev_cond().find({
        "Year": {
        "$gte": int_dates[0] - 6,
        "$lte": int_dates[1]
    }
    })
    df = pd.DataFrame(list(cursorDev)).sort_values(by='Date', ascending=True) 
    df = df.drop('_id', axis=1)
    df = df[df['Région'] == "Moyenne France"]
    dfMoy = df[df['Year'] < int_dates[0]]
    dfDev = df[df['Year'].isin(int_dates)]

    dfDevBleTendre = dfDev[dfDev['Culture'] == 'Blé tendre']
    if datetime.now().year < int_dates[1]:
        dfBleTendreMY = dfDevBleTendre[(dfDevBleTendre['Year'] == int_dates[0]) & (dfDevBleTendre['Week'] >= 36)]
    else :
        dfBleTendreMY = dfDevBleTendre[((dfDevBleTendre['Year'] == int_dates[0]) & (dfDevBleTendre['Week'] >= 36)) | ((dfDevBleTendre['Year'] == int_dates[1]) & (dfDevBleTendre['Week'] <= 35))]
    
    dfDevBleDur = dfDev[dfDev['Culture'] == 'Blé dur']
    if datetime.now().year < int_dates[1]:
        dfBleDurMY = dfDevBleDur[(dfDevBleDur['Year'] == int_dates[0]) & (dfDevBleDur['Week'] >= 36)]
    else :
        dfBleDurMY = dfDevBleDur[((dfDevBleDur['Year'] == int_dates[0]) & (dfDevBleDur['Week'] >= 36)) | ((dfDevBleDur['Year'] == int_dates[1]) & (dfDevBleDur['Week'] <= 35))]

    dfDevMais = dfDev[dfDev['Culture'] == 'Maïs grain']
    if datetime.now().year < int_dates[1]:
        dfMaisMY = pd.DataFrame()
    else :
        dfMaisMY = dfDevMais[(dfDevMais['Year'] == int_dates[1]) & ((dfDevMais['Week'] >= 2) & (dfDevMais['Week'] <= 49))]

    df = pd.concat([dfBleTendreMY, dfMaisMY, dfBleDurMY])
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
    aggregated_stats_cereales = aggregated_stats[(aggregated_stats['Culture'] == 'Blé tendre') | (aggregated_stats['Culture'] == 'Blé dur')]
    start_date_cereales = np.where(
        aggregated_stats_cereales['Week'] >= 36,
        pd.to_datetime(f'{int_dates[0]}-01-01'),  # Use int_dates[0] if Week >= 36
        pd.to_datetime(f'{int_dates[1]}-01-01')   # Use int_dates[1] if Week < 36
    )

    # Add timedelta to calculate the Date column
    aggregated_stats_cereales['Date'] = start_date_cereales + pd.to_timedelta(aggregated_stats_cereales['Week'], unit="w")
    aggregated_stats_cereales = pd.concat([aggregated_stats_cereales[aggregated_stats_cereales['Week'] >= 36], aggregated_stats_cereales[aggregated_stats_cereales['Week'] <= 35]]).reset_index(drop=True)


    aggregated_stats_mais = aggregated_stats[aggregated_stats['Culture'] == 'Maïs grain']

    # Add timedelta to calculate the Date column
    aggregated_stats_mais['Date'] = pd.to_datetime(f'{int_dates[1]}-01-01') + pd.to_timedelta(aggregated_stats_mais['Week'], unit="w")
    #merged = pd.merge(aggregated_stats, df, on=['Culture', 'Week'], how='left')

    response = {
        'Data': df.to_json(orient='values'),
        'MeanCereales': aggregated_stats_cereales.to_json(orient='values'),
        'MeanMais': aggregated_stats_mais.to_json(orient='values'),
    }
    return response

@app.route("/condition")
def condition():
    
    return render_template('condition.html')

@app.route('/process_cond', methods=['POST', 'GET'])
def process_cond():
    cursorDev = db.get_database_dev_cond().find({
        "Year": {
        "$gte": datetime.now().year - 7
    }
    })
    df = pd.DataFrame(list(cursorDev)).sort_values(by='Date', ascending=True) 
    df = df.drop('_id', axis=1)
    df = df[df['Région'] == 'Moyenne France']
    df = df[['Culture', 'Date', 'Semaine', 'Week', 'Year', 'Très mauvaises', 'Mauvaises', 'Assez bonnes', 'Bonnes', 'Très bonnes']]
    dfMoy = df[df['Year'] < datetime.now().year - 1]

    df['MarketYear'] = df.apply(get_market_year, axis=1)
    dfMaisMY = df[(df['Culture'] == 'Maïs grain') & (df['Week']>=9)]
    dfBleTendreMY = df[df['Culture'] == 'Blé tendre']
    dfBleDurMY = df[df['Culture'] == 'Blé dur']

    df = pd.concat([dfBleTendreMY, dfMaisMY, dfBleDurMY])
    df['BonneEtTresBonnes'] = df['Bonnes'] + df['Très bonnes']

    dfMoy['BonnesEtTresBonnes'] = dfMoy['Bonnes'] + dfMoy['Très bonnes']
    aggregated_stats = dfMoy.groupby(['Culture', 'Week']).agg({
        'Très mauvaises': 'mean',
        'Mauvaises': 'mean',
        'Assez bonnes': 'mean',
        'Bonnes': 'mean',
        'Très bonnes': 'mean',
        'BonnesEtTresBonnes': 'mean'
    }).reset_index()
    aggregated_stats = aggregated_stats.rename(columns={'Très mauvaises': 'Très mauvaises Mean', 'Mauvaises': 'Mauvaises Mean', 'Assez bonnes': 'Assez bonnes Mean', 'Bonnes': 'Bonnes Mean', 'Très bonnes': 'Très bonnes Mean', 'BonnesEtTresBonnes': 'BonnesEtTresBonnes Mean'})
    merged = pd.merge(df, aggregated_stats, on=['Culture', 'Week'], how='inner').sort_values(by='Date')
    return merged.to_json(orient='values')

@app.route("/surfrendprod", methods=['GET', 'POST'])
def surfrendprod():
    df = pd.read_csv('static/files/SCR-GRC-hist_dep_surface_prod_cult_cer-A24.csv', encoding='ISO-8859-1', delimiter=';', decimal=',')
    years = sorted(df['ANNEE'].unique(), reverse=True)
    produits = ['Blé tendre', 'Maïs (grain et semence)', 'Colza']
    renderType = ['CULT_SURF', 'CULT_REND', 'CULT_PROD']
    
    imgProduct = []
    for produit in produits:
        imgStringList = []
        if request.method == "POST":
            postResponse = request.get_json()['Date']
            data = produce_data(df, produit, int(postResponse))
        else:
            data = produce_data(df, produit, years[0])
        for rType in renderType:
            img = produce_map(data, rType)
            imgStringList.append(img)
        imgProduct.append({'Produit': produit, 'imgs': imgStringList})

    if request.method == "POST":
        return imgProduct
    else: 
        return render_template('surfrendprod.html', years=years, img=imgProduct) 
    

def produce_data(df, produit, year):
    df['ESPECES'] = df['ESPECES'].str.rstrip()
    df['DEP'] = df['DEP'].str.rstrip()
    df = df[(df['ANNEE'] == year) & (df['ESPECES'] == produit)]
    df = df[['DEP', 'CULT_SURF', 'CULT_REND', 'CULT_PROD']]
    corsica = df[(df['DEP'] == '2A') | (df['DEP'] == '2B')]
    corsicaSurf = corsica['CULT_SURF'].sum()
    corsicaProd = corsica['CULT_PROD'].sum()
    corsicaRend = corsica['CULT_REND'].mean()
    newCorsica = pd.DataFrame({
        'DEP': ['20'],
        'CULT_SURF': [corsicaSurf],
        'CULT_REND': [corsicaRend],
        'CULT_PROD': [corsicaProd]
    })
    df = pd.concat([df, newCorsica]).reset_index(drop=True)
    df = df[~df['DEP'].isin(['2A', '2B'])]
    df['DEP'] = df['DEP'].astype(int)
    departments = gpd.read_file('static/files/geojsonfrance_corse_20.json')[['code', 'geometry']]
    departments['code'] = departments['code'].astype(int)
    final_df = departments.merge(df, how='left', left_on='code', right_on='DEP')
    final_df['DEP'] = final_df['DEP'].fillna(final_df['code'])
    final_df = final_df.fillna(0)
    final_df['DEP'] = final_df['DEP'].astype(int)

    return final_df

def produce_map(produced_data, typeCult):
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    extent = [-5, 10, 41, 52]
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS)
            
    produced_data.plot(column=typeCult, ax=ax)

    cmap = mpl.cm.cool
    norm = mpl.colors.Normalize(vmin=produced_data[typeCult].min(), vmax=produced_data[typeCult].max())
    fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation='horizontal', label='Some Units')
    
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    img = f"<img src='data:image/png;base64,{data}' class='img-fluid'/>"
    return img

@app.route('/cot/<filename>')
def download_cot(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/files'), filename, as_attachment=True)

@app.route("/arome-anomaly")
def arome():
    return render_template('arome.html')