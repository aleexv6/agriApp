import pandas as pd
import database as db
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import database as db
import yfinance as yf
import locale
name_cftc = {
    'M_Money': 'Managed Money',
    'Prod_Merc': 'Producer and Merchant',
    'Other_Rept': 'Other Reportable',
    'Swap': 'Swap'
}

cbot = {
    'ZC' : {
        'data': ['H24', 'K24', 'N24', 'U24', 'Z24'],
        'expiration': ['Mars 2024', 'Mai 2024', 'Juin 2024', 'Septembre 2024', 'Decembre 2024'], 
        'name': 'Maïs Futures'
    },
    'ZL' : {
        'data': ['H24', 'K24', 'N24', 'Q24', 'U24'],
        'expiration': ['Mars 2024', 'Mai 2024', 'Juin 2024', 'Aout 2024', 'Septembre 2024'],
        'name': 'Huile de soja Futures'    
    },
    'ZS' : {
        'data': ['H24', 'K24', 'N24', 'Q24', 'U24'],
        'expiration': ['Mars 2024', 'Mai 2024', 'Juin 2024', 'Aout 2024', 'Septembre 2024'],
        'name': 'Soja Futures',
    },
    'ZW' : {
        'data': ['H24', 'K24', 'N24', 'U24', 'Z24'],
        'expiration': ['Mars 2024', 'Mai 2024', 'Juin 2024', 'Septembre 2024', 'Decembre 2024'], 
        'name': 'Blé SRW Futures'
    },
    'ZM' : {
        'data': ['H24', 'K24', 'N24', 'Q24', 'U24'],
        'expiration': ['Mars 2024', 'Mai 2024', 'Juin 2024', 'Aout 2024', 'Septembre 2024'],
        'name': 'Tourteau de soja Futures'
    }
}

euronext = {
    'EBM': {
        'data': ['MAR24', 'MAY24', 'SEP24', 'DEC24', 'MAR25'],
        'expiration': ['Mars 2024', 'Mai 2024', 'Septembre 2024', 'Decembre 2024', 'Mars 2025'],
        'name': 'Milling wheat / Blé'
    },
    'EMA': {
        'data': ['MAR24', 'JUN24', 'AUG24', 'NOV24', 'MAR25'],
        'expiration': ['Mars 2024', 'Juin 2024', 'Aout 2024', 'Novembre 2024', 'Mars 2025'],
        'name': 'Corn / Mais'
    },
    'ECO': {
        'data': ['MAY24', 'AUG24', 'NOV24', 'FEB25', 'MAY25'],
        'expiration': ['Mai 2024', 'Aout 2024', 'Novrembre 2024', 'Fevrier 2025', 'Mai 2025'],
        'name': 'Rapeseed / Colza'
    }
}

def get_cot_from_db_euronext(ticker):
    dbname = db.get_database()
    collection_name = dbname["euronext_commodity"]
    df = pd.DataFrame(list(collection_name.find({"Ticker": ticker})))
    return df

def get_cot_from_db_cftc(market):
    dbname = db.get_database()
    collection_name = dbname["us_commodity"]
    df = pd.DataFrame(list(collection_name.find({"Market_and_Exchange_Names": market})))
    df = df.drop('_id', axis=1)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')
    df = df.rename(columns={'Swap__Positions_Short_All' : 'Swap_Positions_Short_All', 'Swap__Positions_Spread_All' : 'Swap_Positions_Spread_All'})
    return df

