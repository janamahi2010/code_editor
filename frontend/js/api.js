// Backend and API Communication Client

const ApiClient = {
    getBackendUrl() {
        const storedUrl = localStorage.getItem('sia_backend_url');
        if (storedUrl && storedUrl.trim() !== '') {
            return storedUrl.trim().replace(/\/$/, '');
        }
        // Default to same origin where static page is served
        return window.location.origin;
    },

    getApiKey() {
        return localStorage.getItem('sia_api_key') || 'test_token_123';
    },

    async runCode(code) {
        const baseUrl = this.getBackendUrl();
        const url = `${baseUrl}/run`;
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ code })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const message = errorData.detail || `Server returned status code ${response.status}`;
                throw new Error(message);
            }

            return await response.json();
        } catch (error) {
            console.error('API Run Error:', error);
            throw new Error(error.message || 'Network connection failed. Verify backend service is running.');
        }
    }
};
