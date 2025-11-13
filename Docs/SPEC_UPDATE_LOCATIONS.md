# Repository Cleanup Spec - Update Locations for Large-Scale Graph Analysis

**Date:** November 13, 2025  
**Purpose:** Document where to add Requirement 20 (Large-Scale Graph Analysis) to existing repository-cleanup spec

---

## Overview

The large-scale graph analysis capability (600K-1M+ nodes) should be added to the **repository-cleanup spec** as **Requirement 20** because:

1. ✅ Same scalability patterns (streaming, checkpoints, SQLite, parallel processing)
2. ✅ Reuses existing utilities (ParallelProcessingManager, ProgressTracker)
3. ✅ Follows same architecture (always-on + automatic large-scale optimizations)
4. ✅ Consistent with Requirement 19 (10K+ file handling)

---

## File 1: `.kiro/specs/repository-cleanup/requirements.md`

### Location: After Requirement 19 (line ~280)

### Content to Add:

```markdown
### Requirement 20: Large-Scale Graph Analysis (600K+ Nodes)

**User Story:** As a network analyst, I want FollowWeb to handle graphs with 600,000+ nodes efficiently using distributed processing across GitHub Actions runners, so that I can analyze massive social networks and audio sample collections without memory exhaustion or requiring paid infrastructure.

#### Acceptance Criteria

**Always-On Optimizations (All Graph Sizes):**

1. THE Graph Analysis System SHALL use existing ParallelProcessingManager to auto-detect available CPU cores (1-4) and scale workers accordingly
2. THE Graph Analysis System SHALL use existing ProgressTracker to display progress bars with node count, percentage complete, and estimated time remaining
3. THE Graph Analysis System SHALL use existing caching system (CacheManager) for graph conversions, hashes, and layout positions
4. THE Graph Analysis System SHALL optimize algorithms for graph size (Louvain for <10K nodes, adjusted resolution for 10K+ nodes)

**Automatic Large-Scale Optimizations (600K+ Nodes):**

5. WHEN THE Graph Analysis System detects node count exceeding 600,000, THE Graph Analysis System SHALL automatically enable graph partitioning to distribute work across multiple GitHub Actions runners
6. WHEN THE Graph Analysis System partitions a graph, THE Graph Analysis System SHALL use METIS or similar algorithm to create balanced partitions with minimized cross-partition edges
7. WHEN THE Graph Analysis System calculates partition size, THE Graph Analysis System SHALL auto-scale based on detected resources (50K nodes per partition for 4 cores + 7 GB RAM, 30K for 2 cores + 4 GB RAM, 10K for 1 core + 2 GB RAM)
8. WHEN THE Graph Analysis System processes partitions, THE Graph Analysis System SHALL use GitHub Actions matrix strategy to run up to 20 partitions concurrently
9. WHEN THE Graph Analysis System analyzes each partition, THE Graph Analysis System SHALL use auto-scaled parallel processing within the partition (leveraging detected 1-4 cores per runner)
10. WHEN THE Graph Analysis System completes partition analysis, THE Graph Analysis System SHALL merge results (communities, centrality, layout) across partitions into coherent final graph
11. WHEN THE Graph Analysis System processes graphs exceeding 1 million nodes, THE Graph Analysis System SHALL use multi-wave processing (20 concurrent runners per wave) to handle unlimited graph sizes

**Configuration and Metrics:**

12. THE Graph Analysis System SHALL provide configuration options for partition size (default auto-scaled), max concurrent runners (default 20), and merge strategy (default community-aware)
13. WHEN THE Graph Analysis System completes analysis, THE Graph Analysis System SHALL generate performance metrics including total nodes processed, partitions created, concurrent runners used, execution time per partition, merge time, and total throughput (nodes/second)
14. THE Graph Analysis System SHALL achieve target performance of 1 million nodes in under 30 minutes on free GitHub Actions runners (20 concurrent × 50K nodes per partition)
```

### Why This Location:
- Follows Requirement 19 (scalability patterns)
- Same structure and format
- Logical progression from file handling to graph handling

---

## File 2: `.kiro/specs/repository-cleanup/design.md`

### Location 1: Component Architecture Section (after Workflow Manager, line ~200)

### Content to Add:

