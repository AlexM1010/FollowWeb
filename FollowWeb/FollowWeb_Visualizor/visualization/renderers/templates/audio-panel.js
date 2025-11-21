// Audio Panel State & Logic (using Tone.js)
(function () {
    'use strict';

    let audioContextStarted = false;

    // Wait for DOM and global variables to be ready
    window.addEventListener('DOMContentLoaded', function () {
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
            activePlayers: {}, // Map<nodeId, {player: Tone.Player, duration: number}>
            singlePlayerNode: null, // nodeId
            mixMode: false,
            isLooping: false
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
            if (!node || !node.audio_url) {
                console.warn('No audio URL for node:', nodeId);
                return null;
            }

            try {
                const player = new Tone.Player({
                    url: node.audio_url,
                    loop: audioState.isLooping,
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
                    duration: 0 // Will be set on load
                };

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
                    highlightPlayingNode(nodeId, false);
                } else {
                    player.start();
                    highlightPlayingNode(nodeId, true);
                }

                renderAudioPanel();
            }
        }

        function stopAll() {
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                playerData.player.stop();
                highlightPlayingNode(nodeId, false);
            });
            renderAudioPanel();
        }

        async function playAll() {
            await ensureAudioContext();
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                if (playerData.player.state !== 'started') {
                    playerData.player.start();
                    highlightPlayingNode(nodeId, true);
                }
            });
            renderAudioPanel();
        }

        function pauseAll() {
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                if (playerData.player.state === 'started') {
                    playerData.player.stop();
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

            // Get current playback position (Tone.js doesn't have a simple seek property)
            // We'll calculate it based on when it started
            const seek = player ? player.toSeconds(player.now() - player._startTime) : 0;
            const progress = duration > 0 ? Math.min((seek / duration) * 100, 100) : 0;

            panelContent.innerHTML = `
                <div class="single-player">
                    <div class="sp-header">
                        <div class="sp-title">${escapeHtml(node.name || 'Unknown Sample')}</div>
                        <div class="sp-meta">
                            ${node.user ? `<span>👤 ${escapeHtml(node.user)}</span>` : ''}
                            ${node.duration ? `<span>⏱ ${node.duration.toFixed(1)}s</span>` : ''}
                        </div>
                    </div>
                    <div class="sp-controls">
                        <button class="btn-control ${isPlaying ? 'active' : ''}" onclick="window.audioPanel.togglePlay('${node.id}')">
                            ${isPlaying ? '⏸' : '▶'}
                        </button>
                        <div class="sp-timeline-wrapper">
                            <div class="sp-timeline">
                                <div class="sp-progress" style="width: ${progress}%"></div>
                            </div>
                            <div class="sp-time">${formatTime(seek)} / ${formatTime(duration)}</div>
                        </div>
                        <button class="btn-control" onclick="window.audioPanel.addToMix('${node.id}')" title="Add to Mix">
                            ➕
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
                const isPlaying = playerData?.player && playerData.player.state === 'started';

                return `
                    <div class="mix-item">
                        <div class="mix-info">
                            <div class="mix-name">${escapeHtml(node ? node.name : 'Unknown')}</div>
                        </div>
                        <div class="mix-controls">
                            <button class="btn-mini ${isPlaying ? 'active' : ''}" onclick="window.audioPanel.togglePlay('${id}')">
                                ${isPlaying ? '⏸' : '▶'}
                            </button>
                            <button class="btn-mini btn-danger" onclick="window.audioPanel.removeFromMix('${id}')">✖</button>
                        </div>
                    </div>
                `;
            }).join('');

            panelContent.innerHTML = `
                <div class="mix-mode">
                    <div class="mix-header">
                        <div class="mix-title">Mix Mode (${playerIds.length})</div>
                        <div class="mix-master-controls">
                            <button class="btn-mini" onclick="window.audioPanel.playAll()">▶ All</button>
                            <button class="btn-mini" onclick="window.audioPanel.pauseAll()">⏸ All</button>
                            <button class="btn-mini btn-danger" onclick="window.audioPanel.clearAll()">Clear</button>
                        </div>
                    </div>
                    <div class="mix-list">
                        ${listHtml}
                    </div>
                </div>
            `;
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
            clearAll,
            showSinglePlayer
        };

        // Initial render
        renderAudioPanel();

        console.log('Audio panel initialized with Tone.js');
    });
})();
