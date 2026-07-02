// Main Frontend Orchestrator

// Configuration Templates Generator
function getTemplateCode(templateName) {
    const hdqsUrl = ApiClient.getHdqsServiceUrl();
    const apiKey = ApiClient.getApiKey();

    return `from collections import defaultdict
from sia import hdqs, HDQSError

def main():
    BASE_URL = "${hdqsUrl}"
    API_KEY = "${apiKey}"
    SHOTS = 20

    q = hdqs(base_url=BASE_URL, api_key=API_KEY)

    counts = defaultdict(int)

    for _ in range(SHOTS):
        # Create 3 qubits
        q.qbt_create(num_qubits=3)

        # GHZ State: H + 2 CNOTs
        q.qbt_run([
            "h 0",
            "cx 0 1",
            "cx 1 2"
        ])

        # Measure all 3 qubits
        meas = q.qbt_measure([0, 1, 2], collapse=True)

        bits = ""
        for r in meas["result"]["measurement_results"]:
            bits += str(r["result"])

        counts[bits] += 1

    print("GHZ State Measurement Distribution:")
    for state, count in sorted(counts.items()):
        print(f"{state}: {count}")

if __name__ == "__main__":
    try:
        main()
    except HDQSError as e:
        print("HDQS Error:", e)
`;
}

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize Monaco Editor
    const consoleElement = document.getElementById('console');
    const runBtn = document.getElementById('run-btn');
    const loader = document.getElementById('loader');
    const statusElement = document.getElementById('editor-status');

    try {
        const initialCode = getTemplateCode('ghz-shots');
        await initializeMonacoEditor(initialCode);
        statusElement.textContent = 'Ready';
    } catch (err) {
        consoleElement.textContent = `Editor Error: Failed to load Monaco. Details: ${err.message}`;
        statusElement.textContent = 'Failed to load';
        statusElement.style.color = 'var(--error-color)';
    }

    // 2. Tab Switching logic
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });

    // 3. Templates Selection
    const templateItems = document.querySelectorAll('.template-list .template-item');
    templateItems.forEach(item => {
        item.addEventListener('click', () => {
            templateItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            const templateName = item.dataset.template;
            const code = getTemplateCode(templateName);
            setEditorCode(code);
            
            // Log template change to console
            consoleElement.textContent = `Loaded ${item.querySelector('.template-title').textContent} template.\nReady to run.`;
            consoleElement.classList.remove('error');
            clearQuantumChart();
        });
    });

    // 4. Modal Settings Toggling
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettings = document.getElementById('close-settings');
    const cancelSettings = document.getElementById('cancel-settings');
    const saveSettings = document.getElementById('save-settings');

    const backendUrlInput = document.getElementById('backend-url-input');
    const apiKeyInput = document.getElementById('api-key-input');

    settingsToggle.addEventListener('click', () => {
        backendUrlInput.value = localStorage.getItem('sia_backend_url_v2') || '';
        apiKeyInput.value = localStorage.getItem('sia_api_key') || 'test_token_123';
        settingsModal.classList.add('open');
    });

    const hideModal = () => settingsModal.classList.remove('open');
    closeSettings.addEventListener('click', hideModal);
    cancelSettings.addEventListener('click', hideModal);

    saveSettings.addEventListener('click', () => {
        const backendUrl = backendUrlInput.value.trim();
        localStorage.setItem('sia_backend_url_v2', backendUrl ? ApiClient.cleanUrl(backendUrl) : '');
        localStorage.setItem('sia_api_key', apiKeyInput.value.trim());
        hideModal();
        
        // Refresh active template contents with new variables
        const activeItem = document.querySelector('.template-list .template-item.active');
        if (activeItem) {
            const templateName = activeItem.dataset.template;
            // Only update editor value if they are not editing their own scratch custom script
            if (templateName !== 'custom') {
                const code = getTemplateCode(templateName);
                setEditorCode(code);
            }
        }
        
        consoleElement.textContent += `\n[System: Environment configuration updated]`;
    });

    // 5. Code Execution handler
    runBtn.addEventListener('click', async () => {
        const code = getEditorCode();
        if (!code.trim()) {
            consoleElement.textContent = "Error: Editor is empty. Please write some code.";
            consoleElement.classList.add('error');
            return;
        }

        // Set Loading state
        runBtn.disabled = true;
        loader.style.display = 'flex';
        statusElement.textContent = 'Executing...';
        consoleElement.textContent = 'Running quantum simulation job...\n';
        consoleElement.classList.remove('error');
        clearQuantumChart();

        const startTime = performance.now();

        try {
            const result = await ApiClient.runCode(code);
            const duration = ((performance.now() - startTime) / 1000).toFixed(2);
            
            if (result.success) {
                statusElement.textContent = 'Success';
                statusElement.style.color = 'var(--success-color)';
                
                let output = formatConsoleOutput(result.stdout || '');
                if (result.stderr) {
                    output += `\n[STDERR]\n${result.stderr}`;
                }
                
                consoleElement.textContent = output ? output : 'Execution completed successfully with empty output.';
                
                parseAndRenderQuantumOutput(result.quantum_results || result.stdout);
            } else {
                statusElement.textContent = 'Failed';
                statusElement.style.color = 'var(--error-color)';
                consoleElement.classList.add('error');
                
                let errorDetails = result.error || 'Execution failed';
                if (result.stderr) {
                    errorDetails += `\n\n[Traceback/STDERR]\n${result.stderr}`;
                }
                consoleElement.textContent = errorDetails;
            }
            
            consoleElement.textContent += `\n\n------------------------\n[Finished in ${duration}s]`;

        } catch (error) {
            statusElement.textContent = 'Connection Error';
            statusElement.style.color = 'var(--error-color)';
            consoleElement.classList.add('error');
            consoleElement.textContent = `API Connection Failure:\n${error.message}\n\nMake sure your FastAPI server is running and matches the Backend Base URL config.`;
        } finally {
            runBtn.disabled = false;
            loader.style.display = 'none';
        }
    });

    // 6. Quantum Output Parsing and Graphing
    function parseAndRenderQuantumOutput(source) {
        if (!source) return;
        if (Array.isArray(source)) {
            if (source.length > 0) {
                renderQuantumChart(source[source.length - 1]);
                setTimeout(() => {
                    const visualizerTabBtn = document.querySelector('.tab-btn[data-tab="visualizer"]');
                    if (visualizerTabBtn) {
                        visualizerTabBtn.click();
                    }
                }, 400);
            }
            return;
        }
        
        // Find 'Quantum execution results: ' signature in the output streams
        const pattern = /Quantum execution results:\s*(\{.*\})/g;
        let match;
        
        while ((match = pattern.exec(source)) !== null) {
            try {
                const quantumData = JSON.parse(match[1]);
                renderQuantumChart(quantumData);
                
                // Automatically switch tabs to visualizer on successful quantum run
                setTimeout(() => {
                    const visualizerTabBtn = document.querySelector('.tab-btn[data-tab="visualizer"]');
                    if (visualizerTabBtn) {
                        visualizerTabBtn.click();
                    }
                }, 400);
            } catch (err) {
                console.error("Failed to parse quantum signature payload:", err);
            }
        }
    }

    function formatConsoleOutput(stdout) {
        return stdout
            .split(/\r?\n/)
            .filter(line => !line.startsWith('Quantum execution results:'))
            .join('\n')
            .trimEnd();
    }

    function renderQuantumChart(data) {
        const noStatesMsg = document.getElementById('no-states-msg');
        const chartContent = document.getElementById('chart-content');
        const chartBars = document.getElementById('chart-bars');

        chartBars.innerHTML = '';
        if (!data.probabilities || Object.keys(data.probabilities).length === 0) {
            clearQuantumChart();
            return;
        }

        noStatesMsg.classList.add('hidden');
        chartContent.classList.remove('hidden');

        // Sort computational state keys numerically/alphabetically (e.g. '00', '01', '10', '11')
        const sortedStates = Object.keys(data.probabilities).sort();

        sortedStates.forEach(state => {
            const probability = data.probabilities[state];
            const percentage = (probability * 100).toFixed(1);

            const barWrapper = document.createElement('div');
            barWrapper.className = 'chart-bar-wrapper';
            barWrapper.innerHTML = `
                <div class="chart-bar-labels">
                    <span class="state-label">|${state}⟩</span>
                    <span class="percentage-label">${percentage}%</span>
                </div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: 0%"></div>
                </div>
            `;

            chartBars.appendChild(barWrapper);

            // Trigger animation
            setTimeout(() => {
                const barFill = barWrapper.querySelector('.bar-fill');
                if (barFill) {
                    barFill.style.width = `${percentage}%`;
                }
            }, 100);
        });
    }

    function clearQuantumChart() {
        document.getElementById('no-states-msg').classList.remove('hidden');
        document.getElementById('chart-content').classList.add('hidden');
        document.getElementById('chart-bars').innerHTML = '';
    }
});
