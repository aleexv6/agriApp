let chart;
let tokensDiv;
let fidelity = document.getElementById('timeframeSelector').value;
$(document).ready(function() {
    let debounce;
    $('#marketInput').on('keydown', function (e) { 
        clearTimeout(debounce)
        debounce = setTimeout(() => {
                closeAllLists();
                getAutoComplete();  
        }, 500);
        if (e.keyCode == 13) {
            /*If the ENTER key is pressed, prevent the form from being submitted,*/
            e.preventDefault();
        }
    });
    document.addEventListener("click", function (e) {
        closeAllLists(e.target);
    });
    document.getElementById('timeframeSelector').addEventListener('change', function() {
        if (typeof tokensDiv !== "undefined" && tokensDiv[0].id !== ""){
            fidelity = document.getElementById('timeframeSelector').value
            fetchTokenPrices(tokensDiv, fidelity)
            .then(result => {
                chart = showHighcharts(result);
            })
        }
    });
    
})

function closeAllLists(elmnt) {
    /*close all autocomplete lists in the document,
    except the one passed as an argument:*/
    var x = document.getElementsByClassName("autocomplete-items");
    for (var i = 0; i < x.length; i++) {
        if (elmnt != x[i] && elmnt != document.getElementById("marketInput")) {
            x[i].parentNode.removeChild(x[i]);
        }
    }
}

async function getSelectedTokenPrice(token_id, fidelity) {
    try {
        const endTime = Date.now();
        const response = await fetch(`https://clob.polymarket.com/prices-history?market=${token_id}&startTs=""&endTs=${endTime}&fidelity=${fidelity}`);
        const data = await response.json();
        return data['history'];
    } catch (error) {
        throw error;
    }
}

async function fetchTokenPrices(tokensDiv, fidelity) {
    let priceList = [];
    document.getElementById("noTokenId").innerHTML = "";

    for (let g = 0; g < tokensDiv.length; g++) {
        try {
            let tokenId = tokensDiv[g].id;
            let history = await getSelectedTokenPrice(tokenId, fidelity);
            priceList.push({"outcome": tokensDiv[g].value, "data": history});
        } catch (error) {
            console.error(`Error fetching price for token ID ${tokenId}:`, error);
        }
    }

    return priceList
}

function showHighcharts(priceData){
    const allSeries = []
    priceData.forEach(item => {
        var date = item.data.map(d => d.t * 1000)
        var price = item.data.map(d => d.p * 100)
        const series = {
            name: item.outcome,
            data: date.map((_, i) => [date[i], price[i]])
        }
        allSeries.push(series)
    });
    const chart = new Highcharts.Chart({
        chart: {
            renderTo: 'myChartPolymarket',
            styledMode: true,
            type: 'line'
        },
        title: {
            text: document.getElementById("marketInput").value
        },
        xAxis: {
            title: {
                text: 'Date'
            },
            type: 'datetime'
        },
        yAxis: {
            title: {
                text: '% Chance'
            }
        },
        plotOptions: {
            series: {
                marker: {
                    enabled: false,
                }
            }
        },
        series: allSeries,
        credits: {
            enabled: false
        },
        exporting: {
            // Enable the export menu
            enabled: true,
        }
    });
    return chart
}

function getAutoComplete() {
    const query = $('#marketInput').val();
    fetch(`https://alexandrelargeau.fr/polymarket/search?find=${encodeURIComponent(query.trim())}`)
    .then((resp) => resp.json())
    .then((data) => {
            a = document.createElement("DIV");
            a.setAttribute("id", "autocompleteId");
            a.setAttribute("class", "autocomplete-items");
            /*append the DIV element as a child of the autocomplete container:*/
            document.getElementById("autocompleteResult").parentNode.appendChild(a);
            if (data.length === 0) {
                b = document.createElement("DIV");
                b.innerHTML += 'No data found';
                b.addEventListener("click", function(e) {
                    closeAllLists();
                });
                a.appendChild(b);
            }
            else {
                for (let i = 0; i < data.length; i++) {
                    b = document.createElement("DIV");
                    b.innerHTML += data[i]['question'];
                    for (let j = 0; j < data[i]['tokens'].length; j++){
                        b.innerHTML += "<input type='hidden' id='" + data[i]['tokens'][j]['token_id'] + "' value='" + data[i]['tokens'][j]['outcome'] + "'>";
                    }
                    b.addEventListener("click", function(e) {
                        document.getElementById("marketInput").value = this.textContent; //insert the value for the autocomplete text field
                        tokensDiv = this.getElementsByTagName("input")
                        if (tokensDiv[0].id !== "") {
                            fetchTokenPrices(tokensDiv, fidelity)
                            .then(result => {
                                chart = showHighcharts(result);
                            })
                            //
                        }
                        else{
                            if (typeof chart !== "undefined"){
                                chart.destroy()
                            }
                            document.getElementById("noTokenId").innerHTML = "No tokens found for this market"
                        }
                        closeAllLists();
                    });
                    a.appendChild(b);
                }
            }
            })
}