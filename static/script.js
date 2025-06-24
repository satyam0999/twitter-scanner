document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysisForm');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const resultsDiv = document.getElementById('results');
    const analyzeBtn = document.getElementById('analyzeBtn');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const numTweets = document.getElementById('num_tweets').value;
        
        if (!username) {
            showError('Please enter a username');
            return;
        }

        // Hide previous results and errors
        hideElement(errorDiv);
        hideElement(resultsDiv);
        
        // Show loading
        showElement(loadingDiv);
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

        try {
            console.log('Sending request to /analyze with:', { username, num_tweets: parseInt(numTweets) });
            
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    num_tweets: parseInt(numTweets)
                })
            });

            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);

            const data = await response.json();
            console.log('Response data:', data);

            if (response.ok && data.success) {
                // Redirect to results page
                console.log('Redirecting to:', `/results/${data.analysis_id}`);
                window.location.href = `/results/${data.analysis_id}`;
            } else {
                showError(data.error || 'Analysis failed. Please try again.');
            }
        } catch (error) {
            console.error('Error:', error);
            showError('Network error. Please check your connection and try again.');
        } finally {
            // Reset button
            hideElement(loadingDiv);
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Account';
        }
    });

    function showError(message) {
        document.getElementById('errorMessage').textContent = message;
        showElement(errorDiv);
    }

    function showElement(element) {
        element.classList.remove('hidden');
    }

    function hideElement(element) {
        element.classList.add('hidden');
    }

    // Add some visual feedback for the input
    const usernameInput = document.getElementById('username');
    usernameInput.addEventListener('input', function() {
        // Remove @ if user types it
        if (this.value.startsWith('@')) {
            this.value = this.value.substring(1);
        }
    });
});