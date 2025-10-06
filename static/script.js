document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const resultsContainer = document.getElementById('resultsContainer');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('error-message');

    const API_URL = 'http://127.0.0.1:8000/api';

    const performSearch = async () => {
        const query = searchInput.value.trim();
        const limit = document.getElementById('resultLimit').value;

        if (!query) {
            resultsContainer.innerHTML = '';
            return;
        }

        // Show loading indicator and clear previous results/errors
        loadingIndicator.classList.remove('hidden');
        resultsContainer.innerHTML = '';
        errorMessage.classList.add('hidden');

        try {
            const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&limit=${limit}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const results = await response.json();
            displayResults(results);

        } catch (error) {
            console.error('Search failed:', error);
            showError(error.message);
        } finally {
            // Hide loading indicator
            loadingIndicator.classList.add('hidden');
        }
    };

    const displayResults = (results) => {
        if (results.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center;">No similar root words found.</p>';
            return;
        }

        results.forEach((result, index) => {
            const card = document.createElement('div');
            card.className = 'result-card';
            // Stagger the animation
            card.style.animationDelay = `${index * 0.1}s`;

            // Create table rows for word occurrences
            const occurrencesRows = result.occurrences.map(word => `
                <tr>
                    <td dir="rtl" class="arabic-text">${word.arabic_word}</td>
                    <td>${word.transliteration}</td>
                    <td>${word.english_text}</td>
                    <td>
                        <a href="${word.morphology_url}" target="_blank" title="View morphology">
                            ${word.verse_reference}
                        </a>
                    </td>
                    <td class="similarity-cell ${word.similarity_score > 90 ? 'high-match' : word.similarity_score > 75 ? 'medium-match' : 'low-match'}">
                        ${word.similarity_score}%
                    </td>
                </tr>
            `).join('');

            card.innerHTML = `
                <div class="card-header">
                    <h2>${result.sequence}</h2>
                    <div class="meta">
                        <span>Letter: ${result.letter}</span>
                        <span>Category: ${result.category}</span>
                        <span class="similarity">Best Match: ${result.best_match_score}%</span>
                    </div>
                </div>
                <div class="word-occurrences">
                    <table>
                        <thead>
                            <tr>
                                <th>Arabic</th>
                                <th>Transliteration</th>
                                <th>Meaning</th>
                                <th>Verse</th>
                                <th>Match %</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${occurrencesRows}
                        </tbody>
                    </table>
                </div>
            `;
            resultsContainer.appendChild(card);
        });
    };

    const showError = (message) => {
        errorMessage.textContent = `An error occurred: ${message}`;
        errorMessage.classList.remove('hidden');
    };

    // Event Listeners
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            performSearch();
        }
    });
});
