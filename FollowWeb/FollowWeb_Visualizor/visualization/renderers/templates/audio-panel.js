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
            activePlayers: {}, // Map<nodeId, {player: Tone.Player, meter: Tone.Meter, duration: number, volume: number, isLooping: boolean, isExpanded: boolean}>
            singlePlayerNode: null, // nodeId
            mixMode: false,
            globalBPM: 120,
            masterCompressor: null,
            masterLimiter: null
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
                
                // Initialize master effects chain on first user interaction
                audioState.masterLimiter = new Tone.Limiter(-1).toDestination();
                audioState.masterCompressor = new Tone.Compressor({
                    threshold: -24,
                    ratio: 4,
                    attack: 0.05,
                    release: 0.2
                }).connect(audioState.masterLimiter);
                
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

        // Track failed player creation attempts to prevent retries
        const failedPlayers = new Set();

        // --- Core Functions ---

        async function showSinglePlayer(nodeId, autoPlay = true) {
            await ensureAudioContext();
            
            // Validate node exists
            if (!graph.hasNode(nodeId)) {
                console.error('Node not found in graph:', nodeId);
                return;
            }
            
            audioState.singlePlayerNode = nodeId;
            audioState.mixMode = false;
            renderAudioPanel();

            // Don't retry if player creation already failed for this node
            if (failedPlayers.has(nodeId)) {
                return;
            }

            if (!audioState.activePlayers[nodeId]) {
                // Create player and wait for it to load before playing
                try {
                    const player = await createPlayer(nodeId);
                    
                    // If player creation failed, mark as failed and show error in UI
                    if (!player) {
                        console.error('Failed to create player for node:', nodeId);
                        failedPlayers.add(nodeId);
                        renderAudioPanel();
                        return;
                    }
                    
                    // Now that audio is loaded, start playing automatically
                    if (autoPlay) {
                        const playerData = audioState.activePlayers[nodeId];
                        if (playerData && playerData.duration > 0) {
                            try {
                                player.start('+0', 0);
                                playerData.startTime = Tone.now();
                                playerData.seekPosition = 0;
                                highlightPlayingNode(nodeId, true);
                                renderAudioPanel();
                            } catch (e) {
                                console.error('Failed to auto-play:', e);
                            }
                        }
                    }
                } catch (error) {
                    console.error('Failed to load audio for node:', nodeId, error);
                    failedPlayers.add(nodeId);
                    renderAudioPanel();
                }
            }
        }

        async function addToMix(nodeId) {
            await ensureAudioContext();
            
            // Validate node exists
            if (!graph.hasNode(nodeId)) {
                console.error('Node not found in graph:', nodeId);
                return;
            }
            
            if (!audioState.activePlayers[nodeId]) {
                try {
                    const player = await createPlayer(nodeId);
                    if (!player) {
                        console.error('Failed to create player for node:', nodeId);
                        return;
                    }
                } catch (error) {
                    console.error('Failed to load audio for mix:', nodeId, error);
                    return;
                }
            }
            audioState.mixMode = true;
            renderAudioPanel();
        }

        function removeFromMix(nodeId) {
            if (audioState.activePlayers[nodeId]) {
                const playerData = audioState.activePlayers[nodeId];
                
                try {
                    playerData.player.stop();
                    playerData.player.dispose();
                } catch (e) {
                    console.error('Error disposing player:', e);
                }
                
                try {
                    if (playerData.meter) {
                        playerData.meter.dispose();
                    }
                } catch (e) {
                    console.error('Error disposing meter:', e);
                }
                
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
            
            if (!node) {
                console.error('Node not found:', nodeId);
                return null;
            }
            
            // Reconstruct preview URLs from uploader ID (space-efficient storage)
            // URL Pattern: https://freesound.org/data/previews/[folder]/[sound_id]_[uploader_id]-[quality].mp3
            // - folder: sound_id // 1000 (calculable)
            // - sound_id: node ID (already have)
            // - uploader_id: stored in node data (~7 bytes vs ~75 bytes for full URL)
            
            if (!node.uploader_id) {
                console.error('No uploader_id in node data for:', nodeId);
                console.error('Node data:', node);
                return null;
            }
            
            const soundId = nodeId;
            const uploaderId = node.uploader_id;
            const folderId = Math.floor(soundId / 1000);
            
            const audioUrls = [
                `https://freesound.org/data/previews/${folderId}/${soundId}_${uploaderId}-hq.mp3`,
                `https://freesound.org/data/previews/${folderId}/${soundId}_${uploaderId}-lq.mp3`,
                `https://freesound.org/data/previews/${folderId}/${soundId}_${uploaderId}-lq.ogg`
            ];
            
            console.log('Freesound preview URLs for node', nodeId, ':', audioUrls);

            return new Promise((resolve, reject) => {
                try {
                    // Create meter for visual feedback
                    const meter = new Tone.Meter();
                    
                    // Try URLs in order until one loads successfully
                    console.log('Creating Tone.Player with URLs:', audioUrls);
                    
                    // Create player with first URL
                    const player = new Tone.Player({
                        url: audioUrls[0],
                        loop: false,
                        fadeIn: 0.01,  // Smooth fade in to prevent clicks
                        fadeOut: 0.01, // Smooth fade out to prevent clicks
                        onload: () => {
                            console.log('✓ Audio loaded successfully for node:', nodeId, 'Duration:', player.buffer.duration);
                            // Store duration once loaded
                            if (audioState.activePlayers[nodeId]) {
                                audioState.activePlayers[nodeId].duration = player.buffer.duration;
                                audioState.activePlayers[nodeId].isLoading = false;
                            }
                            renderAudioPanel();
                            resolve(player);
                        },
                        onerror: (error) => {
                            console.warn('Failed to load', audioUrls[0], '- Error:', error);
                            // Try fallback URLs sequentially
                            let currentUrlIndex = 1;
                            
                            const tryNextUrl = () => {
                                if (currentUrlIndex >= audioUrls.length) {
                                    // All URLs failed
                                    console.error('✗ Failed to load audio for node:', nodeId, '- all URLs failed');
                                    console.error('Attempted URLs:', audioUrls);
                                    
                                    // Show user-friendly error in UI
                                    if (audioState.activePlayers[nodeId]) {
                                        audioState.activePlayers[nodeId].loadError = true;
                                        audioState.activePlayers[nodeId].isLoading = false;
                                    }
                                    renderAudioPanel();
                                    reject(new Error('All audio URLs failed to load'));
                                    return;
                                }
                                
                                const nextUrl = audioUrls[currentUrlIndex];
                                console.warn('Trying fallback URL:', nextUrl);
                                
                                player.load(nextUrl).then(() => {
                                    console.log('✓ Audio loaded successfully from fallback:', nextUrl);
                                    if (audioState.activePlayers[nodeId]) {
                                        audioState.activePlayers[nodeId].duration = player.buffer.duration;
                                        audioState.activePlayers[nodeId].isLoading = false;
                                    }
                                    renderAudioPanel();
                                    resolve(player);
                                }).catch((e) => {
                                    console.warn('Failed to load', nextUrl, '- Error:', e);
                                    currentUrlIndex++;
                                    tryNextUrl();
                                });
                            };
                            
                            tryNextUrl();
                        }
                    });

                    // Connect player through meter to master effects chain
                    player.chain(meter, audioState.masterCompressor);

                    // Set up event handlers
                    player.onstop = () => {
                        // Check if player finished naturally (not manually stopped)
                        if (audioState.activePlayers[nodeId]) {
                            const playerData = audioState.activePlayers[nodeId];
                            // If looping is disabled and we reached the end, reset position
                            if (!playerData.isLooping && playerData.duration > 0) {
                                playerData.seekPosition = 0;
                            }
                        }
                        highlightPlayingNode(nodeId, false);
                        renderAudioPanel();
                    };

                    audioState.activePlayers[nodeId] = {
                        player: player,
                        meter: meter,
                        duration: 0, // Will be set on load
                        volume: 0.8,
                        isLooping: false,
                        isExpanded: false,
                        startTime: null,
                        seekPosition: 0, // Track seek position for paused state
                        isLoading: true // Track loading state
                    };

                    // Set volume safely - prevent NaN from 0 or negative values
                    const initialVolume = 0.8;
                    const safeVolume = Math.max(0.001, Math.min(1.0, initialVolume));
                    player.volume.value = Tone.gainToDb(safeVolume);
                } catch (error) {
                    console.error('Error creating player for node:', nodeId, error);
                    reject(error);
                }
            });
        }

        async function togglePlay(nodeId) {
            await ensureAudioContext();

            let playerData = audioState.activePlayers[nodeId];
            if (!playerData) {
                try {
                    await createPlayer(nodeId);
                    playerData = audioState.activePlayers[nodeId];
                } catch (error) {
                    console.error('Failed to create player for node:', nodeId, error);
                    return;
                }
            }

            if (playerData && playerData.player) {
                const player = playerData.player;

                if (player.state === 'started') {
                    // Pause: store current position
                    if (playerData.duration > 0) {
                        const currentProgress = player.progress;
                        const calculatedPosition = currentProgress * playerData.duration;
                        // Ensure valid number
                        playerData.seekPosition = isFinite(calculatedPosition) ? calculatedPosition : 0;
                    }
                    player.stop();
                    playerData.startTime = null;
                    highlightPlayingNode(nodeId, false);
                } else {
                    // Resume from last position or start from beginning
                    // Ensure startOffset is a valid, finite number
                    let startOffset = playerData.seekPosition || 0;
                    
                    // Validate and clamp offset
                    if (!isFinite(startOffset) || startOffset < 0) {
                        startOffset = 0;
                    }
                    
                    // Don't start if duration is not loaded yet
                    if (playerData.duration === 0 || playerData.isLoading) {
                        console.warn('Cannot start player: audio still loading');
                        // Show loading state in UI
                        playerData.isLoading = true;
                        renderAudioPanel();
                        return;
                    }
                    
                    // Clear loading state
                    playerData.isLoading = false;
                    
                    // Clamp to duration
                    if (startOffset >= playerData.duration) {
                        startOffset = 0;
                    }
                    
                    try {
                        player.start('+0', startOffset);
                        playerData.startTime = Tone.now() - startOffset;
                        highlightPlayingNode(nodeId, true);
                    } catch (e) {
                        console.error('Failed to start player:', e);
                        playerData.startTime = null;
                        highlightPlayingNode(nodeId, false);
                    }
                }

                renderAudioPanel();
            }
        }

        function stopPlayer(nodeId) {
            const playerData = audioState.activePlayers[nodeId];
            if (playerData && playerData.player) {
                playerData.player.stop();
                playerData.startTime = null;
                playerData.seekPosition = 0; // Reset to beginning
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
                // Clamp volume to valid range and prevent NaN
                const safeVolume = Math.max(0.001, Math.min(1.0, parseFloat(volume) || 0.001));
                playerData.volume = safeVolume;
                
                try {
                    const db = Tone.gainToDb(safeVolume);
                    // Smooth volume change to prevent clicks
                    playerData.player.volume.rampTo(db, 0.05);
                } catch (e) {
                    console.error('Failed to set volume:', e);
                }
                
                renderAudioPanel();
            }
        }

        function seekTo(nodeId, position) {
            const playerData = audioState.activePlayers[nodeId];
            if (!playerData || !playerData.player) {
                console.warn('Player not found for node:', nodeId);
                return;
            }
            
            // Don't seek if audio not loaded yet
            if (playerData.duration === 0) {
                console.warn('Cannot seek: audio not loaded yet');
                return;
            }
            
            // Validate and clamp position
            let safePosition = parseFloat(position);
            
            if (!isFinite(safePosition) || isNaN(safePosition)) {
                console.error('Invalid seek position:', position);
                return;
            }
            
            safePosition = Math.max(0, Math.min(safePosition, playerData.duration));
            
            const wasPlaying = playerData.player.state === 'started';
            
            // Stop current playback
            playerData.player.stop();
            
            // Update seek position
            playerData.seekPosition = safePosition;
            
            // If was playing, restart from new position
            if (wasPlaying) {
                try {
                    playerData.player.start('+0', safePosition);
                    playerData.startTime = Tone.now() - safePosition;
                    highlightPlayingNode(nodeId, true);
                } catch (e) {
                    console.error('Failed to seek:', e);
                    playerData.startTime = null;
                    highlightPlayingNode(nodeId, false);
                }
            } else {
                playerData.startTime = null;
            }
            
            renderAudioPanel();
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
                playerData.seekPosition = 0; // Reset to beginning
                highlightPlayingNode(nodeId, false);
            });
            renderAudioPanel();
        }

        async function playAll() {
            await ensureAudioContext();
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                // Only play if not already playing, audio is loaded, and not currently loading
                if (playerData.player.state !== 'started' && 
                    playerData.duration > 0 && 
                    !playerData.isLoading) {
                    // Ensure valid offset
                    let startOffset = playerData.seekPosition || 0;
                    if (!isFinite(startOffset) || startOffset < 0) {
                        startOffset = 0;
                    }
                    if (startOffset >= playerData.duration) {
                        startOffset = 0;
                    }
                    
                    try {
                        playerData.player.start('+0', startOffset);
                        playerData.startTime = Tone.now() - startOffset;
                        highlightPlayingNode(nodeId, true);
                    } catch (e) {
                        console.error('Failed to start player:', nodeId, e);
                    }
                }
            });
            renderAudioPanel();
        }

        function pauseAll() {
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                if (playerData.player.state === 'started') {
                    // Store current position before pausing
                    if (playerData.duration > 0) {
                        const currentProgress = playerData.player.progress;
                        const calculatedPosition = currentProgress * playerData.duration;
                        playerData.seekPosition = isFinite(calculatedPosition) ? calculatedPosition : 0;
                    }
                    playerData.player.stop();
                    playerData.startTime = null;
                    highlightPlayingNode(nodeId, false);
                }
            });
            renderAudioPanel();
        }

        function clearAll() {
            Object.entries(audioState.activePlayers).forEach(([nodeId, playerData]) => {
                try {
                    playerData.player.stop();
                    playerData.player.dispose();
                } catch (e) {
                    console.error('Error disposing player:', e);
                }
                
                try {
                    if (playerData.meter) {
                        playerData.meter.dispose();
                    }
                } catch (e) {
                    console.error('Error disposing meter:', e);
                }
                
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
            if (!node) {
                // Node was removed from graph, clear single player mode
                audioState.singlePlayerNode = null;
                renderAudioPanel();
                return;
            }
            
            // Check if player creation failed for this node
            if (failedPlayers.has(node.id)) {
                panelContent.innerHTML = `
                    <div class="single-player">
                        <div class="sp-header">
                            <div class="sp-title">${escapeHtml(node.name || 'Unknown Sample')}</div>
                        </div>
                        <div style="padding: 20px; text-align: center; color: #ff6b6b;">
                            <p style="margin-bottom: 10px;">⚠️ Audio unavailable</p>
                            <p style="font-size: 12px; color: #999;">This sample was collected before audio playback was implemented. Please regenerate the visualization data.</p>
                        </div>
                    </div>
                `;
                return;
            }

            const playerData = audioState.activePlayers[node.id];
            const player = playerData?.player;
            const isPlaying = player && player.state === 'started';
            const duration = playerData?.duration || 0;
            const isLoading = playerData?.isLoading || false;
            const loadError = playerData?.loadError || false;

            // Calculate current position using player.progress for accuracy
            let seek = 0;
            let progress = 0;
            
            if (player && duration > 0) {
                if (isPlaying) {
                    // Use built-in progress property for playing state
                    const playerProgress = player.progress;
                    const calculatedSeek = playerProgress * duration;
                    const calculatedProgress = playerProgress * 100;
                    
                    // Ensure finite values
                    seek = isFinite(calculatedSeek) ? calculatedSeek : 0;
                    progress = isFinite(calculatedProgress) ? Math.min(calculatedProgress, 100) : 0;
                } else {
                    // Use stored seek position for paused state
                    seek = playerData.seekPosition || 0;
                    // Ensure seek is valid
                    if (!isFinite(seek) || seek < 0) {
                        seek = 0;
                    }
                    progress = duration > 0 ? Math.min((seek / duration) * 100, 100) : 0;
                }
            }

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
                        <button class="btn-control ${isPlaying ? 'active' : ''}" 
                                onclick="window.audioPanel.togglePlay('${node.id}')" 
                                ${isLoading ? 'disabled' : ''} 
                                title="${isLoading ? 'Loading audio...' : (isPlaying ? 'Pause' : 'Play')}"
                                aria-label="${isLoading ? 'Loading audio' : (isPlaying ? 'Pause audio' : 'Play audio')}"
                                aria-pressed="${isPlaying}">
                            ${isLoading ? '⏳' : (isPlaying ? 'ΓÅ╕' : 'Γû╢')}
                        </button>
                        <div class="sp-timeline-wrapper">
                            <div class="sp-timeline" 
                                 onclick="window.audioPanel.handleTimelineClick(event, '${node.id}')"
                                 role="slider"
                                 aria-label="Audio timeline"
                                 aria-valuemin="0"
                                 aria-valuemax="${duration}"
                                 aria-valuenow="${seek}"
                                 aria-valuetext="${formatTime(seek)} of ${formatTime(duration)}"
                                 tabindex="0">
                                <div class="sp-progress" style="width: ${progress}%" role="presentation"></div>
                            </div>
                            <div class="sp-time" aria-live="polite">${formatTime(seek)} / ${formatTime(duration)}</div>
                        </div>
                        <button class="btn-control" 
                                onclick="window.audioPanel.addToMix('${node.id}')" 
                                title="Add to Mix"
                                aria-label="Add sample to mix">
                            Γ₧ò
                        </button>
                    </div>
                </div>
            `;
        }

        function renderMixMode() {
            const playerIds = Object.keys(audioState.activePlayers);
            
            // Filter out nodes that no longer exist in graph
            const validPlayerIds = playerIds.filter(id => graph.hasNode(id));
            
            // Clean up invalid players
            playerIds.forEach(id => {
                if (!graph.hasNode(id)) {
                    removeFromMix(id);
                }
            });

            let listHtml = validPlayerIds.map(id => {
                const node = getNodeData(id);
                const playerData = audioState.activePlayers[id];
                const player = playerData?.player;
                const isPlaying = player && player.state === 'started';
                const isExpanded = playerData?.isExpanded || false;
                const duration = playerData?.duration || 0;
                const volume = playerData?.volume || 0.8;
                const isLooping = playerData?.isLooping || false;
                const isLoadingAudio = playerData?.isLoading || false;

                // Calculate current position using player.progress for accuracy
                let seek = 0;
                let progress = 0;
                let audioLevel = 0;
                
                if (player && duration > 0) {
                    if (isPlaying) {
                        // Use built-in progress property for playing state
                        const playerProgress = player.progress;
                        const calculatedSeek = playerProgress * duration;
                        const calculatedProgress = playerProgress * 100;
                        
                        // Ensure finite values
                        seek = isFinite(calculatedSeek) ? calculatedSeek : 0;
                        progress = isFinite(calculatedProgress) ? Math.min(calculatedProgress, 100) : 0;
                        
                        // Get audio level from meter
                        if (playerData.meter) {
                            try {
                                const meterValue = playerData.meter.getValue();
                                // Convert dB to 0-100 range (assuming -60dB to 0dB range)
                                audioLevel = Math.max(0, Math.min(100, ((meterValue + 60) / 60) * 100));
                            } catch (e) {
                                // Meter might not be ready yet
                                audioLevel = 0;
                            }
                        }
                    } else {
                        // Use stored seek position for paused state
                        seek = playerData.seekPosition || 0;
                        // Ensure seek is valid
                        if (!isFinite(seek) || seek < 0) {
                            seek = 0;
                        }
                        progress = duration > 0 ? Math.min((seek / duration) * 100, 100) : 0;
                    }
                }

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
                                    <button class="btn-mini ${isPlaying ? 'active' : ''}" 
                                            onclick="window.audioPanel.togglePlay('${id}')" 
                                            title="${isLoadingAudio ? 'Loading...' : 'Play/Pause'}" 
                                            ${isLoadingAudio ? 'disabled' : ''}
                                            aria-label="${isLoadingAudio ? 'Loading audio' : (isPlaying ? 'Pause' : 'Play')}"
                                            aria-pressed="${isPlaying}">
                                        ${isLoadingAudio ? '⏳' : (isPlaying ? 'ΓÅ╕' : 'Γû╢')}
                                    </button>
                                    <button class="btn-mini" 
                                            onclick="window.audioPanel.stopPlayer('${id}')" 
                                            title="Stop"
                                            aria-label="Stop playback">ΓÅ╣</button>
                                    <button class="btn-mini ${isLooping ? 'active' : ''}" 
                                            onclick="window.audioPanel.toggleLoop('${id}')" 
                                            title="Loop"
                                            aria-label="Toggle loop"
                                            aria-pressed="${isLooping}">
                                        Γƒ▓
                                    </button>
                                    <div class="volume-control">
                                        <span class="volume-icon" aria-hidden="true">≡ƒöè</span>
                                        <input type="range" 
                                               min="0" 
                                               max="100" 
                                               value="${Math.round(volume * 100)}" 
                                               class="volume-slider" 
                                               oninput="window.audioPanel.setVolume('${id}', this.value / 100)"
                                               aria-label="Volume"
                                               aria-valuemin="0"
                                               aria-valuemax="100"
                                               aria-valuenow="${Math.round(volume * 100)}"
                                               aria-valuetext="${Math.round(volume * 100)} percent">
                                        <span class="volume-percent" aria-live="polite">${Math.round(volume * 100)}%</span>
                                    </div>
                                    ${isPlaying ? `<div class="audio-level-meter" role="progressbar" aria-label="Audio level" aria-valuenow="${Math.round(audioLevel)}" aria-valuemin="0" aria-valuemax="100" style="width: ${audioLevel}%; background: linear-gradient(90deg, #4CAF50 0%, #FFC107 70%, #F44336 90%); height: 4px; border-radius: 2px; margin-top: 4px;"></div>` : ''}
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
                        <div class="mix-title">≡ƒÄ╡ Audio Mix (${validPlayerIds.length})</div>
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
            const percentage = Math.max(0, Math.min(1, clickX / rect.width));
            
            const playerData = audioState.activePlayers[nodeId];
            if (playerData && playerData.duration > 0) {
                const position = percentage * playerData.duration;
                seekTo(nodeId, position);
            }
        }

        function setBPM(bpm) {
            const newBPM = parseInt(bpm) || 120;
            const clampedBPM = Math.max(60, Math.min(200, newBPM));
            audioState.globalBPM = clampedBPM;
            
            // Update Tone.js Transport BPM
            Tone.getTransport().bpm.value = clampedBPM;
            
            renderAudioPanel();
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = String(text);
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

        // Periodic update for timelines and meters
        let updateInterval = null;
        
        function startPeriodicUpdate() {
            if (!updateInterval) {
                updateInterval = setInterval(() => {
                    // Only update if there are active players
                    const hasActivePlayers = Object.keys(audioState.activePlayers).length > 0;
                    if (hasActivePlayers && (audioState.singlePlayerNode || audioState.mixMode)) {
                        renderAudioPanel();
                    }
                }, 200);
            }
        }
        
        function stopPeriodicUpdate() {
            if (updateInterval) {
                clearInterval(updateInterval);
                updateInterval = null;
            }
        }
        
        // Start periodic updates
        startPeriodicUpdate();

        // --- Cleanup on page unload ---
        window.addEventListener('beforeunload', () => {
            stopPeriodicUpdate();
            clearAll();
            if (audioState.masterCompressor) {
                audioState.masterCompressor.dispose();
            }
            if (audioState.masterLimiter) {
                audioState.masterLimiter.dispose();
            }
        });

        // --- Keyboard Shortcuts ---
        function initKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Don't trigger if user is typing in an input
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                    return;
                }
                
                // Space: Play/Pause current player
                if (e.code === 'Space') {
                    e.preventDefault();
                    if (audioState.singlePlayerNode) {
                        togglePlay(audioState.singlePlayerNode);
                    } else if (audioState.mixMode) {
                        const firstPlayer = Object.keys(audioState.activePlayers)[0];
                        if (firstPlayer) togglePlay(firstPlayer);
                    }
                }
                
                // M: Toggle mix mode for current node
                if (e.code === 'KeyM' && audioState.singlePlayerNode) {
                    e.preventDefault();
                    addToMix(audioState.singlePlayerNode);
                }
                
                // L: Toggle loop for current player
                if (e.code === 'KeyL' && audioState.singlePlayerNode) {
                    e.preventDefault();
                    toggleLoop(audioState.singlePlayerNode);
                }
                
                // Escape: Close/clear
                if (e.code === 'Escape') {
                    e.preventDefault();
                    if (audioState.mixMode) {
                        clearAll();
                    } else if (audioState.singlePlayerNode) {
                        stopPlayer(audioState.singlePlayerNode);
                        audioState.singlePlayerNode = null;
                        renderAudioPanel();
                    }
                }
                
                // Arrow Left/Right: Seek ±5 seconds
                if (e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
                    e.preventDefault();
                    const nodeId = audioState.singlePlayerNode || Object.keys(audioState.activePlayers)[0];
                    if (nodeId) {
                        const playerData = audioState.activePlayers[nodeId];
                        if (playerData && playerData.duration > 0) {
                            const currentSeek = playerData.seekPosition || 0;
                            const delta = e.code === 'ArrowLeft' ? -5 : 5;
                            const newSeek = Math.max(0, Math.min(currentSeek + delta, playerData.duration));
                            seekTo(nodeId, newSeek);
                        }
                    }
                }
            });
            
            console.log('Keyboard shortcuts initialized: Space (play/pause), M (mix), L (loop), Esc (close), ←/→ (seek)');
        }

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
            setBPM,
            // Expose state for debugging
            getState: () => audioState,
            // Expose cleanup for testing
            cleanup: () => {
                stopPeriodicUpdate();
                clearAll();
            }
        };
        
        // Initialize keyboard shortcuts
        initKeyboardShortcuts();

        // Initial render
        renderAudioPanel();

        console.log('Audio panel initialized with Tone.js');
    }

    // Listen for graph initialization
    window.addEventListener('graphInitialized', initAudioPanel);
})();
