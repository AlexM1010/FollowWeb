# CDN Dependencies

This document lists the JavaScript libraries loaded via CDN in FollowWeb visualizations. These libraries do not require Python installation and are automatically loaded when viewing HTML visualizations in a web browser.

## Sigma.js - High-Performance Graph Visualization

**Purpose**: WebGL-accelerated graph rendering for large networks (10,000+ nodes)

**Version**: 3.0.0-beta.29 (latest stable beta)

**CDN URLs**:
- Main library: `https://cdn.jsdelivr.net/npm/sigma@3.0.0-beta.29/build/sigma.min.js`
- Graphology (required dependency): `https://cdn.jsdelivr.net/npm/graphology@0.25.4/dist/graphology.umd.min.js`

**License**: MIT License

**Documentation**: https://www.sigmajs.org/

**Features Used**:
- WebGL rendering for performance with large graphs
- Interactive pan, zoom, and node selection
- Custom node and edge styling
- Hover tooltips and click events
- Search functionality
- Canvas fallback for browsers without WebGL

**Browser Compatibility**:
- Chrome/Edge: Full WebGL support
- Firefox: Full WebGL support
- Safari: Full WebGL support
- Older browsers: Automatic canvas fallback

## Howler.js - Audio Playback

**Purpose**: Cross-browser audio playback for Freesound sample previews

**Version**: 2.2.4 (latest stable)

**CDN URL**: `https://cdn.jsdelivr.net/npm/howler@2.2.4/dist/howler.min.js`

**License**: MIT License

**Documentation**: https://howlerjs.com/

**Features Used**:
- MP3 audio playback
- Play/pause controls
- Loop functionality
- Seek/scrubbing support
- Error handling for failed audio loads
- Cross-browser audio format support

**Audio Format Support**:
- Primary: MP3 (high-quality previews from Freesound)
- Fallback: OGG (alternative format if MP3 unavailable)
- Browser compatibility: All modern browsers support MP3

**Browser Compatibility**:
- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support (including iOS)
- Mobile browsers: Full support with user interaction requirement

## Tom-Select - Enhanced Dropdowns (Optional)

**Purpose**: Enhanced dropdown UI for node search functionality

**Version**: 2.3.1

**CDN URLs**:
- JavaScript: `https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js`
- CSS: `https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.css`

**License**: Apache 2.0 License

**Documentation**: https://tom-select.js.org/

**Features Used**:
- Searchable dropdown for node selection
- Keyboard navigation
- Custom styling
- Performance optimization for large lists

**Browser Compatibility**: All modern browsers

## Vis.js Network (Legacy - Pyvis Renderer)

**Purpose**: Interactive network visualization (used by Pyvis renderer)

**Version**: 9.1.2

**Local Copy**: `lib/vis-9.1.2/` (bundled with package)

**License**: MIT License / Apache 2.0 License (dual-licensed)

**Documentation**: https://visjs.org/

**Note**: Vis.js is used by the Pyvis renderer for backward compatibility. New visualizations should use Sigma.js renderer for better performance with large graphs.

## CDN Provider

All CDN resources are served via **jsDelivr** (https://www.jsdelivr.com/), which provides:
- High availability and performance
- Automatic minification and compression
- HTTPS support
- Global CDN with edge caching
- Open-source package hosting
- No usage limits or API keys required

## Offline Usage

For offline or air-gapped environments, you can:

1. Download the libraries from their CDN URLs
2. Place them in a local directory (e.g., `lib/`)
3. Update the HTML template paths to reference local files instead of CDN URLs

Example for Sigma.js:
```html
<!-- CDN (default) -->
<script src="https://cdn.jsdelivr.net/npm/sigma@3.0.0-beta.29/build/sigma.min.js"></script>

<!-- Local (offline) -->
<script src="lib/sigma/sigma.min.js"></script>
```

## Security Considerations

**Subresource Integrity (SRI)**: CDN resources include SRI hashes in production templates to ensure file integrity and prevent tampering.

**Content Security Policy (CSP)**: If your environment uses CSP headers, ensure the following domains are whitelisted:
- `cdn.jsdelivr.net` (for all CDN resources)
- `'unsafe-inline'` for inline scripts (required for embedded visualization code)

**HTTPS**: All CDN resources are loaded via HTTPS to prevent man-in-the-middle attacks.

## Version Updates

When updating CDN library versions:

1. Test thoroughly with sample visualizations
2. Check browser console for errors
3. Verify backward compatibility with existing HTML files
4. Update version numbers in this documentation
5. Update SRI hashes if using them in templates

## Python Dependencies vs CDN Dependencies

**Python Dependencies** (installed via pip):
- `freesound-api>=1.1.0` - Freesound API client
- `joblib>=1.3.0` - Checkpoint compression and caching
- `jinja2>=3.1.6` - HTML template rendering
- `networkx>=2.8.0` - Graph data structures and algorithms
- `pyvis>=0.3.0` - Pyvis renderer (includes Vis.js)
- `matplotlib>=3.5.0` - Static graph visualization

**CDN Dependencies** (loaded in browser):
- Sigma.js - Interactive graph rendering
- Howler.js - Audio playback
- Tom-Select - Enhanced dropdowns
- Graphology - Graph data structure for Sigma.js

The Python dependencies handle data processing and HTML generation, while CDN dependencies provide client-side interactivity in the browser.