def format_data_euronext(df):
    df = df.drop('_id', axis=1)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')
    percent_data_list = ["Entreprises d'investissement et établissements de crédit pourcentage position Long (Total)",
        "Entreprises d'investissement et établissements de crédit pourcentage position Short (Total)",
        "Entreprises d'investissement et établissements de crédit pourcentage position Long (Hedge)",
        "Entreprises d'investissement et établissements de crédit pourcentage position Short (Hedge)",
        "Entreprises d'investissement et établissements de crédit pourcentage position Long (Autre)",
        "Entreprises d'investissement et établissements de crédit pourcentage position Short (Autre)",
        "Fonds d'investissement pourcentage position Long (Total)",
        "Fonds d'investissement pourcentage position Short (Total)",
        "Fonds d'investissement pourcentage position Long (Hedge)",
        "Fonds d'investissement pourcentage position Short (Hedge)",
        "Fonds d'investissement pourcentage position Long (Autre)",
        "Fonds d'investissement pourcentage position Short (Autre)",
        "Autres institutions financières pourcentage position Long (Total)",
        "Autres institutions financières pourcentage position Short (Total)",
        "Autres institutions financières pourcentage position Long (Hedge)",
        "Autres institutions financières pourcentage position Short (Hedge)",
        "Autres institutions financières pourcentage position Long (Autre)",
        "Autres institutions financières pourcentage position Short (Autre)",
        "Entreprises commerciales pourcentage position Long (Total)",
        "Entreprises commerciales pourcentage position Short (Total)",
        "Entreprises commerciales pourcentage position Long (Hedge)",
        "Entreprises commerciales pourcentage position Short (Hedge)",
        "Entreprises commerciales pourcentage position Long (Autre)",
        "Entreprises commerciales pourcentage position Short (Autre)",
        "Exploitants soumis à des obligations de conformité pourcentage position Long (Totale)",
        "Exploitants soumis à des obligations de conformité pourcentage position Short (Totale)",
        "Exploitants soumis à des obligations de conformité pourcentage position Long (Hedge)",
        "Exploitants soumis à des obligations de conformité pourcentage position Short (Hedge)",
        "Exploitants soumis à des obligations de conformité pourcentage position Long (Autre)",
        "Exploitants soumis à des obligations de conformité pourcentage position Short (Autre)"]
    
    df[percent_data_list] = df[percent_data_list].apply(lambda x: x.str.strip('%'))

    df = df.drop("Autres institutions financières nombre acteurs", axis=1)
    df = df.drop("Exploitants soumis à des obligations de conformité nombre acteurs", axis=1)
    df = df.drop("Fonds d'investissement nombre acteurs", axis=1)
    df = df.drop("Entreprises d'investissement et établissements de crédit nombre acteurs", axis=1)
    df = df.drop("Entreprises commerciales nombre acteurs", axis=1)

    element = ['Produit', 'Ticker']
    elements = [col for col in df.columns if col not in element]
    df[elements] = df[elements].astype(float)

    df = df.rename(columns={"Entreprises commerciales variation Long (Totale)" : "Entreprises commerciales variation Long (Total)", "Entreprises commerciales variation Short (Totale)" : "Entreprises commerciales variation Short (Total)"})

    return df

def show_positions_data_euronext(df, type_acteur): #type acteur is a string
    
    dfTotal = df[[f"{type_acteur} positions Long (Total)", f"{type_acteur} positions Short (Total)"]]
    dfHedge = df[[f"{type_acteur} positions Long (Hedge)", f"{type_acteur} positions Short (Hedge)"]]
    dfAutre = df[[f"{type_acteur} positions Long (Autre)", f"{type_acteur} positions Short (Autre)"]]

    fig, axs = plt.subplots(3)

    axs[0].plot(dfHedge[f"{type_acteur} positions Long (Hedge)"], color='green', label='positions Long')
    axs[0].plot(dfHedge[f"{type_acteur} positions Short (Hedge)"], color='red', label='positions Short')
    axs[0].set_title(f"{type_acteur} positions Hedge")
    axs[0].legend()

    axs[1].plot(dfAutre[f"{type_acteur} positions Long (Autre)"], color='green', label='positions Long')
    axs[1].plot(dfAutre[f"{type_acteur} positions Short (Autre)"], color='red', label='positions Short')
    axs[1].set_title(f"{type_acteur} positions Autre")
    axs[1].legend()

    axs[2].plot(dfTotal[f"{type_acteur} positions Long (Total)"], color='green', label='positions Long')
    axs[2].plot(dfTotal[f"{type_acteur} positions Short (Total)"], color='red', label='positions Short')
    axs[2].set_title(f"{type_acteur} positions Total")
    axs[2].legend()

    plt.show()

