// Get the select element
let dataPlace = JSON.parse('{{ prod | tojson }}');
let dataExpi = JSON.parse('{{ expi | tojson }}');
var selectElement = document.getElementById("basisProductSelector");
var outputPlace = document.getElementById("basisPlaceSelector");
var outputExpi = document.getElementById("basisContractSelector");
selectElement.addEventListener("change", function() {
    var selectedValue = selectElement.value;
    outputPlace.innerHTML = "";
    outputExpi.innerHTML = "";
    switch(selectedValue) {
        case "Mais":
            addOptions(dataPlace['Mais'], outputPlace);
            addOptions(dataExpi['Mais'], outputExpi);
            break;
        case "Ble tendre":
            addOptions(dataPlace['Ble tendre'], outputPlace);
            addOptions(dataExpi['Ble tendre'], outputExpi);
            break;
        case "Colza":
            addOptions(dataPlace['Colza'], outputPlace);
            addOptions(dataExpi['Colza'], outputExpi);
            break;
        default:
            outputPlace.innerHTML = "Default content";
            outputExpi.innerHTML = "Default content";
    }
});
function addOptions(options, outputDoc) {
    options.forEach(function(optionText) {
        var option = document.createElement("option");
        option.value = optionText;
        option.text = optionText;
        outputDoc.add(option);
    });
}


var produit = document.getElementById("basisProductSelector");
var place = document.getElementById("basisPlaceSelector");
var expiration = document.getElementById("basisContractSelector");
document.addEventListener("DOMContentLoaded", function() {
    console.log(produit.value);
    console.log(place.value);
    console.log(expiration.value);

    produit.addEventListener("change", handleSelectChange);
    place.addEventListener("change", handleSelectChange);
    expiration.addEventListener("change", handleSelectChange);
});
function handleSelectChange() {
    console.log(produit.value);
    console.log(place.value);
    console.log(expiration.value);
}

Highcharts.chart('myChartBase', {
    chart: {
        type: 'line'
    },
    title: {
        text: 'Highcharts with JSON Data'
    },
    xAxis: {
        title: {
            text: 'Day'
        },
        type: 'datetime'
    },
    yAxis: {
        title: {
            text: 'Prix'
        }
    },
    series: [{
        name: 'Prix',
        data: JSON.parse(chartData)
    }]
});
