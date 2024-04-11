Highcharts.theme = {

    lang: {
    
        /*------ Dates translation ------ */
        months: ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
            'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'],
        weekdays: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi',
            'Jeudi', 'Vendredi', 'Samedi'],
        shortMonths: ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil',
            'Aout', 'Sept', 'Oct', 'Nov', 'Déc'],
    
        /*------ Texts translation ------ */
        downloadPNG: 'Télécharger en image PNG',
        downloadJPEG: 'Télécharger en image JPEG',
        downloadPDF: 'Télécharger en document PDF',
        downloadSVG: 'Télécharger en document Vectoriel',
        exportButtonTitle: 'Export du graphique',
        loading: 'Chargement en cours...',
        printButtonTitle: 'Imprimer le graphique',
        resetZoom: 'Réinitialiser le zoom',
        resetZoomTitle: 'Réinitialiser le zoom au niveau 1:1',
        printChart: 'Imprimer le graphique',
    
        /*------ Number Formate ------ */
        thousandsSep: ' ', // ex: 52 000
        decimalPoint: ',' // ex: 1 525,50
    },
    credits: {
        /*------ Unrelated but usefull to remove credits in each charts ------ */
        enabled: false
    },
    rangeSelector: {
        /*------ Highstock date range selector (the 2 little inputs in right corner) ------ */
        inputDateFormat: '%e %b %Y', // ex: 8 Avr 2014
        inputEditDateFormat: '%d/%m/%Y', // After clicking on item ex : 13/06/2014
        // Processing After enter key pressed : apply the 13/06/2014 format
        inputDateParser: function (value) {
            value = value.split('/');
            return Date.UTC(
                    parseInt(value[2]),
                    parseInt(value[1]) - 1,
                    parseInt(value[0])
                    );
        },
        /*------ Highstock zoom selector (on the left top side) ------ */
        buttons: [{
                type: 'month',
                count: 1,
                text: '1 M' // useless translate :p
            }, {
                type: 'month',
                count: 6,
                text: '6 M' // useless translate :p
            }, {
                type: 'year',
                count: 1,
                text: '1 A' // translate Y in A (Année in french)
            }, {
                type: 'all',
                count: 1,
                text: 'Tout' // translate all in Tout
            }],
        selected: 2, // Here we force to select 6 M
        inputEnabled: true // Active Inputs
    },
    };
    
    Highcharts.setOptions(Highcharts.theme);