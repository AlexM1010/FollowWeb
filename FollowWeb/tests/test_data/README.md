# Test Data Generation

This directory contains scripts for generating anonymized test datasets from Instagram follower/following data.

## Security

**IMPORTANT**: The test data generation uses cryptographically secure hashing (PBKDF2-HMAC-SHA256 with 100,000 iterations) to ensure original usernames cannot be recovered from the anonymized data.

### Why This Matters

- Original Instagram usernames are personal information
- Weak hashing (like simple SHA-256) can be reversed with rainbow tables or brute force
- Our approach makes it computationally infeasible to recover original usernames

## Setup

### 1. Generate a Secret Salt

The salt is a secret key that makes the hashing irreversible. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

This will output a 64-character hex string like:
```
a1b2c3d4e5f6...
```

### 2. Create .env File

Create a `.env` file in the **project root** (not in this directory):

```bash
# In project root
TEST_DATA_SALT=your_64_character_hex_salt_here
```

You can copy `.env.example` as a template:

```bash
cp .env.example .env
# Then edit .env and add your salt
```

### 3. NEVER Commit the .env File

The `.env` file is already in `.gitignore`. **Never commit it to git!**

If you accidentally commit it:
1. Remove it from git history (see "Cleaning Git History" below)
2. Generate a new salt
3. Regenerate all test data

## Generating Test Data

### Basic Usage

```bash
# From project root
python FollowWeb/tests/test_data/generate_test_data.py --input followers_following.json
```

### Options

```bash
# Specify output directory
python FollowWeb/tests/test_data/generate_test_data.py \
  --input followers_following.json \
  --output-dir FollowWeb/tests/test_data

# Preserve network structure (slower but better for testing)
python FollowWeb/tests/test_data/generate_test_data.py \
  --input followers_following.json \
  --preserve-structure

# Show timing information
python FollowWeb/tests/test_data/generate_test_data.py \
  --input followers_following.json \
  --timing

# Custom random seed for reproducibility
python FollowWeb/tests/test_data/generate_test_data.py \
  --input followers_following.json \
  --seed 12345
```

## Generated Files

The script generates 5 datasets:

- `tiny_real.json` - 5% of original data (quick unit tests)
- `small_real.json` - 15% of original data (unit/integration tests)
- `medium_real.json` - 33% of original data (integration tests)
- `large_real.json` - 66% of original data (performance tests)
- `full_anonymized.json` - 100% of original data (full system tests)
- `dataset_summary.json` - Statistics about all datasets

**Note**: These files are gitignored and should NOT be committed to the repository.

## Anonymization Format

Usernames are anonymized as:
```
user_<64_character_hex_hash>
```

Example:
```
user_a1b2c3d4e5f6789012345678901234567890123456789012345678901234
```

The hash is generated using:
- Algorithm: PBKDF2-HMAC-SHA256
- Iterations: 100,000
- Salt: 32 bytes (from TEST_DATA_SALT)
- Output: 32 bytes (64 hex characters)

## CI/CD Setup

For GitHub Actions or other CI/CD:

1. Add `TEST_DATA_SALT` as a repository secret
2. Generate test data in CI before running tests:

```yaml
- name: Generate test data
  env:
    TEST_DATA_SALT: ${{ secrets.TEST_DATA_SALT }}
  run: |
    python FollowWeb/tests/test_data/generate_test_data.py \
      --input followers_following.json
```

## Cleaning Git History

If test data with weak hashing was previously committed, you need to remove it from git history:

### Using git-filter-repo (Recommended)

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove test data files from all commits
git filter-repo --path FollowWeb/tests/test_data/tiny_real.json --invert-paths
git filter-repo --path FollowWeb/tests/test_data/small_real.json --invert-paths
git filter-repo --path FollowWeb/tests/test_data/medium_real.json --invert-paths
git filter-repo --path FollowWeb/tests/test_data/large_real.json --invert-paths
git filter-repo --path FollowWeb/tests/test_data/full_anonymized.json --invert-paths
git filter-repo --path FollowWeb/tests/test_data/dataset_summary.json --invert-paths

# Force push to remote (WARNING: This rewrites history!)
git push origin --force --all
```

### Using BFG Repo-Cleaner (Alternative)

```bash
# Install BFG
# Download from: https://rtyley.github.io/bfg-repo-cleaner/

# Remove files
java -jar bfg.jar --delete-files "tiny_real.json"
java -jar bfg.jar --delete-files "small_real.json"
java -jar bfg.jar --delete-files "medium_real.json"
java -jar bfg.jar --delete-files "large_real.json"
java -jar bfg.jar --delete-files "full_anonymized.json"
java -jar bfg.jar --delete-files "dataset_summary.json"

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push origin --force --all
```

### Important Notes

- **Backup first**: Create a backup branch before cleaning history
- **Coordinate with team**: All developers need to re-clone or rebase
- **Force push required**: This rewrites git history
- **Alternative**: If force push is not acceptable, consider starting a fresh repository

## Troubleshooting

### "TEST_DATA_SALT not found in environment"

Make sure:
1. You created a `.env` file in the project root
2. The file contains `TEST_DATA_SALT=<your_salt>`
3. The salt is a valid 64-character hex string

### "Invalid TEST_DATA_SALT format"

The salt must be exactly 64 hexadecimal characters (0-9, a-f). Generate a new one:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Slow generation

PBKDF2 with 100,000 iterations is intentionally slow for security. This is normal.
For large datasets (1000+ users), generation may take several minutes.

### Tests failing after regeneration

If you regenerated test data with a new salt, the hashes will be different.
This is expected and correct - it means the anonymization is working.

## Security Best Practices

1. ✅ **DO**: Keep TEST_DATA_SALT secret
2. ✅ **DO**: Use different salts for different environments
3. ✅ **DO**: Regenerate test data if salt is compromised
4. ✅ **DO**: Add .env to .gitignore
5. ❌ **DON'T**: Commit .env to git
6. ❌ **DON'T**: Share your salt publicly
7. ❌ **DON'T**: Use the same salt in production
8. ❌ **DON'T**: Commit generated test data files

## Questions?

See the main project documentation or open an issue on GitHub.
