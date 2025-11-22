// Audio Panel State & Logic (using Tone.js)
(function () {
    'use strict';

    let audioContextStarted = false;

    // Wait for graph to be initialized
    function initAudioPanel() {
        // Check if required globals exist
        if (typeof graph === 'undefined' || typeof renderer === 'undefined') {
            console.error('Audio panel: Required globals (graph, renderer) not found');
            return;
        }

        if (typeof Tone === 'undefined') {
            console.error('Audio panel: Tone.js not found. Please include Tone.js before audio-panel.js');
            return;
        }

        // State management
        const audioState = {
            activePlayers: {}, // Map<nodeId, {player: Tone.Player, duration: number, volume: number, isLooping: boolean, isExpanded: boolean}>
            singlePlayerNode: null, // nodeId
            mixMode: false,
            globalBPM: 120
        };

        // DOM Elements
        const panelContent = document.getElementById('panel-content');
        if (!panelContent) {
            console.error('Audio panel: #panel-content element not found');
            return;
        }

        // --- Helper Functions ---

        async function ensureAudioContext() {
            if (!audioContextStarted) {
                await Tone.start();
                audioContextStarted = true;
                console.log('Tone.js audio context started');
            }
        }

        function formatTime(seconds) {
            if (!seconds || isNaN(seconds)) return '0:00';
            const minutes = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return minutes + ':' + (secs < 10 ? '0' : '') + secs;
        }

        function getNodeData(nodeId) {
            if (!graph.hasNode(nodeId)) return null;
            return {
                id: nodeId,
                ...graph.getNodeAttributes(nodeId)
            };
        }

        // --- Core Functions ---

        async function showSinglePlayer(nodeId) {
            await ensureAudioContext();
            audioState.singlePlayerNode = nodeId;
            audioState.mixMode = false;
            renderAudioPanel();

            if (!audioState.activePlayers[nodeId]) {
                await togglePlay(nodeId);
            }
        }

        async function addToMix(nodeId) {
            await ensureAudioContext();
            if (!audioState.activePlayers[nodeId]) {
                await createPlayer(nodeId);
            }
            audioState.mixMode = true;
            renderAudioPanel();
        }

        function removeFromMix(nodeId) {
            if (audioState.activePlayers[nodeId]) {
                const playerData = audioState.activePlayers[nodeId];
                playerData.player.stop();
                playerData.player.dispose();
                delete audioState.activePlayers[nodeId];
            }

            // If no players left, exit mix mode
            if (Object.keys(audioState.activePlayers).length === 0) {
                audioState.mixMode = false;
                audioState.singlePlayerNode = null;
            }

            highlightPlayingNode(nodeId, false);
            renderAudioPanel();
        }

        async function createPlayer(nodeId) {
            const node = getNodeData(nodeId);
            
            // Parse audio URLs from JSON array
            let audioUrls = [];
            if (node && node.audio_urls) {
                try {
                    audioUrls = JSON.parse(node.audio_urls);
                } catch (e) {
                    console.error('Failed to parse audio_urls:', e);
                }
            }
            
            if (!audioUrls || audioUrls.length === 0) {
                console.warn('No audio URL for node:', nodeId);
                return null;
            }

            try {
                // Tone.js will try URLs in order until one loads successfully
                const player = new Tone.Player({
                    url: audioUrls,
                    loop: false,
                    onload: () => {
                        // Store duration once loaded
                        if (audioState.activePlayers[nodeId]) {
                            audioState.activePlayers[nodeId].duration = player.buffer.duration;
                        }
                        renderAudioPanel();
                    }
                }).toDestination();

                // Set up event handlers
                player.onstop = () => {
                    highlightPlayingNode(nodeId, false);
                    renderAudioPanel();
                };

                audioState.activePlayers[nodeId] = {
                    player: player,
                    duration: 0, // Will be set on load
                    volume: 0.8,
                    isLooping: false,
                    isExpanded: false,
                    startTime: null
                };

                // Set volume safely
                try {
                    player.volume.value = Tone.gainToDb(0.8);
                } catch (e) {
                    console.error('Failed to set volume:', e);
                    player.volume.value = -10; // Fallback to reasonable dB value
                }

                return player;
            } catch (error) {
                console.error('Error creating player for node:', nodeId, error);
                return null;
            }
        }

        async function togglePlay(nodeId) {
            await ensureAudioContext();

            let playerData = audioState.activePlayers[nodeId];
            if (!playerData) {
                await createPlayer(nodeId);
                playerData = audioState.activePlayers[nodeId];
            }

            if (playerData && playerData.player) {
                const player = playerData.player;

                if (player.state === 'started') {
                    player.stop();
                    playerData.startTime = null;
                    highlightPlayingNode(nodeId, false);
                } else {
                    player.start();
                    playerData.startTime = Tone.now();
                    highlightPlayingNode(nodeId, true);
                }

                renderAudioPanel();
            }
        }

        function stopPlayer(nodeId) {
            const playerData = audioState.activePlayers[nodeId];
            if (playerData && playerData.player) {
                playerData.player.stop();
                playerData.startTime = null;
                highlightPlayingNode(nodeId, false);
                renderAudioPanel();
            }
        }

        function toggleLoop(nodeId) {
            const playerData = audioState.activePlayers[nodeId];
            if (playerData && playerData.player) {
                playerData.isLooping = !playerData.isLooping;
                playerData.player.loop = playerData.isLooping;
                renderAudioPanel();
            }
        }

        function setVolume(nodeId, volume) {
            const playerData = audioState.activePlayers[nodeId];
            if (playerData && playerData.player) {
                playerData.volume = volume;
                playerData.player.volume.value = Tone.gainToDb(volume);
                renderAudioPanel();
            }
        }

        function seekTo(nodeId, position) {
            const playerData = audioState.activePlayers[nodeId];
            if (playerData && playerData.player && playerData.duration > 0) {
                // Validate position
                if (isNaN(position) || position < 0) {
                    console.error('Invalid seek position:', position);
                    return;
                }
                
                const wasPlaying = playerData.player.state === 'started';
                playerData.player.stop();
                
                try {
                    playerData.player.start('+0', Math.min(position, playerData.duration));
                    playerData.startTime = Tone.now() - position;
                } catch (e) {
                    console.error('Failed to seek:', e);
                }
                
                if (!wasPlaying) {
                    playerData.player.stop();
                    playerData.startTime = null;
                }
                renderAudioPanel();
            }
        }

        function toggleExpand(nodeId) {
            const playerData = audioState.activePlayers[nodeId];
            if (playerData) {
                playerData.isExpanded = !playerData.isExpanded;
                renderAudioPanel();
            }
        }

        function stopAll() {
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                playerData.player.stop();
                playerData.startTime = null;
                highlightPlayingNode(nodeId, false);
            });
            renderAudioPanel();
        }

        async function playAll() {
            await ensureAudioContext();
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                if (playerData.player.state !== 'started') {
                    playerData.player.start();
                    playerData.startTime = Tone.now();
                    highlightPlayingNode(nodeId, true);
                }
            });
            renderAudioPanel();
        }

        function pauseAll() {
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                if (playerData.player.state === 'started') {
                    playerData.player.stop();
                    playerData.startTime = null;
                    highlightPlayingNode(nodeId, false);
                }
            });
            renderAudioPanel();
        }

        function clearAll() {
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                playerData.player.stop();
                playerData.player.dispose();
                highlightPlayingNode(nodeId, false);
            });
            audioState.activePlayers = {};
            audioState.singlePlayerNode = null;
            audioState.mixMode = false;
            renderAudioPanel();
        }

        // --- Rendering ---

        function renderAudioPanel() {
            if (audioState.mixMode) {
                renderMixMode();
            } else if (audioState.singlePlayerNode) {
                renderSinglePlayer();
            } else {
                panelContent.innerHTML = '<div style="padding: 20px; text-align: center; color: #888;">Click a node to play</div>';
            }
        }

        function renderSinglePlayer() {
            const node = getNodeData(audioState.singlePlayerNode);
            if (!node) return;

            const playerData = audioState.activePlayers[node.id];
            const player = playerData?.player;
            const isPlaying = player && player.state === 'started';
            const duration = playerData?.duration || 0;

            // Calculate current position
            let seek = 0;
            if (playerData?.startTime && isPlaying) {
                seek = Math.min(Tone.now() - playerData.startTime, duration);
            }
            const progress = duration > 0 ? Math.min((seek / duration) * 100, 100) : 0;

            panelContent.innerHTML = `
                <div class="single-player">
                    <div class="sp-header">
                        <div class="sp-title">${escapeHtml(node.name || 'Unknown Sample')}</div>
                        <div class="sp-meta">
                            ${node.user ? `<span>≡ƒæñ ${escapeHtml(node.user)}</span>` : ''}
                            ${node.duration ? `<span>ΓÅ▒ ${node.duration.toFixed(1)}s</span>` : ''}
                        </div>
                    </div>
                    <div class="sp-controls">
                        <button class="btn-control ${isPlaying ? 'active' : ''}" onclick="window.audioPanel.togglePlay('${node.id}')">
                            ${isPlaying ? 'ΓÅ╕' : 'Γû╢'}
                        </button>
                        <div class="sp-timeline-wrapper">
                            <div class="sp-timeline" onclick="window.audioPanel.handleTimelineClick(event, '${node.id}')">
                                <div class="sp-progress" style="width: ${progress}%"></div>
                            </div>
                            <div class="sp-time">${formatTime(seek)} / ${formatTime(duration)}</div>
                        </div>
                        <button class="btn-control" onclick="window.audioPanel.addToMix('${node.id}')" title="Add to Mix">
                            Γ₧ò
                        </button>
                    </div>
                </div>
            `;
        }

        function renderMixMode() {
            const playerIds = Object.keys(audioState.activePlayers);

            let listHtml = playerIds.map(id => {
                const node = getNodeData(id);
                const playerData = audioState.activePlayers[id];
                const player = playerData?.player;
                const isPlaying = player && player.state === 'started';
                const isExpanded = playerData?.isExpanded || false;
                const duration = playerData?.duration || 0;
                const volume = playerData?.volume || 0.8;
                const isLooping = playerData?.isLooping || false;

                // Calculate current position
                let seek = 0;
                if (playerData?.startTime && isPlaying) {
                    seek = Math.min(Tone.now() - playerData.startTime, duration);
                }
                const progress = duration > 0 ? Math.min((seek / duration) * 100, 100) : 0;

                if (isExpanded) {
                    return `
                        <div class="mix-item expanded">
                            <div class="mix-header-row" onclick="window.audioPanel.toggleExpand('${id}')">
                                <span class="expand-icon">Γû╝</span>
                                <div class="mix-name">${escapeHtml(node ? node.name : 'Unknown')}</div>
                                <button class="btn-mini btn-danger" onclick="event.stopPropagation(); window.audioPanel.removeFromMix('${id}')">Γ£û</button>
                            </div>
                            <div class="mix-expanded-content">
                                <div class="mix-timeline" onclick="window.audioPanel.handleTimelineClick(event, '${id}')">
                                    <div class="mix-progress" style="width: ${progress}%"></div>
                                </div>
                                <div class="mix-time">${formatTime(seek)} / ${formatTime(duration)}</div>
                                <div class="mix-controls-row">
                                    <button class="btn-mini ${isPlaying ? 'active' : ''}" onclick="window.audioPanel.togglePlay('${id}')" title="Play/Pause">
                                        ${isPlaying ? 'ΓÅ╕' : 'Γû╢'}
                                    </button>
                                    <button class="btn-mini" onclick="window.audioPanel.stopPlayer('${id}')" title="Stop">ΓÅ╣</button>
                                    <button class="btn-mini ${isLooping ? 'active' : ''}" onclick="window.audioPanel.toggleLoop('${id}')" title="Loop">
                                        Γƒ▓
                                    </button>
                                    <div class="volume-control">
                                        <span class="volume-icon">≡ƒöè</span>
                                        <input type="range" min="0" max="100" value="${Math.round(volume * 100)}" 
                                               class="volume-slider" 
                                               oninput="window.audioPanel.setVolume('${id}', this.value / 100)">
                                        <span class="volume-percent">${Math.round(volume * 100)}%</span>
                                    </div>
                                </div>
                                <div class="mix-metadata">
                                    ${node?.user ? `<div class="meta-row"><span class="meta-label">User:</span> ${escapeHtml(node.user)}</div>` : ''}
                                    ${node?.duration ? `<div class="meta-row"><span class="meta-label">Duration:</span> ${node.duration.toFixed(1)}s</div>` : ''}
                                    ${node?.tags ? `<div class="meta-row"><span class="meta-label">Tags:</span> ${escapeHtml(node.tags)}</div>` : ''}
                                    ${node?.downloads !== undefined ? `<div class="meta-row"><span class="meta-label">Downloads:</span> ${node.downloads}</div>` : ''}
                                    ${node?.rating !== undefined ? `<div class="meta-row"><span class="meta-label">Rating:</span> ${node.rating.toFixed(1)}</div>` : ''}
                                    ${node?.degree !== undefined ? `<div class="meta-row"><span class="meta-label">Connections:</span> ${node.degree}</div>` : ''}
                                    ${node?.centrality !== undefined ? `<div class="meta-row"><span class="meta-label">Centrality:</span> ${node.centrality.toFixed(4)}</div>` : ''}
                                    ${node?.community !== undefined ? `<div class="meta-row"><span class="meta-label">Community:</span> ${node.community}</div>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    return `
                        <div class="mix-item collapsed">
                            <div class="mix-header-row" onclick="window.audioPanel.toggleExpand('${id}')">
                                <span class="expand-icon">Γû╢</span>
                                <div class="mix-name">${escapeHtml(node ? node.name : 'Unknown')}</div>
                                <button class="btn-mini btn-danger" onclick="event.stopPropagation(); window.audioPanel.removeFromMix('${id}')">Γ£û</button>
                            </div>
                        </div>
                    `;
                }
            }).join('');

            panelContent.innerHTML = `
                <div class="mix-mode">
                    <div class="mix-header">
                        <div class="mix-title">≡ƒÄ╡ Audio Mix (${playerIds.length})</div>
                        <div class="mix-master-controls">
                            <button class="btn-mini" onclick="window.audioPanel.playAll()" title="Play All">Γû╢ All</button>
                            <button class="btn-mini" onclick="window.audioPanel.pauseAll()" title="Pause All">ΓÅ╕ All</button>
                            <button class="btn-mini" onclick="window.audioPanel.stopAll()" title="Stop All">ΓÅ╣ All</button>
                            <button class="btn-mini btn-danger" onclick="window.audioPanel.clearAll()" title="Clear All">Clear</button>
                        </div>
                    </div>
                    <div class="mix-bpm-control">
                        <label>BPM:</label>
                        <input type="number" min="60" max="200" value="${audioState.globalBPM}" 
                               onchange="window.audioPanel.setBPM(this.value)">
                    </div>
                    <div class="mix-list">
                        ${listHtml}
                    </div>
                </div>
            `;
        }

        function handleTimelineClick(event, nodeId) {
            const timeline = event.currentTarget;
            const rect = timeline.getBoundingClientRect();
            const clickX = event.clientX - rect.left;
            const percentage = clickX / rect.width;
            
            const playerData = audioState.activePlayers[nodeId];
            if (playerData && playerData.duration > 0) {
                const position = percentage * playerData.duration;
                seekTo(nodeId, position);
            }
        }

        function setBPM(bpm) {
            audioState.globalBPM = parseInt(bpm) || 120;
            renderAudioPanel();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // --- Highlight Update ---
        function highlightPlayingNode(nodeId, isPlaying) {
            if (nodeId && graph.hasNode(nodeId)) {
                if (isPlaying) {
                    const node = graph.getNodeAttributes(nodeId);
                    if (!node.originalColor) {
                        graph.setNodeAttribute(nodeId, 'originalColor', node.color);
                    }
                    graph.setNodeAttribute(nodeId, 'color', '#FFD93D');
                } else {
                    const node = graph.getNodeAttributes(nodeId);
                    if (node.originalColor) {
                        graph.setNodeAttribute(nodeId, 'color', node.originalColor);
                    }
                }
                renderer.refresh();
            }
        }

        // --- Event Listeners ---

        // Update Node Click Handler
        renderer.on('clickNode', async ({ node }) => {
            await showSinglePlayer(node);
        });

        // Periodic update for timelines
        setInterval(() => {
            if (audioState.singlePlayerNode || audioState.mixMode) {
                renderAudioPanel();
            }
        }, 200);

        // --- Expose API to window ---
        window.audioPanel = {
            togglePlay,
            addToMix,
            removeFromMix,
            playAll,
            pauseAll,
            stopAll,
            clearAll,
            showSinglePlayer,
            stopPlayer,
            toggleLoop,
            setVolume,
            toggleExpand,
            handleTimelineClick,
            setBPM
        };

        // Initial render
        renderAudioPanel();

        console.log('Audio panel initialized with Tone.js');
    }

    // Listen for graph initialization
    window.addEventListener('graphInitialized', initAudioPanel);
})();
