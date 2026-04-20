document.addEventListener("DOMContentLoaded", () => {
    const urlInput = document.getElementById('video-url');
    const extractBtn = document.getElementById('extract-btn');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const resultView = document.getElementById('result-view');
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('video-title');
    const resolutionsDiv = document.getElementById('resolutions');

    // Helper to update the LED Neon Status indicator
    const updateStatus = (state, text) => {
        statusDot.className = `status-dot ${state}`;
        statusText.innerText = text;
    };

    extractBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) return;

        // Visual: Checking State
        updateStatus('checking', 'Checking...');
        extractBtn.disabled = true;
        resultView.style.display = 'none';

        try {
            const baseUrl = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
            // Fetch metadata from local FastAPI /extract endpoint
            const response = await fetch(`${baseUrl}/extract?url=${encodeURIComponent(url)}`);
            if (!response.ok) {
                throw new Error("Failed to fetch metadata");
            }
            
            const data = await response.json();

            // Populate Result UI
            thumbnail.src = data.thumbnail || 'https://via.placeholder.com/600x300/000000/FFFFFF/?text=No+Thumbnail';
            videoTitle.innerText = data.title;
            
            // Clear existing buttons
            resolutionsDiv.innerHTML = '';
            
            // Dynamically inject resolution buttons
            if (data.formats && data.formats.length > 0) {
                data.formats.forEach(format => {
                    const btn = document.createElement('button');
                    btn.className = 'res-btn';
                    
                    // Style differently if it's audio
                    if (format.type === 'audio') {
                        btn.style.border = '1px solid #ffcc00';
                        btn.style.color = '#ffcc00';
                    }

                    btn.innerText = `Download ${format.resolution}`;
                    btn.onclick = () => {
                        btn.innerText = "Starting Download...";
                        btn.style.backgroundColor = "rgba(0, 255, 100, 0.4)";
                        
                        // To trigger a file download natively without crashing browser memory for large files,
                        // we create an invisible full page navigation or iframe.
                        const downloadUrl = `${baseUrl}/download?url=${encodeURIComponent(url)}&format_id=${format.format_id}&type=${format.type}`;
                        
                        // We use a hidden anchor tag to trigger the browser's download manager
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.target = '_blank';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        
                        setTimeout(() => {
                            btn.innerText = `Download ${format.resolution}`;
                            btn.style.backgroundColor = ""; // reset
                        }, 5000);
                    };
                    resolutionsDiv.appendChild(btn);
                });
            } else {
                resolutionsDiv.innerHTML = '<p style="color: rgba(255,255,255,0.5); font-size: 0.9em; grid-column: 1 / -1;">No compatible formats found.</p>';
            }

            // Reveal results and set Ready State
            resultView.style.display = 'block';
            updateStatus('ready', 'Ready');
        } catch (error) {
            console.error("Extraction error:", error);
            // Visual Error State
            updateStatus('error', 'Error');
        } finally {
            extractBtn.disabled = false;
        }
    });
    
    // Quick Extract on Enter key
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            extractBtn.click();
        }
    });

});
