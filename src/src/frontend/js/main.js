document.addEventListener('DOMContentLoaded', function() {
    console.log("Main.js loaded");

    // Counter for generating unique message IDs
    let messageIdCounter = 0;

    function triggerTransition(url) {
        console.log("Triggering transition to:", url);
        const spinner = document.getElementById('loadingSpinner');
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '0';
        spinner.style.display = 'flex';
        setTimeout(() => {
            window.location.href = url;
        }, 500);
    }

    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const messageArea = document.getElementById('messageArea');
    const logoutBtn = document.getElementById('logoutBtn');
    const suggestions = document.querySelectorAll('.suggestion-chip');
    const sendBtn = document.querySelector('.send-btn');

    // Track the current typing indicator ID
    let currentLoadingId = null;
    // Track whether a request is in progress
    let isProcessing = false;

    addMessage('bot', 'Hello! I’m your GBS HR Assistant. How can I help with HR policies today?', true);

    if (suggestions) {
        suggestions.forEach(suggestion => {
            suggestion.addEventListener('click', () => {
                console.log("Suggestion clicked:", suggestion.textContent);
                if (!isProcessing) {
                    userInput.value = suggestion.textContent;
                    chatForm.dispatchEvent(new Event('submit'));
                }
            });
        });
    }

    // Function to toggle input and button state
    function toggleInputState(disabled) {
        userInput.disabled = disabled;
        sendBtn.disabled = disabled;
        sendBtn.style.opacity = disabled ? '0.5' : '1';
        sendBtn.style.cursor = disabled ? 'not-allowed' : 'pointer';
        suggestions.forEach(chip => {
            chip.disabled = disabled;
            chip.style.opacity = disabled ? '0.5' : '1';
        });
    }

    if (chatForm) {
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log("Chat form submitted");

            if (isProcessing) {
                console.log("Request in progress, ignoring submission");
                return;
            }

            const question = userInput.value.trim();
            if (!question) {
                console.log("Empty input, ignoring");
                return;
            }

            // Disable input and button
            isProcessing = true;
            toggleInputState(true);

            // Add user message
            const userMessageId = addMessage('user', question);
            console.log("User message added with ID:", userMessageId);

            // Clear input and focus
            userInput.value = '';
            userInput.focus();

            // Remove any existing typing indicator
            if (currentLoadingId) {
                console.log("Removing existing typing indicator with ID:", currentLoadingId);
                removeMessage(currentLoadingId);
                currentLoadingId = null;
            }

            // Add new typing indicator
            currentLoadingId = addMessage('bot', '<div class="typing-indicator"><span></span><span></span><span></span></div>', false);
            console.log("Typing indicator added with ID:", currentLoadingId);

            try {
                console.log("Sending chat request:", question);
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ question: question })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                console.log("Chat response received:", data);

                // Remove typing indicator
                if (currentLoadingId) {
                    console.log("Removing typing indicator with ID:", currentLoadingId);
                    removeMessage(currentLoadingId);
                    currentLoadingId = null;
                } else {
                    console.error("Typing indicator ID not found");
                }

                // Add bot response
                addMessage('bot', data.answer, true);

            } catch (error) {
                console.error("Chat error:", error.message);
                if (currentLoadingId) {
                    removeMessage(currentLoadingId);
                    currentLoadingId = null;
                }
                addMessage('bot', 'Sorry, I encountered an error. Please try again.', true);
            } finally {
                // Re-enable input and button
                isProcessing = false;
                toggleInputState(false);
            }
        });
    } else {
        console.error("Chat form not found");
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Logout clicked");
            triggerTransition('/logout');
        });
    }

    function addMessage(type, content, animate = false) {
        console.log(`Adding ${type} message:`, content);
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${type}-message`);
        if (animate) {
            messageDiv.style.opacity = '0';
            messageDiv.style.transform = 'translateY(10px)';
            messageDiv.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        }

        if (type === 'bot') {
            const avatar = document.createElement('div');
            avatar.classList.add('bot-avatar');
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
            messageDiv.appendChild(avatar);

            const contentDiv = document.createElement('div');
            contentDiv.classList.add('message-content');

            try {
                const parts = content.split('\n\nSources: ');
                const mainContent = parts[0];
                const sources = parts[1] ? parts[1].replace(/[\[\]]/g, '') : '';

                contentDiv.innerHTML = marked.parse(mainContent);

                if (sources) {
                    const sourcesDiv = document.createElement('div');
                    sourcesDiv.classList.add('sources');
                    sourcesDiv.textContent = `Sources: ${sources}`;
                    contentDiv.appendChild(sourcesDiv);
                }
            } catch (error) {
                console.error("Markdown parsing error:", error);
                contentDiv.innerHTML = content;
            }
            messageDiv.appendChild(contentDiv);
        } else {
            const contentDiv = document.createElement('div');
            contentDiv.classList.add('message-content');
            contentDiv.textContent = content;
            messageDiv.appendChild(contentDiv);
        }

        // Generate unique ID using counter
        const id = `msg_${messageIdCounter++}`;
        messageDiv.setAttribute('data-id', id);

        messageArea.appendChild(messageDiv);
        messageArea.scrollTop = messageArea.scrollHeight;

        if (animate) {
            setTimeout(() => {
                messageDiv.style.opacity = '1';
                messageDiv.style.transform = 'translateY(0)';
            }, 10);
        }

        console.log(`Message added with ID: ${id}`);
        return id;
    }

    function removeMessage(id) {
        console.log("Attempting to remove message with ID:", id);
        const message = messageArea.querySelector(`[data-id="${id}"]`);
        if (message) {
            message.remove();
            console.log("Message removed successfully");
        } else {
            console.error("Message not found for ID:", id);
            // Fallback: Remove any stray typing indicators
            const typingIndicators = messageArea.querySelectorAll('.typing-indicator');
            typingIndicators.forEach(indicator => indicator.closest('.message').remove());
        }
    }
});