def net_position_euronext(df):
    df['FondNetPos'] = df["Fonds d'investissement positions Long (Total)"] - df["Fonds d'investissement positions Short (Total)"]
    df['CommerceNetPos'] = df["Entreprises commerciales positions Long (Total)"] - df["Entreprises commerciales positions Short (Total)"]
    df['InvestAndCredit'] = df["Entreprises d'investissement et établissements de crédit positions Long (Total)"] - df["Entreprises d'investissement et établissements de crédit positions Short (Total)"]
    df['OtherFinancial'] = df["Autres institutions financières positions Long (Total)"] - df["Autres institutions financières positions Short (Total)"]
    
    df = df.sort_index()
    return df
    # fig, ax = plt.subplots(figsize=(13, 6.25))
    # ax.plot(df['FondNetPos'], label="Fonds d'investissement")
    # ax.plot(df['CommerceNetPos'], label="Entreprises commerciales")
    # ax.plot(df['InvestAndCredit'], label="Entreprises d'investissement et établissements de crédit")
    # ax.plot(df['OtherFinancial'], label="Autres institutions financières")
    # ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.8)
    # ax.set_ylabel('Contrats', style='italic')

    # plt.axhline(y = 0, color = 'grey', linestyle = '--', linewidth=0.5, alpha=0.5) 
    # plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), frameon=False, ncol=4)
    # plt.suptitle(f"POSITIONS NETTES", x=0.5125, y=.95, fontsize = 15, fontweight='bold')
    # plt.title(f"{df['Produit'][0]}", fontsize = 10, color="grey", style='italic')
    # plt.savefig(f"img/net{df['Produit'][0].replace('/', '').replace(' ', '')}Euronext.png")
    # plt.close()

def net_position_cftc(df, start_year):
    df = df.sort_index()
    df = df[df.index.year >= start_year]
    df['FondNetPos'] = df["M_Money_Positions_Long_All"] - df["M_Money_Positions_Short_All"]
    df['CommerceNetPos'] = df["Prod_Merc_Positions_Long_All"] - df["Prod_Merc_Positions_Short_All"]
    df['SwapDealers'] = df["Swap_Positions_Long_All"] - df["Swap_Positions_Short_All"]
    df['OtherFinancial'] = df["Other_Rept_Positions_Long_All"] - df["Other_Rept_Positions_Short_All"]

    return df
    
    # fig, ax = plt.subplots(figsize=(13, 6.25))
    # ax.plot(df['FondNetPos'], label="Managed Money")
    # ax.plot(df['CommerceNetPos'], label="Producer/Merchant")
    # ax.plot(df['SwapDealers'], label="Swaps")
    # ax.plot(df['OtherFinancial'], label="Other Reportables")
    # ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.8)
    # ax.set_ylabel('Contrats', style='italic')

    # plt.axhline(y = 0, color = 'grey', linestyle = '--', linewidth=0.5, alpha=0.5) 
    # plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), frameon=False, ncol=4)
    # plt.suptitle(f"POSITIONS NETTES", x=0.5125, y=.95, fontsize = 15, fontweight='bold')
    # plt.title(f"{df['Market_and_Exchange_Names'][0]}", fontsize = 10, color="grey", style='italic')
    # plt.savefig(f"img/net{df['Market_and_Exchange_Names'][0].replace(' ', '')}cbot.png")
    # plt.close()

def seasonality_euronext(df):
    data = []
    df = df.sort_index()
    years = list(set(df.index.year))
    for i, act in enumerate(["Fonds d'investissement", "Entreprises commerciales", "Autres institutions financières", "Entreprises d'investissement et établissements de crédit"]):
        for year in years[:-1]:
            if df['Produit'][0] == "Corn / Mais":
                year_data = df[(df.index >= pd.to_datetime(f"{year}-07-01")) & (df.index < pd.to_datetime(f"{year+1}-07-01"))]
                year_data['Net'] = (year_data[act + " positions Long (Total)"] - year_data[act + " positions Short (Total)"]).sort_index()
                year_data['Type'] = act
                year_data = year_data.reset_index()
            elif df['Produit'][0] == "Milling Wheat / Ble" or df['Produit'][0] == "Rapeseed / Colza":
                year_data = df[(df.index >= pd.to_datetime(f"{year}-07-01")) & (df.index < pd.to_datetime(f"{year+1}-07-01"))]
                year_data['Net'] = (year_data[act + " positions Long (Total)"] - year_data[act + " positions Short (Total)"]).sort_index()
                year_data['Type'] = act
                year_data = year_data.reset_index()
            else:
                print("Erreur dans l'attribution des dates")
            data.append(year_data[['Date', 'Net', 'Type']])
    return data

