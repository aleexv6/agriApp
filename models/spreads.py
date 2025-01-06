from datetime import date
import pandas as pd
import numpy as np

months = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
}

def pad_number(num):
    return f"0{num}" if num < 10 else str(num)

def select_futures(df, ticker, years=None):
    if years:
        df = df[(df['Ticker'] == ticker) & ((df['Date'].dt.year >= years[0]) & (df['Date'].dt.year <= years[1]))]
    else: 
        df = df[(df['Ticker'] == ticker) & (df['Date'].dt.year < date.today().year)]
    return df.reset_index(drop=True)

def getSpread(dfFutures, ticker, firstLegMonth, secondLegMonth, dataYears, expiYearMax):
    dfFutures['Date'] = pd.to_datetime(dfFutures['Date'])
    dfFutures.loc[:, 'Expiration Month'] = dfFutures['Expiration'].str[:3]
    dfFutures.loc[:, 'Expiration Year'] = dfFutures['Expiration'].str[3:].astype(int)
    dfFutures = dfFutures.sort_values(by=['Date', 'Expiration Year'], ascending=True).reset_index(drop=True)

    df = select_futures(dfFutures, ticker, dataYears)
    df = df[df['Expiration Year'] <= expiYearMax]

    dfMay = df[df['Expiration Month'] == firstLegMonth]
    dfSep = df[df['Expiration Month'] == secondLegMonth]

    merged = pd.merge(dfMay, dfSep, on=['Date'], how='inner').reset_index(drop=True)
    merged['Spread'] = merged['Close_x'] - merged['Close_y']
    merged = merged[['Date', 'Spread', 'Expiration_x', 'Expiration_y', 'Expiration Full Date_x', 'Expiration Year_x', 'Expiration Year_y']]


    dfList = []
    years = df['Expiration Year'].unique()[2:]
    for year in years - 1:
        if months[firstLegMonth] > months[secondLegMonth]:
            data = merged[(merged['Expiration_x'] == f'{firstLegMonth}{pad_number(year + 1)}') & (merged['Expiration_y'] == f'{secondLegMonth}{pad_number(year + 2)}')] #year +1 bc we want expiration of year and year +1
        else:
            data = merged[(merged['Expiration_x'] == f'{firstLegMonth}{pad_number(year + 1)}') & (merged['Expiration_y'] == f'{secondLegMonth}{pad_number(year + 1)}')] #year +1 bc we want expiration of year and year +1
        if not data.empty:
            data = data[data['Date'] >= (data['Expiration Full Date_x'].unique()[0] - pd.DateOffset(years=1))] #get 1 year spread from MAY to MAY (expiry)
            compteur = 0
            for i in data['Date'].dt.year.unique():
                mask = data['Date'].dt.year == i
                data.loc[mask, 'Date'] = data.loc[mask, 'Date'].apply(
                    lambda x: x.replace(year=2000 + compteur)
                    if x.month != 2 or x.day != 29
                    else x.replace(day=28, year=2000 + compteur)
                )
                compteur += 1
            dfList.append(data)
    dfSpread = pd.concat(dfList).reset_index(drop=True)
    dfSpread = dfSpread.replace({np.nan: None})

    spreadDict = []
    for expiYear in dfSpread['Expiration Year_x'].unique():
        tmp = dfSpread[dfSpread['Expiration Year_x'] == expiYear].reset_index(drop=True)
        spreadDict.append({'spreadYear': f"{tmp['Expiration_x'].iloc[0]} - {tmp['Expiration_y'].iloc[0]}", 'spreadData': tmp[['Date','Spread']].to_dict()})
    return spreadDict