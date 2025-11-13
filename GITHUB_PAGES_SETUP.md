# GitHub Pages Setup Guide

This guide documents the GitHub Pages configuration for the Freesound Network Explorer website.

## Overview

The Freesound Network Explorer is automatically deployed to GitHub Pages, providing a public website that showcases the growing network of audio samples and their relationships.

**Public URL:** https://alexm1010.github.io/FollowWeb/

---

## Configuration Steps

### 1. Enable GitHub Pages

GitHub Pages must be enabled in the repository settings:

1. Navigate to **Settings** → **Pages** in the GitHub repository
2. Under **Source**, select:
   - **Branch:** `gh-pages`
   - **Folder:** `/ (root)`
3. Click **Save**

The `gh-pages` branch is automatically created and managed by the deployment workflow (`.github/workflows/deploy-website.yml`).

### 2. Deployment Workflow

The website is automatically deployed when:
- New visualizations are committed to `Output/*.html`
- Metrics are updated in `data/metrics_history.jsonl`
- Milestones are recorded in `data/milestone_history.jsonl`
- Manual workflow dispatch is triggered

**Workflow file:** `.github/workflows/deploy-website.yml`

**Key features:**
- Generates landing page with network statistics
- Copies visualizations to website directory
- Deploys using `peaceiris/actions-gh-pages@v3`
- Includes Plausible Analytics support (optional)

### 3. Website Structure

```
website/
├── index.html              # Landing page with statistics
├── visualizations/         # Interactive network visualizations
│   └── *.html             # Individual visualization files
└── lib/                   # JavaScript libraries (vis.js, etc.)
```

### 4. Verification Steps

After enabling GitHub Pages, verify the deployment:

1. **Check workflow status:**
   - Go to **Actions** tab in GitHub
   - Look for "Deploy Freesound Website" workflow
   - Verify it completed successfully

2. **Test website accessibility:**
   - Visit: https://alexm1010.github.io/FollowWeb/
   - Verify landing page loads correctly
   - Check that visualizations are accessible
   - Test on mobile devices for responsiveness

3. **Monitor deployment:**
   - Changes typically appear within 2-5 minutes
   - Check browser console for any errors
   - Verify analytics tracking (if configured)

---

## Features

### Landing Page

The landing page (`index.html`) includes:
- Network statistics (total nodes, edges, last updated)
- Growth metrics dashboard with Chart.js visualizations
- Links to interactive network visualizations
- Milestone history
- Mobile-responsive design

### Interactive Visualizations

Each visualization provides:
- Interactive network graph with physics simulation
- Hover tooltips with node/edge information
- Zoom and pan controls
- Community detection coloring
- Search and filter capabilities

### Analytics (Optional)

Plausible Analytics can be enabled by setting the `PLAUSIBLE_DOMAIN` secret in repository settings:
- Privacy-friendly analytics
- No cookies or personal data collection
- Tracks page views and visitor statistics

---

## Maintenance

### Updating the Website

The website updates automatically through the CI/CD pipeline:
1. Freesound nightly pipeline runs
2. New visualizations generated
3. Metrics updated
4. Deploy workflow triggered
5. Website updated within minutes

### Manual Deployment

To manually trigger a deployment:
1. Go to **Actions** tab
2. Select "Deploy Freesound Website"
3. Click **Run workflow**
4. Select branch and click **Run workflow**

### Troubleshooting

**Website not updating:**
- Check workflow logs in Actions tab
- Verify `gh-pages` branch exists
- Ensure GitHub Pages is enabled in settings
- Clear browser cache

**404 errors:**
- Verify repository name matches URL
- Check that files exist in `gh-pages` branch
- Wait 5-10 minutes for DNS propagation

**Visualizations not loading:**
- Check browser console for errors
- Verify library files copied correctly
- Test with different browsers

---

## Security & Privacy

### Data Protection

- **Checkpoint data:** Remains in private repository (never deployed)
- **Public website:** Only contains visualizations and aggregated statistics
- **No personal data:** Website does not collect or store user information
- **TOS compliance:** Freesound data usage complies with API terms of service

### Access Control

- **Public access:** Website is publicly accessible (read-only)
- **No authentication:** No login required to view visualizations
- **Repository access:** Source code and checkpoints remain private

---

## Performance

### Optimization

- **Compression:** Old visualizations can be compressed to save space
- **Caching:** Browser caching enabled for static assets
- **CDN:** GitHub Pages uses CDN for fast global delivery
- **Lazy loading:** Large visualizations load on-demand

### Limits

- **Storage:** GitHub Pages limited to 1GB total
- **Bandwidth:** 100GB/month soft limit
- **Build time:** 10 minutes per deployment
- **File size:** Individual files should be <100MB

---

## Future Enhancements

Potential improvements for the website:

1. **Historical visualizations:** Archive and display past network states
2. **Advanced analytics:** More detailed growth metrics and trends
3. **API endpoint:** Provide JSON API for programmatic access
4. **Custom domain:** Configure custom domain name
5. **Search functionality:** Search for specific samples or users
6. **Comparison views:** Compare network states across time

---

## References

- **GitHub Pages Documentation:** https://docs.github.com/en/pages
- **peaceiris/actions-gh-pages:** https://github.com/peaceiris/actions-gh-pages
- **Plausible Analytics:** https://plausible.io/docs
- **Chart.js:** https://www.chartjs.org/docs/

---

## Support

For issues or questions:
- Check workflow logs in Actions tab
- Review this documentation
- Open an issue in the repository
- Contact repository maintainers

**Last Updated:** November 13, 2025