def seasonality_cftc(df, start_year):
    df = df.sort_index()
    df = df[df.index.year >= start_year]
    years = list(set(df.index.year))
    #years = years[:2]
    fig, axs = plt.subplots(2, 2, figsize=(13, 6.25))
    for i, act in enumerate(["M_Money", "Prod_Merc", "Other_Rept", "Swap"]):
        row, col = divmod(i, 2)
        for year in years[:-1]:
            if df['Market_and_Exchange_Names'][0] == "CORN - CHICAGO BOARD OF TRADE" or df['Market_and_Exchange_Names'][0] == "SOYBEANS - CHICAGO BOARD OF TRADE":
                year_data = df[(df.index >= pd.to_datetime(f"{year}-09-01")) & (df.index < pd.to_datetime(f"{year+1}-09-01"))]
                net = (year_data[act + "_Positions_Long_All"] - year_data[act + "_Positions_Short_All"]).sort_index()
                net = net.reset_index()
                net['Date'] = pd.to_datetime(net['Date'].map(lambda x: x.replace(year=2100)))
                mask = (net['Date'].dt.month >= 1) & (net['Date'].dt.month < 9)

            elif df['Market_and_Exchange_Names'][0] == "SOYBEAN OIL - CHICAGO BOARD OF TRADE" or df['Market_and_Exchange_Names'][0] == "SOYBEAN MEAL - CHICAGO BOARD OF TRADE":
                year_data = df[(df.index >= pd.to_datetime(f"{year}-10-01")) & (df.index < pd.to_datetime(f"{year+1}-10-01"))]
                net = (year_data[act + "_Positions_Long_All"] - year_data[act + "_Positions_Short_All"]).sort_index()
                net = net.reset_index()
                net['Date'] = pd.to_datetime(net['Date'].map(lambda x: x.replace(year=2100)))
                mask = (net['Date'].dt.month >= 1) & (net['Date'].dt.month < 10)

            elif df['Market_and_Exchange_Names'][0] == "WHEAT-SRW - CHICAGO BOARD OF TRADE" or df['Market_and_Exchange_Names'][0] == "WHEAT-HRSpring - MINNEAPOLIS GRAIN EXCHANGE" or df['Market_and_Exchange_Names'][0] == "WHEAT-HRW - CHICAGO BOARD OF TRADE":
                year_data = df[(df.index >= pd.to_datetime(f"{year}-06-01")) & (df.index < pd.to_datetime(f"{year+1}-06-01"))]
                net = (year_data[act + "_Positions_Long_All"] - year_data[act + "_Positions_Short_All"]).sort_index()
                net = net.reset_index()
                net['Date'] = pd.to_datetime(net['Date'].map(lambda x: x.replace(year=2100)))
                mask = (net['Date'].dt.month >= 1) & (net['Date'].dt.month < 6)

            else:
                print("Erreur dans l'attribution des dates")

            acteur = name_cftc[act]

            net.loc[mask, 'Date'] = net.loc[mask, 'Date'].apply(lambda x: x.replace(year=2101))
            net = net.set_index('Date')
    return net
    #         axs[row, col].xaxis.set_major_formatter(mdates.DateFormatter('%b-%d'))
    #         axs[row, col].plot(net, label=f"{year} / {year+1}")
    #         axs[row, col].grid(True, linestyle='--', linewidth=0.5, alpha=0.8)
    #         axs[row, col].set_title(acteur, fontsize = 10, color="grey", style='italic')
    #         axs[row, col].set_ylabel('Contrats', style='italic')
    
    # plt.axhline(y = 0, color = 'grey', linestyle = '--', linewidth=0.5, alpha=0.5) 
    # plt.legend(bbox_to_anchor=(0.88, -0.1), frameon=False, ncol=len(years))
    # plt.suptitle(f"SAISONALITÉ DES POSITIONS", x=0.5125, y=.98, fontsize = 15, fontweight='bold')
    # fig.text(0.51, 0.93, df['Market_and_Exchange_Names'][0], ha='center', va='center', fontsize=8, color="grey")
    
    # plt.savefig(f"img/seasonalite{df['Market_and_Exchange_Names'][0].replace(' ', '')}Cbot.png")
    # #plt.show()
    # plt.close()

