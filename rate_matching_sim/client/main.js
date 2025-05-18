// Configuration
const WS_URL = 'ws://' + window.location.hostname + ':12000/ws';
const API_URL = 'http://' + window.location.hostname + ':12000/api';

// Global variables
let resultsChart = null;
let websocket = null;
let currentSimulationId = null;
let currentComparisonId = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Initialize UI elements
    initializeUI();
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Set up event listeners
    document.getElementById('simulation-form').addEventListener('submit', runSimulation);
    document.getElementById('comparison-form').addEventListener('submit', runComparison);
    document.getElementById('strategy').addEventListener('change', toggleStrategyOptions);
});

// Initialize UI elements
function initializeUI() {
    // Initialize chart
    initializeResultsChart();
    
    // Set up strategy options
    toggleStrategyOptions();
}

// Initialize results chart
function initializeResultsChart() {
    const ctx = document.getElementById('results-chart').getContext('2d');
    resultsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: '最終最高レート (平均)',
                data: [],
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgb(75, 192, 192)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
}

// Toggle strategy options based on selected strategy
function toggleStrategyOptions() {
    const strategy = document.getElementById('strategy').value;
    const thresholdContainer = document.getElementById('threshold-container');
    const customStrategyContainer = document.getElementById('custom-strategy-container');
    
    // Hide all strategy-specific options
    thresholdContainer.classList.add('d-none');
    customStrategyContainer.classList.add('d-none');
    
    // Show options for selected strategy
    if (strategy === 'THRESHOLD_LOWEST') {
        thresholdContainer.classList.remove('d-none');
    } else if (strategy === 'CUSTOM') {
        customStrategyContainer.classList.remove('d-none');
    }
}

// Connect to WebSocket
function connectWebSocket() {
    websocket = new WebSocket(WS_URL);
    
    websocket.onopen = () => {
        console.log('WebSocket connected');
    };
    
    websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };
    
    websocket.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after a delay
        setTimeout(connectWebSocket, 3000);
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(message) {
    console.log('Received message:', message);
    
    switch (message.type) {
        case 'simulation_results':
            displaySimulationResults(message.results);
            break;
        case 'comparison_results':
            displayComparisonResults(message.results);
            break;
        case 'error':
            alert(`Error: ${message.error}`);
            break;
        default:
            console.log('Unknown message type:', message.type);
    }
}

// Run simulation
function runSimulation(event) {
    event.preventDefault();
    
    // Show loading state
    document.getElementById('run-simulation').disabled = true;
    document.getElementById('run-simulation').textContent = '実行中...';
    
    // Get form data
    const formData = new FormData(event.target);
    const params = {};
    
    // Process form data
    for (const [key, value] of formData.entries()) {
        // Convert numeric values
        if (key === 'custom_strategy_code') {
            params[key] = value;
        } else if (value === '') {
            params[key] = null;
        } else if (!isNaN(value) && key !== 'strategy') {
            params[key] = Number(value);
        } else {
            params[key] = value;
        }
    }
    
    // Send request via WebSocket
    const requestId = Date.now().toString();
    websocket.send(JSON.stringify({
        type: 'run_simulation',
        id: requestId,
        params: params
    }));
    
    // Alternative: Send request via REST API
    /*
    fetch(`${API_URL}/simulation`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(params)
    })
    .then(response => response.json())
    .then(data => {
        displaySimulationResults(data);
    })
    .catch(error => {
        console.error('Error running simulation:', error);
        alert('Error running simulation: ' + error.message);
    })
    .finally(() => {
        // Reset button state
        document.getElementById('run-simulation').disabled = false;
        document.getElementById('run-simulation').textContent = 'シミュレーション実行';
    });
    */
}

