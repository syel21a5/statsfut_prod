document.addEventListener('DOMContentLoaded', function () {
    const chartCanvas = document.getElementById('progressionChart');
    if (!chartCanvas) return;

    const ctx = chartCanvas.getContext('2d');
    const dataStr = chartCanvas.getAttribute('data-chart');
    if (!dataStr) return;
    const data = JSON.parse(dataStr);

    // Colors mapping
    const winColor = '#28a745';
    const lossColor = '#dc3545';
    const drawColor = '#ffc107';

    const barColors = data.results.map(r => r === 'W' ? winColor : (r === 'L' ? lossColor : drawColor));

    // Prepare GF and GA for split bars
    // For 0-0 draws, we add a tiny offset so the color is visible
    const gfValues = data.gf.map((v, i) => (v === 0 && data.ga[i] === 0) ? 0.2 : v);
    const gaValues = data.ga.map((v, i) => (v === 0 && data.gf[i] === 0) ? -0.2 : v);

    new Chart(ctx, {
        data: {
            labels: data.labels,
            datasets: [
                {
                    type: 'line',
                    data: data.values,
                    borderColor: '#0066cc',
                    borderWidth: 2,
                    fill: false,
                    yAxisID: 'y-line',
                    pointRadius: 0,
                    order: 1
                },
                {
                    type: 'bar',
                    label: 'GF',
                    data: gfValues,
                    backgroundColor: barColors,
                    yAxisID: 'y-bar',
                    order: 2,
                    barPercentage: 1.0,
                    categoryPercentage: 0.9
                },
                {
                    type: 'bar',
                    label: 'GA',
                    data: gaValues,
                    backgroundColor: barColors,
                    yAxisID: 'y-bar',
                    order: 2,
                    barPercentage: 1.0,
                    categoryPercentage: 0.9
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { display: false, stacked: true },
                'y-line': { type: 'linear', display: false },
                'y-bar': {
                    type: 'linear',
                    display: true,
                    stacked: true,
                    grid: { display: true, drawOnChartArea: true, color: '#eee' },
                    ticks: { display: false }
                }
            }
        }
    });

    // Apply dynamic widths to avoid CSS linting errors with Django templates
    document.querySelectorAll('[data-width]').forEach(el => {
        let width = el.getAttribute('data-width');
        if (width) {
            // Ensure decimal separator is a dot (fixes locale issues where it might be a comma)
            width = width.replace(',', '.');
            el.style.width = width + '%';
        }
    });

    // Comparison tabs functionality
    const comparisonTabs = document.querySelectorAll('.comparison-tab');
    const comparisonContents = document.querySelectorAll('.comparison-content');

    comparisonTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const targetTab = this.getAttribute('data-tab');

            // Update tab styles
            comparisonTabs.forEach(t => {
                t.classList.remove('active');
                t.style.background = 'transparent';
                t.style.fontWeight = 'normal';
                t.style.borderBottom = 'none';
            });

            this.classList.add('active');
            this.style.background = '#fff';
            this.style.fontWeight = 'bold';
            this.style.borderBottom = '2px solid #0066cc';

            // Update content visibility
            comparisonContents.forEach(content => {
                const contentTab = content.getAttribute('data-content');
                if (contentTab === targetTab) {
                    content.style.display = 'block';
                } else {
                    content.style.display = 'none';
                }
            });
        });
    });
});