def variation_euronext(df):
    fig, axs = plt.subplots(2, 2, figsize=(13, 6.25))
    for i, act in enumerate(["Fonds d'investissement", "Entreprises commerciales", "Autres institutions financières", "Entreprises d'investissement et établissements de crédit"]):
        row, col = divmod(i, 2)
        df['NetVar'] = df[f"{act} variation Long (Total)"] - df[f"{act} variation Short (Total)"]
        df = df.sort_index()
        axs[row, col].plot(df['NetVar'].index, df['NetVar'].values, label='Variation par rapport au rapport précendent', linewidth=0.8)
        axs[row, col].set_ylabel('Contrats', style='italic')
        axs[row, col].set_title(act, fontsize = 10, color="grey", style='italic')

    plt.axhline(y = 0, color = 'grey', linestyle = '--', linewidth=0.5, alpha=0.5) 
    plt.legend(bbox_to_anchor=(0.30, -0.1), frameon=False)
    plt.suptitle(f"VARIATION NETTE DES POSITIONS", x=0.5125, y=.98, fontsize = 15, fontweight='bold')
    fig.text(0.51, 0.93, df['Produit'][0], ha='center', va='center', fontsize=10, color="grey")
    
    plt.savefig(f"img/variation{df['Produit'][0].replace('/', '').replace(' ', '')}Euronext.png")
    #plt.show()
    plt.close()

def variation_cftc(df, start_year):
    df = df.sort_index()
    df = df[df.index.year >= start_year]
    fig, axs = plt.subplots(2, 2, figsize=(13, 6.25))
    for i, act in enumerate(["M_Money", "Prod_Merc", "Other_Rept", "Swap"]):
        row, col = divmod(i, 2)
        acteur = name_cftc[act]
        df['NetVar'] = (df[f"Change_in_{act}_Long_All"].str.strip()).astype(float) - (df[f"Change_in_{act}_Short_All"].str.strip()).astype(float)
        axs[row, col].plot(df['NetVar'].index, df['NetVar'].values, label='Variation par rapport au rapport précendent', linewidth=0.8)
        axs[row, col].set_ylabel('Contrats', style='italic')
        axs[row, col].set_title(acteur, fontsize = 10, color="grey", style='italic')

    plt.axhline(y = 0, color = 'grey', linestyle = '--', linewidth=0.5, alpha=0.5) 
    plt.legend(bbox_to_anchor=(0.30, -0.1), frameon=False)
    plt.suptitle(f"VARIATION NETTE DES POSITIONS", x=0.5125, y=.98, fontsize = 15, fontweight='bold')
    fig.text(0.51, 0.93, df['Market_and_Exchange_Names'][0], ha='center', va='center', fontsize=10, color="grey")
    plt.savefig(f"img/variation{df['Market_and_Exchange_Names'][0].replace(' ', '')}Cbot.png")
    #plt.show()
    plt.close()

def euronext_futures(produit_dict):
    for comm, val in produit_dict.items():
            fig = plt.figure(figsize=(13, 6.25))
            gs = gridspec.GridSpec(2, 6)
            name = val['name']
            for i, expi in enumerate(val['data']):
                if i < 3:
                    ax = plt.subplot(gs[0, 2 * i:2 * i + 2])
                else:
                    ax = plt.subplot(gs[1, 2 * i - 5:2 * i + 2 - 5])

                df = pd.DataFrame(list(db.get_database_price()["euronext"].find({"Ticker": comm, "Expiration": expi})))
                df = df.sort_values(by='Date', ascending=True)
                ax.plot(df['Date'], df['Prix'], label='Prix')
                ax.set_title(val['expiration'][i], fontsize = 10, color="grey", style='italic')
                ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.8)
                ax.set_ylabel('Prix (€/t)', style='italic')
                ax.tick_params(axis='x', labelsize=6)

            plt.suptitle(f"{name.upper()} FUTURES", x=0.50, y=0.98, fontsize = 15, fontweight='bold')
            fig.tight_layout()
            #plt.show()
            plt.savefig(f"img/{comm}Futures.png")
            plt.close()

