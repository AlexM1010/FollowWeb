# Utility Scripts

This directory contains utility scripts organized by purpose.

## Directory Structure

### `scripts/analysis/`

Scripts for data analysis and processing

Scripts:
- `analyze_color_differences.py`
- `detect_milestone.py`
- `fix_audio_urls.py`
- `monitor_pipeline.py`
- `workflow_orchestrator.py`

### `scripts/backup/`

Scripts for checkpoint backup and restoration

Scripts:
- `check_checkpoint_audio.py`
- `cleanup_old_backups.py`
- `migrate_checkpoint.py`
- `restore_from_backup.py`
- `visualize_from_checkpoint.py`

### `scripts/freesound/`

Scripts for Freesound API operations and data collection

Scripts:
- `fetch_freesound_data.py`
- `generate_freesound_visualization.py`
- `validate_freesound_samples.py`

### `scripts/generation/`

Scripts for generating visualizations and reports

Scripts:
- `generate_k7_sigma.py`
- `generate_landing_page.py`
- `generate_metrics_dashboard.py`
- `generate_user_pack_edges.py`

### `scripts/testing/`

Scripts for testing and benchmarking

### `scripts/validation/`

Scripts for data validation and verification

Scripts:
- `check_color_similarity.py`
- `validate_pipeline_data.py`
- `verify_complete_data.py`

## Usage

All scripts can be run from the repository root:

```bash
python scripts/<category>/<script_name>.py
```