// Run comparison
function runComparison(event) {
    event.preventDefault();
    
    // Show loading state
    document.getElementById('run-comparison').disabled = true;
    document.getElementById('run-comparison').textContent = '実行中...';
    
    // Get form data
    const formData = new FormData(event.target);
    const params = {};
    
    // Process form data
    for (const [key, value] of formData.entries()) {
        // Convert numeric values
        if (value === '') {
            params[key] = null;
        } else if (!isNaN(value)) {
            params[key] = Number(value);
        } else {
            params[key] = value;
        }
    }
    
    // Send request via WebSocket
    const requestId = Date.now().toString();
    websocket.send(JSON.stringify({
        type: 'run_comparison',
        id: requestId,
        params: params
    }));
}

// Display simulation results
function displaySimulationResults(results) {
    // Store current simulation ID
    currentSimulationId = results.simulation_id;
    
    // Update results container
    const container = document.getElementById('simulation-results');
    
    // Format results
    const html = `
        <div class="row">
            <div class="col-md-6">
                <h5>戦略: ${formatStrategyName(results.strategy)}</h5>
                <p>シミュレーション回数: ${results.num_simulations}</p>
            </div>
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body">
                        <h5 class="card-title">最終最高レート</h5>
                        <h3 class="card-text text-center">${results.mean_highest_rate.toFixed(2)}</h3>
                        <p class="card-text text-center text-muted">標準偏差: ${results.std_highest_rate.toFixed(2)}</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-3">
            <div class="col-md-3">
                <div class="border rounded p-2 text-center">
                    <div class="small text-muted">最小値</div>
                    <div class="fw-bold">${results.min_highest_rate.toFixed(2)}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2 text-center">
                    <div class="small text-muted">最大値</div>
                    <div class="fw-bold">${results.max_highest_rate.toFixed(2)}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2 text-center">
                    <div class="small text-muted">中央値</div>
                    <div class="fw-bold">${results.median_highest_rate.toFixed(2)}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2 text-center">
                    <div class="small text-muted">シミュレーションID</div>
                    <div class="fw-bold small">${results.simulation_id}</div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Update chart
    updateResultsChart([results.strategy], [results.mean_highest_rate]);
    
    // Display detailed results
    displayDetailedResults(results.detailed_results);
    
    // Reset button state
    document.getElementById('run-simulation').disabled = false;
    document.getElementById('run-simulation').textContent = 'シミュレーション実行';
}

// Display comparison results
function displayComparisonResults(results) {
    // Store current comparison ID
    currentComparisonId = results.comparison_id;
    
    // Update results container
    const container = document.getElementById('simulation-results');
    
    // Format results
    const html = `
        <div class="row">
            <div class="col-md-6">
                <h5>戦略比較</h5>
                <p>最良戦略: ${formatStrategyName(results.best_strategy)}</p>
                <p>最良戦略の平均レート: ${results.best_strategy_mean_rate.toFixed(2)}</p>
            </div>
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body">
                        <h5 class="card-title">比較ID</h5>
                        <p class="card-text text-center small">${results.comparison_id}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Update chart with comparison data
    const strategies = [];
    const rates = [];
    
    for (const [strategy, data] of Object.entries(results.results)) {
        strategies.push(strategy);
        rates.push(data.mean_highest_rate);
    }
    
    updateResultsChart(strategies, rates);
    
    // Display detailed comparison results
    displayDetailedComparisonResults(results.results);
    
    // Reset button state
    document.getElementById('run-comparison').disabled = false;
    document.getElementById('run-comparison').textContent = '戦略比較実行';
}

// Update results chart
function updateResultsChart(labels, data) {
    // Format strategy names for display
    const formattedLabels = labels.map(formatStrategyName);
    
    // Update chart data
    resultsChart.data.labels = formattedLabels;
    resultsChart.data.datasets[0].data = data;
    
    // Update chart
    resultsChart.update();
}

