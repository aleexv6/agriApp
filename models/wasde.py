import db.database as db
import pandas as pd
from datetime import date

COMMODITIES = ['Corn', 'Wheat', 'Oilseed, Soybean']
REPORTTITLE = ['U.S. Feed Grain and Corn Supply and Use', 'World Corn Supply and Use',
                'U.S. Soybeans and Products Supply and Use (Domestic Measure)', 'World Soybean Supply and Use',
                'U.S. Wheat Supply and Use', 'World Wheat Supply and Use']
FLAGS = ['Proj.', 'Est.', '(Proj.)', '(Est.)']

ATTRIBUTE_COMMODITY_MAP = {
    'Corn': {'US': 'U.S. Feed Grain and Corn Supply and Use',
             'World': 'World Corn Supply and Use'},
    'Wheat': {'US': 'U.S. Wheat Supply and Use',
             'World': 'World Wheat Supply and Use'},
    'Oilseed, Soybean': {'US': 'U.S. Soybeans and Products Supply and Use (Domestic Measure)',
             'World': 'World Soybean Supply and Use'}
}

CURSOR = db.get_database_wasde().find({ #db call with properties to extract only what is needed
                "ForecastYear": {
                "$gte": date.today().year - 5,
                "$lte": date.today().year
                },
                "Commodity": {
                    "$in": COMMODITIES
                },
                "ReportTitle": {
                    "$in": REPORTTITLE
                },
                "ProjEstFlag": {
                    "$in": FLAGS
                }
            }, {'_id': 0})
DF = pd.DataFrame(list(CURSOR)).sort_values(by=['ForecastYear', 'ForecastMonth'], ascending=True) #df sorted 

def normalize_years(df):
    result = df.copy() #copy df
    
    for name, group in df.groupby('MarketYear'): #for each marketyear
        unique_years = group['ReleaseDate'].dt.year.unique() #get unique years and create a mapping to normalized years
        year_mapping = dict(zip(unique_years, range(2000, 2000 + len(unique_years)))) #mapping
        group_mask = result['MarketYear'] == name # create mask for this group
        
        result.loc[group_mask, 'FakeDate'] = result.loc[group_mask, 'ReleaseDate'].apply( #apply changes
            lambda x: x.replace(year=year_mapping[x.year])
        )
    return result
def find_wasde(attribute, commodity, region='US', df=DF):
    df['ReleaseDate'] = pd.to_datetime(df['ReleaseDate'])
    df = df[df['ReleaseDate'] >= pd.to_datetime(f"{date.today().year - 5}-05-01")].reset_index(drop=True) #keep only last five years time released date

    dataList = []
    for my in df['MarketYear'].unique()[1:]: #we skip first MY it is always non complete
        tmp = df[(df['MarketYear'] == my) & (df['Attribute'] == attribute) & (df['Commodity'] == commodity) & (df['ReportTitle'] == ATTRIBUTE_COMMODITY_MAP[commodity][region])] #filter df
        nextDate = pd.to_datetime(f"{tmp['ReleaseDate'].iloc[0].year}-{tmp['ReleaseDate'].iloc[0].month}-01") + pd.DateOffset(months=17) #filter to keep values from MAY to September + 1
        tmp = tmp[tmp['ReleaseDate'] < nextDate]
        dataList.append(tmp)
    data = pd.concat(dataList)
    data = normalize_years(data)
    return data

def get_commodity_attributes(df=DF):
    attrList = []
    for commodity in COMMODITIES:
        attrUs = df[(df['Commodity'] == commodity) & (df['ReportTitle'] == ATTRIBUTE_COMMODITY_MAP[commodity]['US'])]['Attribute'].unique().tolist()
        attrWorld = df[(df['Commodity'] == commodity) & (df['ReportTitle'] == ATTRIBUTE_COMMODITY_MAP[commodity]['World'])]['Attribute'].unique().tolist()
        attrList.append({'Produit': commodity, 'Attributes': {'US': attrUs, 'World': attrWorld}})
    return attrList