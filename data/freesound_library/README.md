# Freesound Library - Persistent Data Storage

## 🎯 Purpose

This directory contains the **persistent Freesound sample library** that grows over time across multiple runs. The data is **committed to Git** to ensure it survives:

- ✅ PC crashes
- ✅ System corruption
- ✅ Hardware failures
- ✅ Team collaboration
- ✅ CI/CD environments

## 📁 Files

### Main Library
- `freesound_library.pkl` - Primary checkpoint file containing:
  - NetworkX graph with all samples and relationships
  - Set of processed sample IDs
  - Sound object cache (saves API calls)
  - Metadata (timestamps, statistics)

### Automatic Backups
- `freesound_library_backup_*nodes_*.pkl` - Created every 100 nodes
- Format: `freesound_library_backup_{nodes}nodes_{timestamp}.pkl`
- Example: `freesound_library_backup_500nodes_20251110_143022.pkl`

## 🔄 How It Works

### First Run
```bash
python generate_freesound_visualization.py
# Creates: freesound_library.pkl with 50 samples
# Commits to Git
```

### Subsequent Runs
```bash
python generate_freesound_visualization.py
# Loads: freesound_library.pkl (50 samples)
# Adds: 50 more samples
# Saves: freesound_library.pkl (100 samples)
# Commits to Git
```

### After PC Crash
```bash
git clone <repo>
python generate_freesound_visualization.py
# Loads: freesound_library.pkl from Git
# Continues from where it left off!
```

## 📊 Growth Over Time

| Run | Samples | Edges | Cache Size | File Size |
|-----|---------|-------|------------|-----------|
| 1   | 50      | ~200  | 50         | ~500 KB   |
| 2   | 100     | ~800  | 100        | ~1 MB     |
| 10  | 500     | ~4000 | 500        | ~5 MB     |
| 100 | 5000    | ~40K  | 5000       | ~50 MB    |

## 🔧 Maintenance

### If File Gets Too Large (>100 MB)
Consider using **Git LFS** (Large File Storage):
```bash
git lfs install
git lfs track "data/freesound_library/*.pkl"
git add .gitattributes
git commit -m "Enable Git LFS for library files"
```

### Restore from Backup
```bash
cp data/freesound_library/freesound_library_backup_500nodes_*.pkl \\
   data/freesound_library/freesound_library.pkl
```

### Clean Old Backups
```bash
# Keep only last 5 backups
cd data/freesound_library
ls -t freesound_library_backup_*.pkl | tail -n +6 | xargs rm
```

## 🎵 What's Stored

Each sample in the library includes:
- **Basic**: ID, name, tags, duration, username
- **Audio**: Preview URLs (HQ MP3, LQ MP3, OGG)
- **Popularity**: Downloads, ratings, comments, bookmarks
- **Technical**: Filesize, bitrate, samplerate, channels
- **Metadata**: Description, license, pack info, upload date
- **Images**: Waveform and spectrogram URLs
- **Relationships**: Similar sounds (edges in graph)

## 🚀 Benefits

1. **Crash Recovery**: Never lose collected data
2. **Incremental Growth**: Library grows over weeks/months
3. **API Efficiency**: Cache prevents re-fetching known samples
4. **Team Collaboration**: Share library across team members
5. **CI/CD Ready**: Automated builds can use existing library
6. **Version Control**: Track library growth over time

## 📝 Notes

- Checkpoint saved after **every sample** (checkpoint_interval=1)
- Automatic backup created every **100 nodes**
- All data is **compressed** (joblib compress=3)
- **Atomic writes** prevent corruption during save
- **Thread-safe** for concurrent access
