// static/script.js - Frontend for MariaDB Query Optimizer

document.addEventListener('DOMContentLoaded', () => {
    const sqlTextarea = document.getElementById('sql');
    const runBtn = document.getElementById('run');
    const clearBtn = document.getElementById('clear');
    const sandboxSelect = document.getElementById('sandbox');
    const messageDiv = document.getElementById('message');
    const resultsDiv = document.getElementById('results');

    // Run analysis
    runBtn.addEventListener('click', async () => {
        const sql = sqlTextarea.value.trim();
        if (!sql) {
            showMessage('Please enter a SQL query.', 'error');
            return;
        }

        showMessage('Analyzing query...', 'info');
        runBtn.disabled = true;

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sql: sql,
                    run_in_sandbox: sandboxSelect.value === 'true'
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Analysis failed');
            }

            renderResults(data);
            showMessage('Analysis complete!', 'success');
        } catch (error) {
            showMessage(`Error: ${error.message}`, 'error');
            console.error(error);
        } finally {
            runBtn.disabled = false;
        }
    });

    // Clear
    clearBtn.addEventListener('click', () => {
        sqlTextarea.value = '';
        messageDiv.classList.add('hidden');
        resultsDiv.classList.add('hidden');
    });

    // Analyze schema
    window.analyzeSchema = async () => {
        showMessage('Analyzing schema...', 'info');

        try {
            const response = await fetch('/analyze-schema', { method: 'POST' });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Schema analysis failed');
            }

            const schemaResults = document.getElementById('schema-results');
            schemaResults.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        } catch (error) {
            showMessage(`Schema analysis error: ${error.message}`, 'error');
        }
    };
});

function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.classList.remove('hidden');
}

function renderResults(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.classList.remove('hidden');

    // Summary
    document.getElementById('summary').textContent = JSON.stringify({
        original_query: data.original_query,
        optimized_query: data.optimized_query,
        database: data.database_used
    }, null, 2);

    // Optimized Query
    document.getElementById('opt-query').textContent = data.optimized_query;

    // Recommendations
    const analysis = data.analysis || {};
    document.getElementById('recommendations').textContent = JSON.stringify(analysis.recommendations || [], null, 2);

    // Warnings
    document.getElementById('warnings').textContent = JSON.stringify(analysis.warnings || [], null, 2);

    // Impact
    document.getElementById('impact').textContent = analysis.estimated_impact || 'N/A';

    // AI Notes
    const aiDetails = analysis.ai_details || {};
    document.getElementById('ai-notes').textContent = JSON.stringify(aiDetails, null, 2);

    // Explain Plan
    document.getElementById('plan').textContent = JSON.stringify(data.explain_plan, null, 2);

    // Sample Rows
    document.getElementById('rows').textContent = JSON.stringify(data.sample_rows, null, 2);

    // Raw JSON
    document.getElementById('raw').textContent = JSON.stringify(data, null, 2);
}
