// Shared variables - no longer tracking isDarkMode as we're always in dark mode

// Apply dark mode styling only
function setDarkModeOnly() {
    const body = document.body;
    const chatContainer = document.getElementById('chatContainer');
    const chatHeader = document.getElementById('chatHeader');
    const searchInput = document.getElementById('searchInput');
    const infoPanel = document.getElementById('infoPanel');
    
    body.style.backgroundColor = '#343541';
    body.style.color = 'white';
    
    if (chatContainer) {
        chatContainer.style.backgroundColor = '#444654';
    }
    
    if (chatHeader) {
        chatHeader.style.backgroundColor = '#202123';
        chatHeader.style.color = 'white';
    }
    
    const chatBox = document.querySelector('.chat-box');
    if (chatBox) {
        chatBox.style.backgroundColor = '#343541';
    }
    
    const chatInputContainer = document.getElementById('chatInputContainer');
    if (chatInputContainer) {
        chatInputContainer.style.backgroundColor = '#202123';
        const chatInput = chatInputContainer.querySelector('input');
        if (chatInput) {
            chatInput.style.backgroundColor = '#555';
            chatInput.style.color = 'white';
        }
    }
    
    // Update search input dark mode
    if (searchInput) {
        searchInput.style.backgroundColor = '#444654';
        searchInput.style.color = 'white';
    }
    
    // Update info panel
    if (infoPanel) {
        infoPanel.style.backgroundColor = '#2f303a';
        infoPanel.style.color = 'white';
        
        // Update collapsibles
        const collapsibles = infoPanel.querySelectorAll('.collapsible');
        collapsibles.forEach(item => {
            item.style.backgroundColor = '#3a3b47';
            item.style.color = 'white';
        });
        
        // Update content
        const contents = infoPanel.querySelectorAll('.content');
        contents.forEach(item => {
            item.style.backgroundColor = '#41424f';
            item.style.color = 'white';
        });
    }
    
    document.querySelectorAll('.chat-message').forEach(message => {
        if (!message.classList.contains('user-message')) {
            message.style.backgroundColor = '#444654';
            message.style.color = 'white';
        }
    });
    
    // Update feedback elements if in feedback mode
    const feedbackContent = document.querySelector('.feedback-content');
    if (feedbackContent) {
        feedbackContent.style.backgroundColor = '#444654';
        feedbackContent.style.color = 'white';
    }
    
    const feedbackContainer = document.querySelector('.feedback-container');
    if (feedbackContainer) {
        feedbackContainer.style.backgroundColor = '#343541';
        feedbackContainer.style.color = 'white';
    }
}

// Setup collapsible functionality
function setupCollapsibles() {
    const collapsibles = document.getElementsByClassName("collapsible");
    for (let i = 0; i < collapsibles.length; i++) {
        // Remove any existing event listeners first to avoid duplicates
        const oldElement = collapsibles[i];
        const newElement = oldElement.cloneNode(true);
        oldElement.parentNode.replaceChild(newElement, oldElement);
        
        // Add click event listener
        newElement.addEventListener("click", function() {
            this.classList.toggle("active");
            const content = this.nextElementSibling;
            if (content.style.display === "block") {
                content.style.display = "none";
            } else {
                content.style.display = "block";
            }
        });
    }
}