```markdown
### 7. Graph Partitioning System (New)

**Purpose**: Partition large graphs for distributed processing across GitHub Actions runners

**Location**: `FollowWeb_Visualizor/analysis/partitioning.py`

**Responsibilities**:
- Detect graph size and auto-calculate optimal partition count
- Partition graphs using METIS to minimize edge cuts
- Balance partition sizes for even workload distribution
- Preserve community structure during partitioning
- Save/load partitions as GitHub Actions artifacts

**Interface**:
```python
from ..utils.parallel import ParallelProcessingManager

class GraphPartitioner:
    def __init__(self):
        self.parallel_manager = ParallelProcessingManager()
        self.detected_cores = self.parallel_manager._cpu_count
        self.detected_ram = self._detect_available_ram()
    
    def calculate_optimal_partitions(self, total_nodes: int) -> int:
        """Auto-calculate partition count based on resources."""
        if self.detected_ram >= 7:
            nodes_per_partition = 50000
        elif self.detected_ram >= 4:
            nodes_per_partition = 30000
        else:
            nodes_per_partition = 10000
        return math.ceil(total_nodes / nodes_per_partition)
    
    def partition_graph(self, graph: nx.DiGraph, num_partitions: int) -> List[nx.DiGraph]:
        """Partition using METIS to minimize edge cuts."""
        
    def save_partition(self, partition: nx.DiGraph, partition_id: int, output_dir: str):
        """Save partition as compressed artifact."""
```

### 8. Partition Analysis Worker (New)

**Purpose**: Analyze individual graph partition with auto-scaled resources

**Location**: `FollowWeb_Visualizor/analysis/partition_worker.py`

**Responsibilities**:
- Load partition from artifact
- Run community detection on partition
- Calculate centrality metrics with auto-scaled parallelization
- Calculate layout positions
- Identify boundary nodes for cross-partition merging
- Save results as artifact

**Interface**:
```python
class PartitionAnalysisWorker:
    def __init__(self, partition_id: int):
        self.partition_id = partition_id
        self.parallel_manager = ParallelProcessingManager()
    
    def analyze_partition(self, partition: nx.DiGraph) -> PartitionResults:
        """Analyze partition using auto-scaled workers."""
        config = self.parallel_manager.get_parallel_config(
            operation_type='analysis',
            graph_size=partition.number_of_nodes()
        )
        
        with ProcessPoolExecutor(max_workers=config.cores_used) as executor:
            communities = self._detect_communities(partition)
            centrality = self._calculate_centrality(partition, executor)
            layout = self._calculate_layout(partition)
        
        return PartitionResults(
            partition_id=self.partition_id,
            communities=communities,
            centrality=centrality,
            layout=layout,
            boundary_nodes=self._identify_boundary_nodes(partition)
        )
```

### 9. Partition Results Merger (New)

**Purpose**: Merge results from distributed partition analysis

**Location**: `FollowWeb_Visualizor/analysis/partition_merger.py`

**Responsibilities**:
- Load results from all partition artifacts
- Merge community assignments across partitions
- Merge and normalize centrality scores
- Merge layout positions using hierarchical approach
- Handle boundary nodes between partitions
- Create final graph with merged attributes

**Interface**:
```python
class PartitionResultsMerger:
    def merge_communities(self, partition_results: List[PartitionResults]) -> dict:
        """Merge community assignments across partitions."""
        
    def merge_centrality(self, partition_results: List[PartitionResults]) -> dict:
        """Merge centrality scores across partitions."""
        
    def merge_layouts(self, partition_results: List[PartitionResults]) -> dict:
        """Merge layout positions across partitions."""
        
    def create_final_graph(self, original_graph: nx.DiGraph, 
                          merged_results: MergedResults) -> nx.DiGraph:
        """Create final graph with merged analysis results."""
```
```

### Location 2: Data Models Section (line ~1800)

### Content to Add:

```markdown
### Graph Partitioning Data Models

```python
@dataclass
class PartitionInfo:
    """Information about a graph partition."""
    partition_id: int
    node_count: int
    edge_count: int
    boundary_node_count: int
    artifact_path: str

@dataclass
class PartitionResults:
    """Results from analyzing a single partition."""
    partition_id: int
    communities: dict[str, int]  # node_id -> community_id
    centrality: dict[str, float]  # node_id -> centrality_score
    layout: dict[str, tuple[float, float]]  # node_id -> (x, y)
    boundary_nodes: list[str]  # nodes with cross-partition edges
    metrics: dict[str, Any]  # partition-specific metrics

