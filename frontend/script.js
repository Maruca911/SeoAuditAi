document.getElementById('auditForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('urlInput').value;
    const resultDiv = document.getElementById('result');
    const submitBtn = document.getElementById('submitBtn');

    // Disable button during request
    submitBtn.disabled = true;
    submitBtn.textContent = 'Running Audit...';
    resultDiv.innerHTML = '<p>Loading...</p>';

    try {
        const response = await fetch('https://seoauditai.onrender.com/audit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        // Adjust based on actual API response structure
        if (data.status === 'success') {
            resultDiv.innerHTML = formatResults(data.data);
        } else {
            resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.message || 'Audit failed'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Run Audit';
    }
});

// Format API response into HTML (customize based on actual response)
function formatResults(data) {
    // Example: Assuming data contains issues like { errors: [], warnings: [] }
    let html = '<h3>Audit Results</h3>';
    if (data.errors && data.errors.length) {
        html += '<h4>Errors</h4><ul class="list-group mb-3">';
        data.errors.forEach(error => {
            html += `<li class="list-group-item">${error}</li>`;
        });
        html += '</ul>';
    }
    if (data.warnings && data.warnings.length) {
        html += '<h4>Warnings</h4><ul class="list-group mb-3">';
        data.warnings.forEach(warning => {
            html += `<li class="list-group-item">${warning}</li>`;
        });
        html += '</ul>';
    }
    if (!data.errors && !data.warnings) {
        html += '<div class="alert alert-success">No issues found!</div>';
    }
    return html;
}
