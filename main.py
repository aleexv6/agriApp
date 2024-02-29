from flask import Flask, render_template
import database as db
import pandas as pd
from highcharts_core import highcharts

app = Flask(__name__)

expi = {'Ble tendre' : 'MAR24', 'Mais' : 'MAR24', 'Colza' : 'MAY24'}
listProductFutures = {'Ble tendre':'EBM', 'Mais':'EMA', 'Colza':'ECO'}

cursorPhysique = db.get_database_physical().find({})
dfPhysique = pd.DataFrame(list(cursorPhysique)).sort_values(by='Date', ascending=True)
dfPhysiqueEBM = dfPhysique[(dfPhysique['Produit'] == 'Ble tendre') & (dfPhysique['Place'] == 'La Pallice Rendu')]
dfPhysiqueEBM = dfPhysiqueEBM[['Date', 'Prix']]
dfPhysiqueEBM = dfPhysiqueEBM[dfPhysiqueEBM['Date'].dt.year > 2023]

productPhysique = dfPhysique['Produit'].unique()

cursorFutures = db.get_database_euronext().find({})
dfFutures = pd.DataFrame(list(cursorFutures)).sort_values(by='Date', ascending=True)
productFutures = dfFutures['Ticker'].unique()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/physique")
def physique():
    my_chart = highcharts.Chart.from_pandas(dfPhysiqueEBM,
                                            property_map = {'x': 'Date', 'y': 'Prix'},
                                            chart_kwargs = {'container':'myChartBase', 'variable_name': 'myChart'},
                                            options_kwargs={'title': {'text': 'Abrakadabra'}, 'x_axis': {'type': 'datetime'}})
    my_chart.to_js_literal('static/js/my-js-literal.js')
    return render_template('physique.html', data=dfPhysique, listProduct=productPhysique, datafutures=dfFutures, listProductFutures=listProductFutures, expi=expi)

@app.route("/futures")
def futures():
    return render_template('futures.html', listProduct=productFutures, data=dfFutures, listProductFutures=listProductFutures)
    