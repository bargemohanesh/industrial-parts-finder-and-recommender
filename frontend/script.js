/**
 * Industrial Parts Product Finder - Frontend JavaScript
 */

class ProductFinder {
    constructor() {
        this.apiBaseUrl = '/api';
        this.systemInitialized = false;
        this.isSearching = false;
        this.recognition = null;
        this.isRecording = false;

        this.initializeElements();
        this.bindEvents();
        this.initializeSpeechRecognition();
        this.checkSystemStatus();
    }

    initializeElements() {
        // Sections
        this.welcomeSection = document.getElementById('welcome-section');
        this.searchSection = document.getElementById('search-section');

        // Buttons
        this.initButton = document.getElementById('init-button');
        this.searchBtn = document.getElementById('search-btn');
        this.voiceBtn = document.getElementById('voice-btn');

        // Inputs
        this.searchInput = document.getElementById('search-input');

        // Status
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusText = document.getElementById('status-text');
        this.initProgress = document.getElementById('init-progress');
        this.initStatus = document.getElementById('init-status');

        // Results
        this.resultsContainer = document.getElementById('results-container');

        // Overlays
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.loadingText = document.getElementById('loading-text');

        // Toast
        this.toast = document.getElementById('toast');
        this.toastMessage = document.getElementById('toast-message');

        // Other
        this.charCounter = document.getElementById('char-counter');
        this.voiceStatus = document.getElementById('voice-status');
    }

