# Plausible Analytics Integration

## Overview

The Freesound Network Explorer uses [Plausible Analytics](https://plausible.io/) for privacy-friendly website analytics. Plausible is a lightweight, open-source alternative to Google Analytics that doesn't use cookies and doesn't collect personal data.

## Why Plausible?

- **Privacy-first**: No cookies, no personal data collection
- **GDPR compliant**: Fully compliant with privacy regulations
- **Lightweight**: < 1 KB script size (45x smaller than Google Analytics)
- **Open source**: Transparent and auditable
- **Simple**: Clean dashboard with essential metrics only

## How It Works

### Client-Side (Browser)

When users visit your GitHub Pages site, the Plausible script:
1. Loads from `https://plausible.io/js/script.js`
2. Tracks page views anonymously
3. Sends data to Plausible's servers (not your repository)
4. Does NOT use cookies or local storage
5. Does NOT track users across sites

### Server-Side (GitHub Actions)

The `generate_landing_page.py` script:
1. Reads the latest visualization HTML
2. Injects the Plausible script into the `<head>` section
3. Writes the modified HTML as `index.html`
4. The deploy workflow publishes to GitHub Pages

## Setup Instructions

### 1. Create Plausible Account

1. Go to [plausible.io](https://plausible.io/)
2. Sign up for an account (free trial available)
3. Add your GitHub Pages domain (e.g., `username.github.io`)

### 2. Configure Repository Secret

1. Navigate to your repository on GitHub
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `PLAUSIBLE_DOMAIN`
5. Value: Your GitHub Pages domain (e.g., `username.github.io`)
6. Click **Add secret**

### 3. Deploy Website

The next time you push visualizations, the deploy workflow will:
- Generate landing page with Plausible script
- Deploy to GitHub Pages
- Start tracking analytics

## Viewing Analytics

1. Log in to your Plausible account
2. Select your domain from the dashboard
3. View metrics:
   - **Page views**: Total visits to your site
   - **Unique visitors**: Number of distinct visitors
   - **Bounce rate**: Percentage of single-page visits
   - **Visit duration**: Average time spent on site
   - **Top pages**: Most visited pages
   - **Referrers**: Where visitors came from
   - **Countries**: Geographic distribution
   - **Devices**: Desktop vs mobile vs tablet

## Technical Details

### Script Injection

The Plausible script is injected into the HTML `<head>` section:

```html
<!-- Plausible Analytics -->
<script defer data-domain="your-domain.github.io" src="https://plausible.io/js/script.js"></script>
```

### Implementation

**File**: `generate_landing_page.py`

```python
def inject_plausible_analytics(html_content: str, domain: str) -> str:
    """Inject Plausible Analytics script into HTML head."""
    plausible_script = f'''
    <!-- Plausible Analytics -->
    <script defer data-domain="{domain}" src="https://plausible.io/js/script.js"></script>
'''
    
    # Inject before closing </head> tag
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', f'{plausible_script}\n</head>')
    
    return html_content
```

### Workflow Integration

**File**: `.github/workflows/deploy-website.yml`

```yaml
- name: Generate landing page
  env:
    PLAUSIBLE_DOMAIN: ${{ secrets.PLAUSIBLE_DOMAIN }}
  run: |
    # Build command with optional Plausible domain
    cmd="python generate_landing_page.py --output-dir website ..."
    
    # Add Plausible domain if configured
    if [ -n "$PLAUSIBLE_DOMAIN" ]; then
      cmd="$cmd --plausible-domain $PLAUSIBLE_DOMAIN"
    fi
    
    eval "$cmd"
```

## Testing

Run the test suite to verify Plausible integration:

```bash
python test_landing_page_generation.py
```

Tests verify:
- ✅ Plausible script is correctly injected
- ✅ Script is placed in `<head>` section
- ✅ Domain attribute is set correctly
- ✅ Landing page works without Plausible (optional)

## Disabling Analytics

To disable analytics:

1. Remove the `PLAUSIBLE_DOMAIN` secret from repository settings
2. The landing page generator will skip analytics injection
3. Visualizations will work normally without tracking

## Privacy Considerations

### What Plausible Tracks

- Page URL (which page was visited)
- HTTP Referer (where visitor came from)
- Browser (Chrome, Firefox, Safari, etc.)
- Operating system (Windows, macOS, Linux, etc.)
- Device type (desktop, mobile, tablet)
- Country (based on IP address, not stored)

### What Plausible Does NOT Track

- ❌ Personal data (names, emails, etc.)
- ❌ Cookies or persistent identifiers
- ❌ Cross-site tracking
- ❌ IP addresses (not stored)
- ❌ User behavior across sessions
- ❌ Fingerprinting

### GDPR Compliance

Plausible is fully GDPR compliant because:
- No personal data is collected
- No consent banner required
- Data is anonymized at collection
- Hosted in EU (optional)

## Cost

Plausible pricing (as of 2024):
- **Free trial**: 30 days
- **Starter**: $9/month (up to 10k monthly pageviews)
- **Growth**: $19/month (up to 100k monthly pageviews)
- **Business**: Custom pricing for higher volumes

**Alternative**: Self-host Plausible for free (requires server)

## Troubleshooting

### Analytics Not Showing

**Check:**
1. `PLAUSIBLE_DOMAIN` secret is set correctly
2. Domain matches your GitHub Pages URL exactly
3. Domain is added to your Plausible account
4. Website has been deployed after adding secret
5. Ad blockers may block Plausible (expected behavior)

### Script Not Injected

**Check:**
1. Landing page generator ran successfully
2. View page source and search for "plausible.io"
3. Check workflow logs for "Injecting Plausible Analytics" message

### Wrong Domain

**Fix:**
1. Update `PLAUSIBLE_DOMAIN` secret with correct domain
2. Re-run deploy workflow or push new visualization

## Resources

- **Plausible Website**: https://plausible.io/
- **Documentation**: https://plausible.io/docs
- **Privacy Policy**: https://plausible.io/privacy
- **GitHub**: https://github.com/plausible/analytics
- **Self-Hosting Guide**: https://plausible.io/docs/self-hosting

## Related Files

- **Landing Page Generator**: `generate_landing_page.py`
- **Deploy Workflow**: `.github/workflows/deploy-website.yml`
- **Test Suite**: `test_landing_page_generation.py`
- **Pipeline Documentation**: `Docs/FREESOUND_PIPELINE.md`