// Display detailed results
function displayDetailedResults(detailedResults) {
    const container = document.getElementById('detailed-results');
    
    if (!detailedResults || detailedResults.length === 0) {
        container.innerHTML = '<div class="text-center text-muted"><p>詳細結果はありません</p></div>';
        return;
    }
    
    // Get the first detailed result
    const firstResult = detailedResults[0];
    
    // Generate HTML for account stats
    const accountStatsHtml = firstResult.account_stats.map(account => `
        <div class="col-md-4 mb-3">
            <div class="card strategy-card h-100">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0">アカウント ${account.account_id}</h6>
                </div>
                <div class="card-body">
                    <div class="row g-2">
                        <div class="col-6">
                            <div class="small text-muted">初期レート</div>
                            <div class="fw-bold">${account.initial_rate}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">最終レート</div>
                            <div class="fw-bold">${account.current_rate.toFixed(2)}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">適正レート</div>
                            <div class="fw-bold">${account.true_skill}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">レート変化</div>
                            <div class="fw-bold ${account.rate_change >= 0 ? 'positive' : 'negative'}">
                                ${account.rate_change >= 0 ? '+' : ''}${account.rate_change}
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">試合数</div>
                            <div class="fw-bold">${account.matches_played}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">勝率</div>
                            <div class="fw-bold">${account.win_rate}%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    // Generate HTML for detailed results
    const html = `
        <h5>サンプルシミュレーション結果</h5>
        <p class="text-muted">以下は${detailedResults.length}個のシミュレーションのうち1つの詳細結果です</p>
        
        <div class="row mt-3">
            <div class="col-md-6">
                <div class="border rounded p-2">
                    <div class="small text-muted">戦略</div>
                    <div class="fw-bold">${formatStrategyName(firstResult.strategy)}</div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="border rounded p-2">
                    <div class="small text-muted">総試合数</div>
                    <div class="fw-bold">${firstResult.total_matches}</div>
                </div>
            </div>
        </div>
        
        <h5 class="mt-4">アカウント統計</h5>
        <div class="row">
            ${accountStatsHtml}
        </div>
    `;
    
    container.innerHTML = html;
}

// Display detailed comparison results
function displayDetailedComparisonResults(results) {
    const container = document.getElementById('detailed-results');
    
    if (!results || Object.keys(results).length === 0) {
        container.innerHTML = '<div class="text-center text-muted"><p>詳細結果はありません</p></div>';
        return;
    }
    
    // Generate HTML for strategy results
    const strategiesHtml = Object.entries(results).map(([strategy, data]) => `
        <div class="col-md-4 mb-3">
            <div class="card strategy-card h-100">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0">${formatStrategyName(strategy)}</h6>
                </div>
                <div class="card-body">
                    <div class="row g-2">
                        <div class="col-6">
                            <div class="small text-muted">平均レート</div>
                            <div class="fw-bold">${data.mean_highest_rate.toFixed(2)}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">標準偏差</div>
                            <div class="fw-bold">${data.std_highest_rate.toFixed(2)}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">最小値</div>
                            <div class="fw-bold">${data.min_highest_rate.toFixed(2)}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">最大値</div>
                            <div class="fw-bold">${data.max_highest_rate.toFixed(2)}</div>
                        </div>
                        <div class="col-12">
                            <div class="small text-muted">中央値</div>
                            <div class="fw-bold">${data.median_highest_rate.toFixed(2)}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    // Generate HTML for detailed results
    const html = `
        <h5>戦略比較詳細</h5>
        <div class="row mt-3">
            ${strategiesHtml}
        </div>
    `;
    
    container.innerHTML = html;
}

// Format strategy name for display
function formatStrategyName(strategy) {
    switch (strategy) {
        case 'HIGHEST_RATE':
            return '最高レート';
        case 'SECOND_HIGHEST_RATE':
            return '2番目に高いレート';
        case 'LOWEST_RATE':
            return '最低レート';
        case 'RANDOM':
            return 'ランダム';
        case 'THRESHOLD_LOWEST':
            return '閾値以上の最低レート';
        case 'CLOSEST_TO_AVERAGE':
            return '平均に最も近い';
        case 'FARTHEST_FROM_AVERAGE':
            return '平均から最も遠い';
        case 'CUSTOM':
            return 'カスタム戦略';
        default:
            return strategy;
    }
}