    bindEvents() {
        // Initialize button
        this.initButton.addEventListener('click', () => this.initializeSystem());

        // Search
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        this.searchInput.addEventListener('input', () => this.updateCharCounter());

        // Voice
        this.voiceBtn.addEventListener('click', () => this.toggleVoiceInput());

        // Example buttons
        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.currentTarget.dataset.query;
                this.searchInput.value = query;
                this.updateCharCounter();
                if (this.systemInitialized) {
                    this.performSearch();
                }
            });
        });

        // Help/About links
        document.getElementById('help-link')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.searchInput.value = 'help';
            if (this.systemInitialized) this.performSearch();
        });
    }

    initializeSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            this.recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';

            this.recognition.onstart = () => {
                this.isRecording = true;
                this.voiceBtn.classList.add('recording');
                this.voiceStatus.textContent = 'Listening...';
            };

            this.recognition.onresult = (event) => {
                let finalTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    }
                }

                if (finalTranscript) {
                    this.searchInput.value = finalTranscript;
                    this.updateCharCounter();
                    this.voiceStatus.textContent = 'Voice input captured';
                    setTimeout(() => this.voiceStatus.textContent = '', 2000);
                }
            };

            this.recognition.onerror = (event) => {
                this.isRecording = false;
                this.voiceBtn.classList.remove('recording');
                this.voiceStatus.textContent = `Error: ${event.error}`;
                setTimeout(() => this.voiceStatus.textContent = '', 3000);
            };

            this.recognition.onend = () => {
                this.isRecording = false;
                this.voiceBtn.classList.remove('recording');
                if (this.voiceStatus.textContent === 'Listening...') {
                    this.voiceStatus.textContent = '';
                }
            };
        } else {
            this.voiceBtn.disabled = true;
            this.voiceBtn.title = 'Speech recognition not supported';
            this.voiceBtn.style.opacity = '0.5';
        }
    }

    toggleVoiceInput() {
        if (!this.recognition) return;

        if (this.isRecording) {
            this.recognition.stop();
        } else {
            this.recognition.start();
        }
    }

    updateCharCounter() {
        const length = this.searchInput.value.length;
        this.charCounter.textContent = `${length}/500`;
        this.searchBtn.disabled = length === 0;
    }

    async checkSystemStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/status`);
            const status = await response.json();

            if (status.initialized) {
                this.systemInitialized = true;
                this.showSearchInterface();
                this.updateStatus('ready', 'System Ready');
            } else {
                this.updateStatus('initializing', 'Not Initialized');
            }
        } catch (error) {
            console.error('Status check failed:', error);
            this.updateStatus('error', 'Connection Error');
        }
    }

    async initializeSystem() {
        try {
            this.initButton.style.display = 'none';
            this.initProgress.classList.add('show');
            this.initStatus.textContent = 'Initializing system...';
            this.updateStatus('initializing', 'Initializing...');

            this.showLoading('Initializing Product Finder...');

            const response = await fetch(`${this.apiBaseUrl}/initialize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();

            this.hideLoading();

            if (result.status === 'success') {
                this.systemInitialized = true;
                this.showToast(`System initialized! ${result.stats.products} products loaded.`, 'success');
                this.updateStatus('ready', 'System Ready');

                setTimeout(() => {
                    this.showSearchInterface();
                }, 500);
            } else {
                throw new Error(result.message);
            }

        } catch (error) {
            console.error('Initialization error:', error);
            this.hideLoading();
            this.showToast(`Initialization failed: ${error.message}`, 'error');
            this.updateStatus('error', 'Initialization Failed');
            this.initButton.style.display = 'inline-flex';
            this.initProgress.classList.remove('show');
        }
    }

    showSearchInterface() {
        this.welcomeSection.style.display = 'none';
        this.searchSection.style.display = 'block';
        this.searchInput.focus();
    }

    async performSearch() {
        const query = this.searchInput.value.trim();

        if (!query || this.isSearching) return;

        if (!this.systemInitialized) {
            this.showToast('Please initialize the system first', 'error');
            return;
        }

        try {
            this.isSearching = true;
            this.searchBtn.disabled = true;
            this.showLoading('Searching products...');

            const response = await fetch(`${this.apiBaseUrl}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, max_results: 5 })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            this.hideLoading();
            this.displayResults(result);

        } catch (error) {
            console.error('Search error:', error);
            this.hideLoading();
            this.showToast(`Search failed: ${error.message}`, 'error');
        } finally {
            this.isSearching = false;
            this.searchBtn.disabled = false;
        }
    }

    displayResults(result) {
        this.resultsContainer.innerHTML = '';

        const resultCard = document.createElement('div');
        resultCard.className = 'result-card';

        // AI Response
        const aiResponse = document.createElement('div');
        aiResponse.className = 'ai-response';
        aiResponse.innerHTML = `
            <h3>
                <i class="fas fa-robot"></i>
                AI Response
            </h3>
            <div class="ai-response-content">
                ${this.formatResponse(result.response)}
            </div>
            <div style="margin-top: 12px; font-size: 12px; color: #6b7280;">
                <i class="fas fa-clock"></i> Processed in ${result.processing_time.toFixed(2)}s
            </div>
        `;
        resultCard.appendChild(aiResponse);

        // Products
        if (result.products && result.products.length > 0) {
            const productsSection = document.createElement('div');
            productsSection.innerHTML = '<h3 style="margin: 24px 0 16px 0; color: #1f2937;"><i class="fas fa-box"></i> Products Found</h3>';

            const productsGrid = document.createElement('div');
            productsGrid.className = 'products-grid';

            result.products.forEach(product => {
                const productCard = this.createProductCard(product);
                productsGrid.appendChild(productCard);
            });

            productsSection.appendChild(productsGrid);
            resultCard.appendChild(productsSection);
        }

        // Recommendations
        if (result.recommendations && result.recommendations.length > 0) {
            const recsSection = document.createElement('div');
            recsSection.className = 'recommendations-section';
            recsSection.innerHTML = `
                <h3>
                    <i class="fas fa-shopping-cart"></i>
                    Frequently Bought Together
                </h3>
            `;

            const recsList = document.createElement('div');
            recsList.className = 'recommendations-list';

            result.recommendations.forEach(rec => {
                const recItem = this.createRecommendationItem(rec);
                recsList.appendChild(recItem);
            });

            recsSection.appendChild(recsList);
            resultCard.appendChild(recsSection);
        }

        this.resultsContainer.appendChild(resultCard);

        // Scroll to results
        this.resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    createProductCard(product) {
        const card = document.createElement('div');
        card.className = 'product-card';

        card.innerHTML = `
            <div class="product-header">
                <div>
                    <div class="product-name">${this.escapeHtml(product.name)}</div>
                    <span class="product-reference">${this.escapeHtml(product.reference)}</span>
                </div>
            </div>
            <div class="product-meta">
                <div class="meta-item">
                    <i class="fas fa-folder"></i>
                    <span>${this.escapeHtml(product.category)}</span>
                </div>
                <div class="meta-item">
                    <i class="fas fa-file-alt"></i>
                    <span>Page ${product.page}</span>
                </div>
                <div class="meta-item">
                    <i class="fas fa-book"></i>
                    <span>${this.escapeHtml(product.catalog)}</span>
                </div>
            </div>
            <div class="product-description">
                ${this.escapeHtml(product.description)}
            </div>
        `;

        return card;
    }

    createRecommendationItem(rec) {
        const item = document.createElement('div');
        item.className = 'recommendation-item';

        item.innerHTML = `
            <div class="recommendation-info">
                <h4>${this.escapeHtml(rec.name)}</h4>
                <div class="recommendation-reason">
                    <i class="fas fa-info-circle"></i>
                    ${this.escapeHtml(rec.reason)}
                </div>
            </div>
            <span class="recommendation-ref">${this.escapeHtml(rec.reference)}</span>
        `;

        return item;
    }

    formatResponse(text) {
        // Convert markdown-like formatting to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^(.)/g, '<p>$1')
            .replace(/(.)$/g, '$1</p>')
            .replace(/<p><\/p>/g, '');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    updateStatus(status, text) {
        this.statusText.textContent = text;
        this.statusIndicator.className = 'status-indicator ' + status;
    }

    showLoading(text) {
        this.loadingText.textContent = text;
        this.loadingOverlay.classList.add('show');
    }

    hideLoading() {
        this.loadingOverlay.classList.remove('show');
    }

    showToast(message, type = 'info') {
        this.toastMessage.textContent = message;
        this.toast.className = 'toast show ' + type;

        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 4000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.productFinderApp = new ProductFinder();
});