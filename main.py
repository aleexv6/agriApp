from flask import Flask, render_template, request, send_from_directory
import database as db
import pandas as pd
from cot import format_data_euronext, net_position_euronext, get_cot_from_db_euronext, seasonality_euronext, variation_euronext
import warnings
import requests
from datetime import datetime, date, timedelta
import numpy as np
import os
import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import matplotlib as mpl
import config

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
        if 2 <= week <= 49:
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

def dev(produits, stadeDevBle, stadeDevMais, statsStadeDevBle, statsStadeDevMais, marketYear=None):
    if marketYear:
        cursorDev = db.get_database_dev_cond().find({
            "Year": {
            "$gte": int(marketYear.split('/')[0]) - 6,
            "$lte": int(marketYear.split('/')[1])
            },
            "Culture": {
                "$in": produits
            },
            "Région": "Moyenne France"
        }, {'_id': 0})
    else:
        cursorDev = db.get_database_dev_cond().find({
            "Year": {
            "$gte": date.today().year - 6,
            },
            "Culture": {
                "$in": produits
            },
            "Région": "Moyenne France"
        }, {'_id': 0})
    df = pd.DataFrame(list(cursorDev)).sort_values(by='Date', ascending=True)
    df['MarketYear'] = df.apply(get_market_year, axis=1) #apply function to get marketyear
    uniqueMY = df['MarketYear'].unique()[1:]
    if marketYear:
        dfCurrent = df[df['MarketYear'] == marketYear]
        reversedUniqueMY = uniqueMY[:-1][::-1]
    else:
        reversedUniqueMY = uniqueMY[::-1]
        dfCurrent = df[df['MarketYear'] == reversedUniqueMY[0]]

    dfCurrent = dfCurrent.replace(np.nan, None)
    dfCurrent['epoch'] = dfCurrent['Date'].apply(lambda x: x.timestamp()) * 1000 #timestamp to milliseconds
    prodList = []
    for produit in produits:
        devList = []
        dfProduit = dfCurrent[dfCurrent['Culture'] == produit]
        if (produit == 'Blé tendre') | (produit == 'Blé dur'):
            stade = stadeDevBle
        else:
            stade = stadeDevMais
        for dev in stade:
            devList.append({'Dev': dev, 'Data': [[timestamp, value] for timestamp, value in zip(dfProduit['epoch'].to_list(), dfProduit[dev].to_list())]})
        prodList.append({'Produit': produit, 'Stade': devList})

    #stats
    dfStats = df[df['MarketYear'].isin(reversedUniqueMY[1:-1])]
    statsMY = dfStats['MarketYear'].unique()
    aggregated_stats = dfStats.groupby(['Culture', 'Week']).agg({
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
    aggregated_stats = pd.merge(df, aggregated_stats, on=['Culture', 'Week'], how='inner').sort_values(by='Date') #here we merge on df to align the data on the week (easier)
    aggregated_stats = aggregated_stats[aggregated_stats['MarketYear'] == statsMY[-2]]
    aggregated_stats_cereales = aggregated_stats[(aggregated_stats['Culture'] == 'Blé tendre') | (aggregated_stats['Culture'] == 'Blé dur')]
    if marketYear:
        start_date_cereales = np.where(
            aggregated_stats_cereales['Week'] >= 36,
            pd.to_datetime(f'{marketYear.split("/")[0]}-01-01'),  # Use int_dates[0] if Week >= 36
            pd.to_datetime(f'{marketYear.split("/")[1]}-01-01')   # Use int_dates[1] if Week < 36
        )
    else:
        start_date_cereales = np.where(
            aggregated_stats_cereales['Week'] >= 36,
            pd.to_datetime(f'{reversedUniqueMY[0].split("/")[0]}-01-01'),  # Use int_dates[0] if Week >= 36marketYear
            pd.to_datetime(f'{reversedUniqueMY[0].split("/")[1]}-01-01')   # Use int_dates[1] if Week < 36
        )
    aggregated_stats_cereales['Date'] = start_date_cereales + pd.to_timedelta(aggregated_stats_cereales['Week'], unit="w")

    aggregated_stats_mais = aggregated_stats[aggregated_stats['Culture'] == 'Maïs grain']
    if marketYear:
        aggregated_stats_mais['Date'] = pd.to_datetime(f'{marketYear.split("/")[1]}-01-01') + pd.to_timedelta(aggregated_stats_mais['Week'], unit="w")
    else:
        aggregated_stats_mais['Date'] = pd.to_datetime(f'{reversedUniqueMY[0].split("/")[1]}-01-01') + pd.to_timedelta(aggregated_stats_mais['Week'], unit="w")
    
    fullStats = pd.concat([aggregated_stats_cereales, aggregated_stats_mais])
    fullStats = fullStats.replace(np.nan, None)
    fullStats['epoch'] = fullStats['Date'].apply(lambda x: x.timestamp()) * 1000

    statsProdList = []
    for produit in produits:
        statsDevList = []
        dfProduit = fullStats[fullStats['Culture'] == produit]
        if (produit == 'Blé tendre') | (produit == 'Blé dur'):
            stade = statsStadeDevBle
        else:
            stade = statsStadeDevMais
        for dev in stade:
            statsDevList.append({'Dev': dev, 'Parent': dev.split("_")[0], 'Data': [[timestamp, value] for timestamp, value in zip(dfProduit['epoch'].to_list(), dfProduit[dev].to_list())]})
        statsProdList.append({'Produit': produit, 'Stade': statsDevList})

    return {'prodList': prodList, 'statsProdList': statsProdList, 'MarketYear': reversedUniqueMY.tolist()}

listProductFutures = {'Ble tendre':'EBM', 'Mais':'EMA', 'Colza':'ECO', 'Ble dur':'EDW'} #set a futures ticker for every product name

#initalize data that we use in a lot of pages here
cursorPhysique = db.get_database_physical().find({}, {'_id': 0})#get data from db removing id column
dfPhysique = pd.DataFrame(list(cursorPhysique)).sort_values(by='Date', ascending=True).reset_index(drop=True)#put data in df for sorting on date and reindexing
cursorFutures = db.get_database_new_euronext().find({}, {'_id': 0})#get data from db removing id column
dfFutures = pd.DataFrame(list(cursorFutures)).sort_values(by='Date', ascending=True).reset_index(drop=True)#put data in df for sorting on date and reindexing
dfFutures['Expiration Full Date'] = dfFutures[['Ticker', 'Expiration']].apply(full_expiration_date, axis=1)
sampleFutures = dfFutures.tail(100).sort_values(by='Expiration Full Date').reset_index(drop=True) #sample 100 last values (to avoid sorting full df) to sort expiration date by date

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
    dfFutures = dfFutures[dfFutures['Expiration Full Date'] > date.today()] #show data that are not expired
    dfFutures = dfFutures.replace('-', 0) #in case of change of contract sometimes volume is set at -
    dfFutures = dfFutures.fillna(0) #fill nan for JSON compatibility
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
    lastDate = dfFutures.iloc[-1]['Date']
    baseSelector = []
    for produit in sorted(dfPhysique['Produit'].unique()): #sort product to have always same order
        if produit != 'Ble dur': #remove ble dur we do not have futures
            place = sorted(list(dfPhysique[dfPhysique['Produit'] == produit]['Place'].unique())) #keep unique places for this product, sorted to always have same order
            ticker = listProductFutures[produit] #use dict to get futures ticker from product
            expi = list(sampleFutures[(sampleFutures['Ticker'] == ticker) & (sampleFutures['Expiration Full Date'] > date.today())]['Expiration'].unique()) #get expiration for the productn sorted by expiration date
            baseSelector.append({'Produit': produit, 'Place':place, 'Expi':expi})

    return render_template('basis.html', lastDate=lastDate, baseSelector=baseSelector)

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
    lastDate = dfFutures.iloc[-1]['Date']
    spreadSelector = []
    for ticker in sorted(dfFutures['Ticker'].unique()): #loop throught unique tickers in df sorted alphabeticaly
        expi = list(sampleFutures[(sampleFutures['Ticker'] == ticker) & (sampleFutures['Expiration Full Date'] > date.today())]['Expiration'].unique()) #get expiration for the product sorted by expiration date
        spreadSelector.append({'Ticker': ticker, 'Expi': expi})
    first2ebmExpi = [item['Expi'] for item in spreadSelector if item['Ticker'] == 'EBM'][0][:2]
    firstLeg = dfFutures[(dfFutures['Ticker'] == 'EBM') & (dfFutures['Expiration'] == first2ebmExpi[0])][['Date', 'Ticker', 'Expiration', 'Close']]
    secondLeg = dfFutures[(dfFutures['Ticker'] == 'EBM') & (dfFutures['Expiration'] == first2ebmExpi[1])][['Date', 'Ticker', 'Expiration', 'Close']]
    spreadDf = pd.merge(firstLeg, secondLeg, on=['Date', 'Ticker'], how='inner') #x is firstleg, y is second leg
    spreadDf['Spread'] = spreadDf['Close_x'] - spreadDf['Close_y'] #spread calculation
    spreadDf = spreadDf[['Date', 'Spread']] #keep interesting values
    json_string = spreadDf.to_json(orient='values') #return json string
    return render_template('spread.html', lastDate=lastDate, dfFutures=dfFutures, spreadSelector=spreadSelector, data=json_string)
    
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
    dfFutures = dfFutures[dfFutures['Expiration Full Date'] > date.today()] #show data that are not expired
    lastFuturesDate = dfFutures.iloc[-1]['Date'] #get last date from df
    lastFutures = dfFutures[dfFutures['Date'] == lastFuturesDate] #filter on last date
    lastFutures = lastFutures.sort_values(by='Expiration Full Date').reset_index(drop=True) #sort by expiration date
    for ticker in sorted(lastFutures['Ticker'].unique()): #loop through unique tickers 
        data = {'Ticker': ticker, 'Expirations': list(lastFutures[lastFutures['Ticker'] == ticker]['Expiration']), 'Prix': list(lastFutures[lastFutures['Ticker'] == ticker]['Close'])} #create data for ticker, expis and prices
        curveData.append(data)    
    return render_template('curve.html', curveData=curveData)

@app.route("/saisonnalite")
def saisonnalite(dfFutures=dfFutures):
    todayofyear = pd.to_datetime(date.today().strftime('%Y-%m-%d')).dayofyear # get day of year to print on chart
    lst = []
    for _, ticker in listProductFutures.items(): #loop through futures tickers
        if ticker != 'EDW': #we remove EDW we do not have data
            dfFuturesProduct = dfFutures[dfFutures['Ticker'] == ticker] #filter on current ticker
            dfFuturesProduct['Date'] = pd.to_datetime(dfFuturesProduct['Date']) #set as type date
            dfFuturesProduct = dfFuturesProduct[(dfFuturesProduct['Date'].dt.year > 2003) & (dfFuturesProduct['Date'].dt.year < date.today().year)] #filter data from 2003 to current year -1
            dfFuturesProduct = dfFuturesProduct[~((dfFuturesProduct['Date'].dt.month == 2) & (dfFuturesProduct['Date'].dt.day == 29))] #remove 02/29 for leap year
            dfFuturesProduct = dfFuturesProduct.reset_index(drop=True)
            dfFuturesProduct = dfFuturesProduct.set_index(['Date', 'Expiration'])

            rollingContractsPctChange = dfFuturesProduct.groupby('Expiration')['Close'].pct_change() * 100 #groupby expi and percent change for each contracts
            rollingContractsPctChange.name = 'Percent Change'
            continuous = pd.merge(dfFuturesProduct, rollingContractsPctChange, left_index=True, right_index=True) #merge new data on df
            continuous = continuous.reset_index()

            continuousOI = continuous.loc[continuous.groupby('Date')['Open Interest'].idxmax()] #filter on contract with largest Open interest to have the one infront
            continuousOI['Year'] = continuousOI['Date'].dt.year
            continuousOI = continuousOI.set_index('Date')

            yearly_cumulative_percentage_change = continuousOI.groupby("Year")["Percent Change"].cumsum() #groupby year and cumsum on full year to have each day represent the cummulative % change  
            filled_series = yearly_cumulative_percentage_change.reindex(pd.date_range(start=yearly_cumulative_percentage_change.index.min(), end=yearly_cumulative_percentage_change.index.max())) #fill series with dates that are not present
            filled_series.loc[(filled_series.index.month == 1) & (filled_series.index.day == 1)] = 0 #set value to 0 for first days of year that have been set
            filled_series = filled_series.ffill().fillna(0) #fill with last know value or 0 if no know values

            median_cumulative_percentage_change = filled_series.groupby(filled_series.index.dayofyear).median() #groupby day of year and median the values
            if 366 in median_cumulative_percentage_change.index:
                median_cumulative_percentage_change = median_cumulative_percentage_change.drop(index=366) #remove the value if dayofyear is 366
            
            median_cumulative_percentage_change = median_cumulative_percentage_change.round(2) #round it

            lst.append({'Ticker': ticker, 'Cumulative': median_cumulative_percentage_change.to_dict()}) #append to list to send to front

    return render_template('saisonnalite.html', data=lst, dayofyear=todayofyear)

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

@app.route("/developpement", methods=['POST', 'GET'])
def developpement():
    produits = ['Blé tendre', 'Blé dur', 'Maïs grain'] # set the products
    stadeDevBle = ['Semis', 'Levée', 'Début tallage', 'Épi 1 cm', '2 noeuds', 'Épiaison', 'Récolte']
    stadeDevMais = ['Semis', 'Levée', '6/8 feuilles visibles', 'Floraison femelle', 'Humidité du grain 50%', 'Récolte']
    statsStadeDevBle = ['Semis_mean', 'Semis_min', 'Semis_max', 'Levée_mean', 'Levée_min', 'Levée_max', 'Début tallage_mean', 'Début tallage_min', 'Début tallage_max', 'Épi 1 cm_mean', 'Épi 1 cm_min', 'Épi 1 cm_max', '2 noeuds_mean', '2 noeuds_min', '2 noeuds_max', 'Épiaison_mean', 'Épiaison_min', 'Épiaison_max', 'Récolte_mean', 'Récolte_min', 'Récolte_max']
    statsStadeDevMais = ['Semis_mean', 'Semis_min', 'Semis_max', 'Levée_mean', 'Levée_min', 'Levée_max', '6/8 feuilles visibles_mean', '6/8 feuilles visibles_min', '6/8 feuilles visibles_max', 'Floraison femelle_mean', 'Floraison femelle_min', 'Floraison femelle_max', 'Humidité du grain 50%_mean', 'Humidité du grain 50%_min', 'Humidité du grain 50%_max', 'Récolte_mean', 'Récolte_min', 'Récolte_max']

    if request.method == "POST":
        marketingYear = request.get_json()['Marketing_year']
        developpement = dev(produits, stadeDevBle, stadeDevMais, statsStadeDevBle, statsStadeDevMais, marketingYear)
    else:
        developpement = dev(produits, stadeDevBle, stadeDevMais, statsStadeDevBle, statsStadeDevMais)

    return render_template('developpement.html', marketYear=developpement['MarketYear'], data=developpement['prodList'], statsData=developpement['statsProdList'], stadeDevBle=stadeDevBle, stadeDevMais=stadeDevMais)

@app.route("/process_dev", methods=['POST', 'GET'])
def process_dev():
    produits = ['Blé tendre', 'Blé dur', 'Maïs grain'] # set the products
    stadeDevBle = ['Semis', 'Levée', 'Début tallage', 'Épi 1 cm', '2 noeuds', 'Épiaison', 'Récolte']
    stadeDevMais = ['Semis', 'Levée', '6/8 feuilles visibles', 'Floraison femelle', 'Humidité du grain 50%', 'Récolte']
    statsStadeDevBle = ['Semis_mean', 'Semis_min', 'Semis_max', 'Levée_mean', 'Levée_min', 'Levée_max', 'Début tallage_mean', 'Début tallage_min', 'Début tallage_max', 'Épi 1 cm_mean', 'Épi 1 cm_min', 'Épi 1 cm_max', '2 noeuds_mean', '2 noeuds_min', '2 noeuds_max', 'Épiaison_mean', 'Épiaison_min', 'Épiaison_max', 'Récolte_mean', 'Récolte_min', 'Récolte_max']
    statsStadeDevMais = ['Semis_mean', 'Semis_min', 'Semis_max', 'Levée_mean', 'Levée_min', 'Levée_max', '6/8 feuilles visibles_mean', '6/8 feuilles visibles_min', '6/8 feuilles visibles_max', 'Floraison femelle_mean', 'Floraison femelle_min', 'Floraison femelle_max', 'Humidité du grain 50%_mean', 'Humidité du grain 50%_min', 'Humidité du grain 50%_max', 'Récolte_mean', 'Récolte_min', 'Récolte_max']

    if request.method == "POST":
        marketingYear = request.get_json()['Marketing_year']
        developpement = dev(produits, stadeDevBle, stadeDevMais, statsStadeDevBle, statsStadeDevMais, marketingYear)

    return [developpement['prodList'], developpement['statsProdList']]

@app.route("/condition")
def condition():
    produits = ['Blé tendre', 'Blé dur', 'Maïs grain'] # set the products
    cursorDev = db.get_database_dev_cond().find({ #find data from db 
        "Year": {
        "$gte": datetime.now().year - 7
    }
    }, {'_id': 0})
    df = pd.DataFrame(list(cursorDev)).sort_values(by='Date', ascending=True) #make it a df ordered by date 
    df = df[df['Région'] == 'Moyenne France'] #filter on Moyenne France only
    df = df[['Culture', 'Date', 'Semaine', 'Week', 'Year', 'Très mauvaises', 'Mauvaises', 'Assez bonnes', 'Bonnes', 'Très bonnes']] #filter on wanted columns
    dfMoy = df[df['Year'] < datetime.now().year - 1] #select a portion of the df and make it another df for stats

    df['MarketYear'] = df.apply(get_market_year, axis=1) #apply function to get marketyear

    productLst = [] #we are making the list of dict for returning data to view
    for produit in produits: #loop throught products
        dfProduit = df[df['Culture'] == produit] #select wanted product
        dfProduit = dfProduit.reset_index(drop=True)
        MYLst = []
        for year in dfProduit['MarketYear'].unique(): #now loop through each marketyear
            dfMY = dfProduit[dfProduit['MarketYear'] == year] #filter on MY
            dfMY[['Bonnes', 'Très bonnes']] = dfMY[['Bonnes', 'Très bonnes']].fillna(0) #set NaN to 0 for calculation
            dfMY['BonneEtTresBonnes'] = dfMY['Bonnes'] + dfMY['Très bonnes'] #add bonnes and très bonnes values 
            dfMY = dfMY.replace({np.nan: None}) #if some nan left we replace for JSON compatibility
            dfMY = dfMY.replace({0: None}) #Replace 0 with None for JSON compatibility
            MYLst.append({'Year': year, 'Data': dfMY.to_dict()}) #append the dict to the list of dict
        productLst.append({'Produit': produit, 'MYs': MYLst}) #append the datas to a list of dict of each product

    #Basically doing the same but for the stats dataframe (Mean of 5 last years)
    dfMoy[['Bonnes', 'Très bonnes']] = dfMoy[['Bonnes', 'Très bonnes']].fillna(0)
    dfMoy['BonnesEtTresBonnes'] = dfMoy['Bonnes'] + dfMoy['Très bonnes']
    dfMoy = dfMoy.replace(0, np.nan)
    aggregated_stats = dfMoy.groupby(['Culture', 'Week']).agg({
        'Très mauvaises': 'mean',
        'Mauvaises': 'mean',
        'Assez bonnes': 'mean',
        'Bonnes': 'mean',
        'Très bonnes': 'mean',
        'BonnesEtTresBonnes': 'mean'
    }).reset_index()
    aggregated_stats = aggregated_stats.rename(columns={'BonnesEtTresBonnes': 'BonnesEtTresBonnesMean'})    
    aggregated_stats = pd.merge(df, aggregated_stats, on=['Culture', 'Week'], how='inner').sort_values(by='Date')[['Culture', 'Week', 'MarketYear', 'BonnesEtTresBonnesMean']] #here we merge on df to align the data on the week (easier)
    lastMY = aggregated_stats['MarketYear'].unique()[-3] #we choose a middle of MarketYear to keep only one year of stats

    aggregateLst = []
    for produit in produits:        
        dfProduitAgg = aggregated_stats[(aggregated_stats['Culture'] == produit) & (aggregated_stats['MarketYear'] == lastMY)] #filter on product and choosed MY
        dfProduitAgg = dfProduitAgg.reset_index(drop=True)
        dfProduitAgg = dfProduitAgg.replace({np.nan: None})
        aggregateLst.append({'Produit': produit, 'stats': dfProduitAgg.to_dict()}) #make the list of dict

    return render_template('condition.html', data=productLst, stats=aggregateLst)

@app.route("/surfrendprod", methods=['GET', 'POST'])
def surfrendprod():
    df = pd.read_csv(config.SURFRENDPROD_URL, encoding='ISO-8859-1', delimiter=';', decimal=',') #read surf,rend,prod file
    years = sorted(df['ANNEE'].unique(), reverse=True) #get every years in descending order
    produits = ['Blé tendre', 'Maïs (grain et semence)', 'Colza'] #products to filter
    renderType = ['CULT_SURF', 'CULT_REND', 'CULT_PROD'] #type to filter
    
    imgProduct = []
    for produit in produits: #loop through products
        imgStringList = []
        if request.method == "POST": #if we sent a poste (meaning we changed the date)
            postResponse = request.get_json()['Date'] #get the wanted date from response
            data = produce_data(df, produit, int(postResponse)) #make data for this date
            for rType in renderType: #loop through each type
                img = produce_map(data, rType, produit, int(postResponse)) #produce the map
                imgStringList.append(img) #append img string to list of string
        else: #if we have get (first load of page)
            data = produce_data(df, produit, years[0]) #data for the first year of years, meaning most recent year
            for rType in renderType:
                img = produce_map(data, rType, produit, years[0]) #data for most recent year
                imgStringList.append(img)        
        imgProduct.append({'Produit': produit, 'imgs': imgStringList}) #make a list of dict with data

    if request.method == "POST":
        return imgProduct #if we are post we just have to send data to front 
    else: 
        return render_template('surfrendprod.html', years=years, img=imgProduct) 

def produce_data(df, produit, year):
    df['ESPECES'] = df['ESPECES'].str.rstrip() #remove spaces
    df['DEP'] = df['DEP'].str.rstrip() #remove spaces
    df = df[(df['ANNEE'] == year) & (df['ESPECES'] == produit)] #filter on year and product
    df = df[['DEP', 'CULT_SURF', 'CULT_REND', 'CULT_PROD']] #keep essential data
    #corsica is two departements but here we will make it one
    corsica = df[(df['DEP'] == '2A') | (df['DEP'] == '2B')] #filter corsica
    corsicaSurf = corsica['CULT_SURF'].sum()
    corsicaProd = corsica['CULT_PROD'].sum()
    corsicaRend = corsica['CULT_REND'].mean()
    newCorsica = pd.DataFrame({ #make a df with new values
        'DEP': ['20'],
        'CULT_SURF': [corsicaSurf],
        'CULT_REND': [corsicaRend],
        'CULT_PROD': [corsicaProd]
    })
    df = pd.concat([df, newCorsica]).reset_index(drop=True) #concat new corsica data
    df = df[~df['DEP'].isin(['2A', '2B'])] #then remove the two corsican departements
    df['DEP'] = df['DEP'].astype(int) #set as int to merge
    departments = gpd.read_file(config.GEOJSON_URL)[['code', 'geometry']] #find geometry data for each departement
    departments['code'] = departments['code'].astype(int) #set as int for merge
    final_df = departments.merge(df, how='left', left_on='code', right_on='DEP') #merge geometry and df
    final_df['DEP'] = final_df['DEP'].fillna(final_df['code']) #fill na with code if we dont have value for dep (can happen)
    final_df = final_df.fillna(0) #fill rest of values with 0
    final_df['DEP'] = final_df['DEP'].astype(int) #set as int

    return final_df

def produce_map(produced_data, typeCult, produit, year):
    typeCultLegend= { #for legend
        'CULT_SURF': 'Surface (ha)',
        'CULT_REND': 'Rendement (t/ha)',
        'CULT_PROD': 'Production (tonnes)'
    }
    typeCultTitle= { #for title
        'CULT_SURF': 'surface',
        'CULT_REND': 'rendement',
        'CULT_PROD': 'production'
    }
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': ccrs.PlateCarree()}) #initialize fig axe
    extent = [-5, 10, 41, 52] #to be centered on france
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS)
            
    cmap = mpl.cm.YlGn #cmap color
    norm = mpl.colors.Normalize(vmin=produced_data[typeCult].min(), vmax=produced_data[typeCult].max()) #map normalization

    produced_data.plot(column=typeCult, ax=ax, cmap=cmap, norm=norm) #plot data
    cbar = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation='horizontal', location='bottom', pad=0.04, shrink=0.70) #setup colorbar
    cbar.set_label(label=typeCultLegend[typeCult], size=14)
    plt.suptitle(f'{produit} {typeCultTitle[typeCult]} {year}', fontsize=18) #set title

    fig.tight_layout() 
    #prepare buffer to return an image link
    buf = BytesIO()
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

@app.route("/404")
def quatrecentquatre():
    return render_template('404.html')