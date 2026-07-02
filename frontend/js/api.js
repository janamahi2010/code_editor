// Backend and API Communication Client

const ApiClient = {
    // Real external HDQS quantum service (separate infrastructure, not part of this repo).
    // Used only as the base_url baked into sandboxed script templates.
    HDQS_SERVICE_URL: 'http://31.97.239.213:8000',

    // Execution backend: this repo's own FastAPI app, which serves /run and also
    // serves the frontend it's running (see main.py's StaticFiles mount). Same-origin
    // works whenever this app is accessed via that combined service (incl. local dev).
    //
    // The frontend is additionally deployed on its own as a static site (no backend
    // attached), so requests from that host must be redirected to the real backend.
    STATIC_FRONTEND_HOST: 'code-editor-1-l8ec.onrender.com',
    COMBINED_SERVICE_URL: 'https://code-editor-pq97.onrender.com',

    getBackendUrl() {
        const storedUrl = localStorage.getItem('sia_backend_url_v2');
        if (storedUrl && storedUrl.trim() !== '') {
            return this.cleanUrl(storedUrl);
        }
        if (window.location.hostname === this.STATIC_FRONTEND_HOST) {
            return this.COMBINED_SERVICE_URL;
        }
        return window.location.origin;
    },

    getHdqsServiceUrl() {
        return this.HDQS_SERVICE_URL;
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