@dataclass
class MergedResults:
    """Merged results from all partitions."""
    global_communities: dict[str, int]
    global_centrality: dict[str, float]
    global_layout: dict[str, tuple[float, float]]
    partition_count: int
    total_nodes: int
    merge_time: float
```
```

### Location 3: GitHub Actions Workflows Section (new section after Implementation Considerations)

### Content to Add:

```markdown
## GitHub Actions Workflow for Large Graphs

### Workflow Architecture

The large-scale graph analysis uses a three-stage GitHub Actions workflow:

1. **Partition Stage**: Single runner partitions graph and uploads artifacts
2. **Analyze Stage**: Matrix of up to 20 runners analyze partitions in parallel
3. **Merge Stage**: Single runner merges results and generates visualization

### Workflow Configuration

```yaml
# .github/workflows/large-graph-analysis.yml
name: Large Graph Analysis

on:
  workflow_dispatch:
    inputs:
      graph_file:
        description: 'Path to graph file'
        required: true
      auto_scale:
        description: 'Auto-scale partition size'
        default: 'true'

jobs:
  partition:
    name: Partition Graph
    runs-on: ubuntu-latest
    timeout-minutes: 30
    outputs:
      num_partitions: ${{ steps.partition.outputs.num_partitions }}
      partition_ids: ${{ steps.partition.outputs.partition_ids }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Partition graph
        id: partition
        run: |
          python -m FollowWeb_Visualizor.analysis.partition_graph \
            --input ${{ inputs.graph_file }} \
            --auto-scale ${{ inputs.auto_scale }} \
            --output-dir partitions/
      
      - name: Upload partitions
        uses: actions/upload-artifact@v4
        with:
          name: graph-partitions
          path: partitions/
          retention-days: 1
  
  analyze:
    name: Analyze Partition ${{ matrix.partition_id }}
    needs: partition
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      matrix:
        partition_id: ${{ fromJson(needs.partition.outputs.partition_ids) }}
      max-parallel: 20
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Download partition
        uses: actions/download-artifact@v4
        with:
          name: graph-partitions
      
      - name: Analyze partition
        run: |
          python -m FollowWeb_Visualizor.analysis.analyze_partition \
            --partition-id ${{ matrix.partition_id }} \
            --input partitions/partition-${{ matrix.partition_id }}.pkl \
            --output results/
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: partition-results-${{ matrix.partition_id }}
          path: results/partition-${{ matrix.partition_id }}-results.pkl
          retention-days: 1
  
  merge:
    name: Merge Results
    needs: analyze
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Download all results
        uses: actions/download-artifact@v4
        with:
          pattern: partition-results-*
          merge-multiple: true
      
      - name: Merge results
        run: |
          python -m FollowWeb_Visualizor.analysis.merge_results \
            --input-dir results/ \
            --output final_graph.gpickle
      
      - name: Generate visualization
        run: |
          python -m FollowWeb_Visualizor --input final_graph.gpickle
      
      - name: Upload final outputs
        uses: actions/upload-artifact@v4
        with:
          name: final-analysis
          path: |
            final_graph.gpickle
            Output/*.html
            Output/*.txt
```

### Resource Allocation

**Per Runner (GitHub Free Tier):**
- CPU: 4 cores (auto-detected)
- RAM: 7 GB
- Disk: 14 GB SSD
- Timeout: 6 hours max

**Matrix Capacity:**
- Max concurrent: 20 runners
- Total capacity: 80 cores, 140 GB RAM
- Multi-wave: 20 runners × N waves for unlimited scale

**Auto-Scaling:**
- Each runner auto-detects 1-4 cores
- Partition size auto-scales: 50K (4 cores), 30K (2 cores), 10K (1 core)
- Workers auto-scale within partition based on detected cores
```

---

## File 3: `.kiro/specs/repository-cleanup/tasks.md`

### Location: After Phase 5 (line ~450)

### Content to Add:

```markdown
## Phase 6: Large-Scale Graph Analysis Implementation

- [ ] 16. Implement graph partitioning system
  - [ ] 16.1 Implement GraphPartitioner
    - Implement calculate_optimal_partitions() with auto-scaling based on detected RAM
    - Implement partition_graph() using METIS for balanced partitions
    - Implement save_partition() and load_partition() with compression
    - Integrate with existing ParallelProcessingManager for resource detection
    - _Requirements: 20.1, 20.5, 20.6, 20.7_

  - [ ] 16.2 Implement PartitionAnalysisWorker
    - Implement analyze_partition() with auto-scaled parallel processing
    - Implement _detect_communities() for partition-local community detection
    - Implement _calculate_centrality() with parallel execution
    - Implement _calculate_layout() for partition-local layout
    - Implement _identify_boundary_nodes() for cross-partition edges
    - Integrate with existing ParallelProcessingManager for worker scaling
    - _Requirements: 20.1, 20.9_

  - [ ] 16.3 Implement PartitionResultsMerger
    - Implement merge_communities() to combine partition communities
    - Implement merge_centrality() to aggregate and normalize scores
    - Implement merge_layouts() using hierarchical positioning
    - Implement create_final_graph() to build final analyzed graph
    - Handle boundary nodes and cross-partition edges
    - _Requirements: 20.10_

  - [ ] 16.4 Create GitHub Actions workflow
    - Create .github/workflows/large-graph-analysis.yml
    - Implement partition job with artifact upload
    - Implement analyze matrix job (max-parallel: 20)
    - Implement merge job with artifact download
    - Configure timeout-minutes and fail-fast settings
    - _Requirements: 20.8, 20.11_

- [ ] 17. Write tests for graph partitioning
  - [ ] 17.1 Unit tests for GraphPartitioner
    - Test calculate_optimal_partitions() with various RAM sizes
    - Test partition_graph() with synthetic graphs
    - Test partition balance and edge cut minimization
    - Test save/load partition with compression
    - _Requirements: 20.5, 20.6, 20.7_

  - [ ] 17.2 Unit tests for PartitionAnalysisWorker
    - Test analyze_partition() with 50K node partition
    - Test auto-scaling with 1, 2, 4 core configurations
    - Test community detection on partition
    - Test centrality calculation with parallel execution
    - Test boundary node identification
    - _Requirements: 20.9_

  - [ ] 17.3 Unit tests for PartitionResultsMerger
    - Test merge_communities() with overlapping communities
    - Test merge_centrality() normalization
    - Test merge_layouts() hierarchical positioning
    - Test boundary node handling
    - _Requirements: 20.10_

  - [ ] 17.4 Integration tests for full pipeline
    - Test 100K node graph (2 partitions)
    - Test 300K node graph (6 partitions)
    - Test 600K node graph (12 partitions)
    - Test 1M node graph (20 partitions)
    - Verify final graph correctness
    - Measure performance metrics
    - _Requirements: 20.12, 20.13, 20.14_

  - [ ] 17.5 Performance benchmarks
    - Benchmark partition time vs graph size
    - Benchmark analysis time per partition
    - Benchmark merge time vs partition count
    - Verify 1M nodes < 30 minutes target
    - Generate performance report
    - _Requirements: 20.14_
```

---

## Summary of Changes

### Files to Update:
1. ✅ `.kiro/specs/repository-cleanup/requirements.md` - Add Requirement 20
2. ✅ `.kiro/specs/repository-cleanup/design.md` - Add 3 new components + data models + workflow
3. ✅ `.kiro/specs/repository-cleanup/tasks.md` - Add Phase 6 with implementation tasks

### New Components:
- GraphPartitioner (partitioning.py)
- PartitionAnalysisWorker (partition_worker.py)
- PartitionResultsMerger (partition_merger.py)
- GitHub Actions workflow (large-graph-analysis.yml)

### Reused Components:
- ParallelProcessingManager (auto-scaling)
- ProgressTracker (progress bars)
- CacheManager (caching)
- Checkpoint patterns (from Freesound)

### Dependencies to Add:
- `metis` or `pymetis` - Graph partitioning library
- No other new dependencies (reuse existing)

---

## Next Steps

1. **Review locations** - Confirm where to add content
2. **Approve integration** - Confirm adding as Requirement 20
3. **Update spec files** - Add content to requirements.md, design.md, tasks.md
4. **Begin implementation** - Start with Milestone 1 (100K nodes)

---

**Status:** Ready for Spec Integration  
**Awaiting:** Confirmation to proceed with updates
