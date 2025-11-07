# Examples and Sample Data

This directory contains example data files and sample outputs:

## Sample Data

- `followers_following.json` - Example Instagram follower/following data

## Usage

The sample data can be used to test the FollowWeb package functionality:

```bash
# Analyze sample data
followweb --input examples/followers_following.json

# Use with custom configuration
followweb --input examples/followers_following.json --config configs/fast_config_k1.json
```

## Data Format

The `followers_following.json` file demonstrates the expected input format for Instagram data. See the main documentation for detailed format specifications.