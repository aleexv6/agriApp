import pandas as pd
import numpy as np

def select_futures(df, ticker, years=None):
    if years:
        df = df[(df['Ticker'] == ticker) & ((df['Date'].dt.year >= years[0]) & (df['Date'].dt.year <= years[1]))]
    else: 
        df = df[(df['Ticker'] == ticker)]
    return df.reset_index(drop=True)


def normalize_years(df):
    # Create a copy to avoid modifying the original DataFrame
    result = df.copy()
    
    # For each Expiration group
    for name, group in df.groupby('Expiration'):
        # Get unique years and create a mapping to normalized years
        unique_years = group['Date'].dt.year.unique()
        year_mapping = dict(zip(unique_years, range(2000, 2000 + len(unique_years))))

        # Create mask for this group
        group_mask = result['Expiration'] == name
        
        # Apply the year transformation
        result.loc[group_mask, 'Date'] = result.loc[group_mask, 'Date'].apply(
            lambda x: x.replace(year=year_mapping[x.year])
        )
    
    return result

def getContractSeasonality(dfFutures, ticker, contractMonth, expiStartYear):
    dfFutures['Date'] = pd.to_datetime(dfFutures['Date'])
    dfFutures.loc[:, 'Expiration Month'] = dfFutures['Expiration'].str[:3]
    dfFutures.loc[:, 'Expiration Year'] = dfFutures['Expiration'].str[3:].astype(int)
    df = select_futures(dfFutures, ticker)
    df = df[(df['Expiration Month'] == contractMonth) & (df['Expiration Year'] >= expiStartYear)]        

    pctChange = df.groupby('Expiration')['Close'].pct_change()
    df.loc[:,'Percent Change'] = pctChange * 100
    cumSumPctChange = df.groupby('Expiration')['Percent Change'].cumsum()
    df.loc[:,'CumulativePercentChange'] = cumSumPctChange

    df = df[~((df['Date'].dt.month == 2) & (df['Date'].dt.day == 29))].reset_index(drop=True) #remove 02/29 for leap year
    df = normalize_years(df)
    df = df.replace({np.nan: None})
    
    dataList = []
    for expi in df['Expiration'].unique():
        tmp = df[df['Expiration'] == expi]
        dataList.append({'Expiration' : expi, 'data': tmp[['Date', 'CumulativePercentChange']].to_dict()})
    return dataList