// Backend and API Communication Client

const ApiClient = {
    DEPLOYED_BACKEND_URL: 'https://code-editor-pq97.onrender.com',

    getBackendUrl() {
        const storedUrl = localStorage.getItem('sia_backend_url');
        if (storedUrl && storedUrl.trim() !== '') {
            return this.cleanUrl(storedUrl);
        }
        if (window.location.hostname === 'code-editor-1-l8ec.onrender.com') {
            return this.DEPLOYED_BACKEND_URL;
        }
        // Default to same origin where static page is served, useful when FastAPI serves the frontend.
        return window.location.origin;
    },

    cleanUrl(url) {
        return url.trim().replace(/^['"]|['"]$/g, '').replace(/\/$/, '');
    },

    getApiKey() {
        return localStorage.getItem('sia_api_key') || 'test_token_123';
    },

    async parseJsonResponse(response) {
        const text = await response.text();
        if (!text.trim()) {
            throw new Error(`Server returned an empty response from ${response.url}`);
        }

        try {
            return JSON.parse(text);
        } catch (error) {
            throw new Error(`Server returned a non-JSON response from ${response.url}`);
        }
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
                const errorData = await this.parseJsonResponse(response).catch(() => ({}));
                const message = errorData.detail || `Server returned status code ${response.status}`;
                throw new Error(message);
            }

            return await this.parseJsonResponse(response);
        } catch (error) {
            console.error('API Run Error:', error);
            throw new Error(error.message || 'Network connection failed. Verify backend service is running.');
        }
    }
};
