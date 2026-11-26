// Function to generate correct morphology URL from verse reference
const generateMorphologyUrl = (verseRef) => {
    // References look like "(2:255:3)": chapter, verse, word position
    const [chapter, verse] = verseRef.replace(/[()]/g, '').split(':').map(num => parseInt(num, 10));
    return `https://corpus.quran.com/wordbyword.jsp?chapter=${chapter}&verse=${verse}`;
};

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    // Search Tab
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const resultsContainer = document.getElementById('resultsContainer');
    
    // Chat Tab
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const generateAllButton = document.getElementById('generateAllButton');
    const allNamesContainer = document.getElementById('all-names-container');
    const copyAllButton = document.getElementById('copyAllButton');
    const copyUnsuccessfulButton = document.getElementById('copyUnsuccessfulButton');

    // Shared
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('error-message');
    const tabs = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    // --- State ---
    let sessionToken = null; // To hold the session token for the chat

    // --- API Configuration ---
    const API_URL = '/api';

    // --- Tab Switching Logic ---
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Deactivate all tabs and content
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Activate the clicked tab and its content
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });


    // --- Semantic Search Logic ---
    const performSearch = async () => {
        const query = searchInput.value.trim();
        const limit = document.getElementById('resultLimit').value;
        const minSimilarity = parseFloat(document.getElementById('minSimilarity').value) || 0;

        if (!query) {
            resultsContainer.innerHTML = '';
            return;
        }

        // Show loading indicator and clear previous results/errors
        loadingIndicator.classList.remove('hidden');
        resultsContainer.innerHTML = '';
        errorMessage.classList.add('hidden');

        try {
            const response = await fetch(
                `${API_URL}/search?q=${encodeURIComponent(query)}&limit=${limit}&min_similarity=${minSimilarity}`
            );
            
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
                        <a href="${generateMorphologyUrl(word.verse_reference)}" target="_blank" title="View morphology">
                            ${word.verse_reference}
                        </a>
                    </td>
                    <td class="similarity-cell ${getSimilarityClass(word.similarity_score)}">
                        ${word.similarity_score.toFixed(0)}%
                    </td>
                </tr>
            `).join('');

            card.innerHTML = `
                <div class="card-header">
                    <h2>${result.sequence}</h2>
                    <div class="meta">
                        <span>Letter: ${result.letter}</span>
                        <span>Category: ${result.category}</span>
                        <span class="similarity">Best Match: ${result.best_match_score.toFixed(0)}%</span>
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

    const getSimilarityClass = (score) => {
        if (score > 85) return 'high-match';
        if (score > 65) return 'medium-match';
        return 'low-match';
    };

    const showError = (message) => {
        errorMessage.textContent = `An error occurred: ${message}`;
        errorMessage.classList.remove('hidden');
    };

    // --- Chat Logic ---
    const sendChatMessage = async () => {
        const query = chatInput.value.trim();
        if (!query) return;

        displayMessage(query, 'user');
        chatInput.value = '';
        showLoadingIndicator(true, 'chat');

        try {
            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, session_token: sessionToken }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const chatResponse = await response.json();
            sessionToken = chatResponse.session_token; // Store the session token

            if (chatResponse.suggestions && chatResponse.suggestions.length > 0) {
                displaySuggestions(chatResponse.suggestions);
            } else {
                displayMessage("I couldn't find any specific name suggestions for that. Could you try a different meaning?", 'ai');
            }

        } catch (error) {
            console.error('Chat failed:', error);
            displayMessage(`Sorry, an error occurred: ${error.message}`, 'ai-error');
        } finally {
            showLoadingIndicator(false, 'chat');
        }
    };

    const displayMessage = (text, sender) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = text; // Use innerHTML to allow for formatted cards

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to bottom
    };

    const displaySuggestions = (suggestions) => {
        // Create a separate message bubble for each suggestion
        suggestions.forEach(suggestion => {
            const cardHtml = createNameCard(suggestion);
            displayMessage(cardHtml, 'ai');
        });
    };

    const createNameCard = (suggestion) => {
        // This function creates the HTML for a single name suggestion item.
        const rootInfo = suggestion.root ? `, Root: ${suggestion.root}` : '';
        return `
            <div class="name-suggestion-item">
                <div class="name-english"><strong>${suggestion.name}</strong></div>
                <div class="name-meaning">${suggestion.meaning}</div>
                <div class="name-meta">(Gender: ${suggestion.gender || 'Unspecified'}${rootInfo})</div>
            </div>
        `;
    };

    const showLoadingIndicator = (show, context = 'search') => {
        if (context === 'chat') {
            // For chat, we can show a typing indicator
            let indicator = document.getElementById('typing-indicator');
            if (show) {
                if (!indicator) {
                    indicator = document.createElement('div');
                    indicator.id = 'typing-indicator';
                    indicator.className = 'message ai-message';
                    indicator.innerHTML = `<div class="message-content"><div class="spinner"></div></div>`;
                    chatMessages.appendChild(indicator);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            } else {
                if (indicator) {
                    indicator.remove();
                }
            }
        } else {
            // Original behavior for search and batch
            loadingIndicator.classList.toggle('hidden', !show);
        }
    };


    // --- Event Listeners ---
    // Search
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') performSearch();
    });
    document.getElementById('resultLimit').addEventListener('change', performSearch);
    document.getElementById('minSimilarity').addEventListener('change', performSearch);

    // Chat
    sendButton.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') sendChatMessage();
    });

    // Batch Generation
    generateAllButton.addEventListener('click', toggleGeneration);
    copyAllButton.addEventListener('click', copyAllGeneratedNames);
    copyUnsuccessfulButton.addEventListener('click', copyUnsuccessfulRoots);

    // --- State for Batch Generation ---
    let allGeneratedNames = [];
    let allUnsuccessfulRoots = [];
    let isGenerationPaused = true;
    let currentOffset = 0;
    const pageSize = 10;
    let totalRoots = 0;

    // --- Batch Generation Logic ---
    function toggleGeneration() {
        isGenerationPaused = !isGenerationPaused;
        if (!isGenerationPaused) {
            generateAllButton.textContent = 'Pause Generation';
            generateAllButton.classList.add('secondary-action');
            handleGenerateAll();
        } else {
            generateAllButton.textContent = 'Resume Generation';
            generateAllButton.classList.remove('secondary-action');
        }
    }

    async function handleGenerateAll() {
        if (isGenerationPaused) return;

        showLoadingIndicator(true, 'batch');
        errorMessage.classList.add('hidden');

        // Only clear the container if starting from the beginning
        if (currentOffset === 0) {
            allNamesContainer.innerHTML = '';
            allGeneratedNames = [];
            allUnsuccessfulRoots = [];
            copyUnsuccessfulButton.classList.add('hidden');
        }

        try {
            // 1. Fetch a page of root words
            const response = await fetch(`${API_URL}/root-words?skip=${currentOffset}&limit=${pageSize}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            const rootWords = data.root_words;
            totalRoots = data.total;

            // 2. Process the fetched root words in smaller batches for the LLM
            const llmBatchSize = 5;
            for (let i = 0; i < rootWords.length; i += llmBatchSize) {
                if (isGenerationPaused) {
                    showLoadingIndicator(false, 'batch');
                    return; // Stop processing if paused
                }
                const batch = rootWords.slice(i, i + llmBatchSize);

                // 3. Call the generate-names endpoint for each small batch
                const generateResponse = await fetch(`${API_URL}/generate-names`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ root_words: batch }),
                });

                if (!generateResponse.ok) {
                    console.warn(`LLM Batch failed. Continuing...`);
                    continue;
                }

                const result = await generateResponse.json();
                const suggestions = result.suggestions;
                const unsuccessfulRoots = result.unsuccessful_roots;

                // 4. Store and display the results
                if (unsuccessfulRoots && unsuccessfulRoots.length > 0) {
                    allUnsuccessfulRoots.push(...unsuccessfulRoots);
                }
                if (suggestions && suggestions.length > 0) {
                    allGeneratedNames.push(...suggestions);
                }
                // Always display the batch card, even if there are no suggestions
                displayBatchSuggestions(suggestions, batch, unsuccessfulRoots);
            }

            currentOffset += pageSize;

            if (currentOffset < totalRoots && !isGenerationPaused) {
                // Automatically fetch the next page
                handleGenerateAll();
            } else {
                // All pages are processed or paused
                isGenerationPaused = true;
                generateAllButton.textContent = 'Generation Complete';
                generateAllButton.disabled = true;
                copyAllButton.classList.remove('hidden');
                if (allUnsuccessfulRoots.length > 0) {
                    copyUnsuccessfulButton.classList.remove('hidden');
                }
                showLoadingIndicator(false, 'batch');
            }

        } catch (error) {
            console.error('Batch generation failed:', error);
            showError(error.message);
            isGenerationPaused = true;
            generateAllButton.textContent = 'Start Generation';
            showLoadingIndicator(false, 'batch');
        }
    }

    function displayBatchSuggestions(suggestions, batchRoots, unsuccessfulRoots) {
        allNamesContainer.classList.remove('hidden');
        const batchContainer = document.createElement('div');
        batchContainer.className = 'batch-result-card';

        const rootWordsHtml = batchRoots.map(root => 
            `<span class="root-word-tag">${root.sequence}</span>`
        ).join(' ');

        let suggestionsHtml = suggestions.map(createNameCard).join('');
        
        let unsuccessfulHtml = '';
        if (unsuccessfulRoots && unsuccessfulRoots.length > 0) {
            unsuccessfulHtml = `
                <div class="unsuccessful-roots">
                    <h5>Roots with no name suggestions:</h5>
                    ${unsuccessfulRoots.map(root => `<div class="unsuccessful-item"><strong>${root.sequence}:</strong> ${root.english_text}</div>`).join('')}
                </div>
            `;
        }

        batchContainer.innerHTML = `
            <div class="batch-header">
                <h4>Names from Roots: ${rootWordsHtml}</h4>
            </div>
            <div class="batch-suggestions">
                ${suggestionsHtml || '<p>No names were generated for this batch.</p>'}
            </div>
            ${unsuccessfulHtml}
        `;
        allNamesContainer.appendChild(batchContainer);
        allNamesContainer.scrollTop = allNamesContainer.scrollHeight;
    }

    function copyAllGeneratedNames() {
        const namesJson = JSON.stringify(allGeneratedNames, null, 2);
        navigator.clipboard.writeText(namesJson).then(() => {
            alert('All generated names copied to clipboard as JSON!');
        }, (err) => {
            console.error('Could not copy text: ', err);
            alert('Failed to copy names.');
        });
    }

    function copyUnsuccessfulRoots() {
        const rootsText = allUnsuccessfulRoots.map(r => `${r.sequence} - ${r.english_text}`).join('\n');
        navigator.clipboard.writeText(rootsText).then(() => {
            alert('All unsuccessful roots copied to clipboard!');
        }, (err) => {
            console.error('Could not copy text: ', err);
            alert('Failed to copy roots.');
        });
    }
});
