let darkmode = localStorage.getItem('darkmode')
const elements = document.getElementsByClassName('highcharts-chart-theme-responsive');
const themeSwitch = document.getElementById('themeToggle')

const enableDarkmode = () => {
    document.body.classList.add('dark-theme')
    Array.from(elements).forEach(element => {
        element.classList.add('highcharts-dark')
    });
    Array.from(elements).forEach(element => {
        element.classList.remove('highcharts-light')
    });
    localStorage.setItem('darkmode', 'active')
}

const disableDarkmode = () => {
    document.body.classList.remove('dark-theme')
    Array.from(elements).forEach(element => {
        element.classList.add('highcharts-light')
    });
    Array.from(elements).forEach(element => {
        element.classList.remove('highcharts-dark')
    });
    localStorage.removeItem('darkmode');
}

if (darkmode === 'active') enableDarkmode()

themeSwitch.addEventListener('click', () => {
    darkmode = localStorage.getItem('darkmode')
    darkmode !== "active" ? enableDarkmode() : disableDarkmode()
})