def euronext_physique(startDate):
    df = pd.DataFrame(list(db.get_database_price()["physique"].find({"Date": {"$gte": pd.to_datetime(startDate, format='%Y-%m-%d')}})))
    df = df.sort_values(by='Date', ascending=True)
    df = df[df['Produit'] != 'Ble dur']
    for prod in df['Produit'].unique():
        dfProd = df[df['Produit'] == prod]
        places = dfProd['Place'].unique()
        fig = plt.figure(figsize=(13, 6.25))
        if len(places) < 3:
            gs = gridspec.GridSpec(1, 2)
        else:
            gs = gridspec.GridSpec(2, 6)
        for i, place in enumerate(dfProd['Place'].unique()):         
            dfPlace = dfProd[dfProd['Place'] == place]
            if len(places) < 3:
                ax = plt.subplot(gs[0, 1 * i:1 * i + 1])
            elif len(places) < 6:
                if i < 3:
                    ax = plt.subplot(gs[0, 2 * i:2 * i + 2])
                else:
                    ax = plt.subplot(gs[1, 2 * i - 5:2 * i + 2 - 5])
            else:
                if i < 3:
                    ax = plt.subplot(gs[0, 2 * i:2 * i + 2])
                else:
                    ax = plt.subplot(gs[1, 2 * i - 6:2 * i + 2 - 6])

            ax.plot(dfPlace['Date'], dfPlace['Prix'], label='Prix')
            ax.set_title(place, fontsize = 10, color="grey", style='italic')
            ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.8)
            ax.set_ylabel('Prix (€/t)', style='italic')
            ax.tick_params(axis='x', labelsize=6)

        if prod == 'Ble tendre':
            prod = 'Blé tendre'
        plt.suptitle(f'{prod.upper()} PHYSIQUE', x=0.50, y=0.98, fontsize = 15, fontweight='bold')
        fig.tight_layout()
        #plt.show()
        plt.savefig(f"img/{prod.replace(' ', '')}Physique.png")
        plt.close()

def cbot_futures(produit_dict):
    for comm, val in produit_dict.items():
        fig = plt.figure(figsize=(13, 6.25))
        gs = gridspec.GridSpec(2, 6)
        name = val['name']
        for i, expi in enumerate(val['data']):
            if i < 3:
                ax = plt.subplot(gs[0, 2 * i:2 * i + 2])
            else:
                ax = plt.subplot(gs[1, 2 * i - 5:2 * i + 2 - 5])

            ticker = comm+expi+'.CBT'
            price = yf.download(ticker, start='1900-01-01', interval='1d')
            ax.plot(price.index, price['Close'], label='Price')
            ax.set_title(val['expiration'][i], fontsize = 10, color="grey", style='italic')
            ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.8)
            ax.set_ylabel('Prix ($c/bu)', style='italic')
            ax.tick_params(axis='x', labelsize=6)

        plt.suptitle(f"{name.upper()}", x=0.50, y=0.98, fontsize = 15, fontweight='bold')
        fig.tight_layout()
        plt.savefig(f'img/{comm}Futures.png')
        plt.close()

if __name__ == '__main__': 
    for i in ['EBM', 'EMA', 'ECO']:
        df = get_cot_from_db_euronext(i)
        dfEuronext = format_data_euronext(df)
        net_position_euronext(dfEuronext)
        seasonality_euronext(dfEuronext)
        variation_euronext(dfEuronext)
    euronext_futures(euronext)
    euronext_physique('2021-01-01')
    for y in ['CORN - CHICAGO BOARD OF TRADE', 'SOYBEAN OIL - CHICAGO BOARD OF TRADE', 'SOYBEANS - CHICAGO BOARD OF TRADE', 'WHEAT-SRW - CHICAGO BOARD OF TRADE', 'SOYBEAN MEAL - CHICAGO BOARD OF TRADE']:
        dfCbot = get_cot_from_db_cftc(y)
        net_position_cftc(dfCbot, 2018)
        seasonality_cftc(dfCbot, 2018)
        variation_cftc(dfCbot, 2018)
    cbot_futures(cbot)
    
