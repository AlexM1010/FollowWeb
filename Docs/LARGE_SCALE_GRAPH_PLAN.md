# Large-Scale Graph Analysis Plan (600K → 1M+ Nodes)

**Date:** November 13, 2025  
**Status:** Temporary Planning Document  
**Target:** Enable FollowWeb to handle 600,000+ nodes, then scale to 1,000,000+ nodes

---

## Current State Analysis

### What Works Now (Up to 10,000 nodes)

**Current Performance Benchmarks:**
- 500 nodes: 5-10 seconds
- 2,000 nodes: 30-60 seconds  
- 5,000 nodes: 1-2 minutes
- 10,000 nodes: 3-5 minutes

**Current Architecture:**
- **In-memory graph processing**: Full NetworkX DiGraph loaded into RAM
- **Community detection**: Louvain algorithm on full graph (adjusted resolution for 10K+)
- **Centrality calculations**: Full graph betweenness, eigenvector, degree
- **Visualization**: Sigma.js supports 10,000+ nodes with WebGL
- **Caching**: Centralized cache manager for graph conversions, hashes, layouts
- **Parallel processing**: ParallelProcessingManager with auto-detection

**Memory Usage:**
- Test suite: 200-500 MB per worker
- Production: 500 MB - 1 GB for nightly pipeline
- Visualization: 200-500 MB

### What Breaks at 600K+ Nodes

**Memory Bottlenecks:**
1. **Full graph in memory**: 600K nodes × ~1KB per node = ~600 MB just for nodes
2. **Edge storage**: 600K nodes × avg 50 edges × ~100 bytes = ~3 GB for edges
3. **Community detection**: Louvain creates temporary structures, 2-3x graph size
4. **Centrality calculations**: Betweenness requires O(n²) space for some algorithms
5. **Layout calculation**: Spring layout stores positions, forces, velocities
6. **Total estimated**: 10-15 GB RAM for 600K nodes, 20-30 GB for 1M nodes

**Performance Bottlenecks:**
1. **Community detection**: O(n log n) but slow on large graphs
2. **Betweenness centrality**: O(n³) for exact, O(n²) for approximate
3. **Eigenvector centrality**: Iterative, slow convergence on large graphs
4. **Layout calculation**: O(n²) for spring layout
5. **Graph I/O**: Loading/saving 600K nodes takes minutes

**Visualization Bottlenecks:**
1. **Sigma.js**: Claims 10K+ support, but 600K nodes will be slow
2. **JSON serialization**: Converting 600K nodes to JSON is expensive
3. **Browser memory**: 600K nodes in browser = 5-10 GB RAM
4. **Rendering**: Even with WebGL, 600K nodes is pushing limits

---

## Auto-Scaling Architecture

### Existing Auto-Scaling Capabilities (Already Implemented ✅)

The system already has robust auto-scaling built into `ParallelProcessingManager`:

```python
class ParallelProcessingManager:
    def _detect_cpu_count(self) -> int:
        """Detect available CPU cores with fallback."""
        count = os.cpu_count()  # Returns 4 on GitHub Actions
        return count if count and count >= 1 else 2
    
    def _detect_ci_environment(self) -> dict:
        """Detect CI and apply appropriate strategy."""
        # GitHub Actions → "moderate" strategy
        # Local development → "aggressive" strategy
        # Unknown CI → "conservative" strategy
    
    def get_parallel_config(self, operation_type, graph_size, override_cores=None):
        """Auto-scale workers based on environment and workload."""
        # Automatically adjusts cores based on:
        # - Detected CPU count (1-4 cores)
        # - CI environment (GitHub Actions, local, etc.)
        # - Operation type (analysis, testing, visualization)
        # - Data size (graph_size parameter)
```

**What This Means:**
- ✅ System already scales from 1 core to 4 cores automatically
- ✅ System already detects GitHub Actions and optimizes accordingly
- ✅ System already adjusts workers based on workload size
- ✅ No changes needed for basic auto-scaling

**What We Need to Add:**
- Graph partitioning for distributed processing across runners
- Partition size auto-adjustment based on detected resources
- Cross-partition merge logic

## Architecture Changes Required

### Phase 1: Enable 600K Nodes with Matrix Distribution (Target: <30 min)

#### 1.1 Graph Partitioning System (NEW - Core Requirement)
**Problem:** Single runner can't hold 600K+ nodes in 7 GB RAM  
**Solution:** Partition graph across multiple runners with auto-scaling

```python
class GraphPartitioner:
    """Partition graphs for distributed processing with auto-scaling"""
    
    def __init__(self):
        self.parallel_manager = ParallelProcessingManager()
        self.detected_cores = self.parallel_manager._cpu_count  # Auto-detected
        self.detected_ram = self._detect_available_ram()  # 7 GB on GitHub
    
    def calculate_optimal_partitions(self, total_nodes: int) -> int:
        """Auto-calculate partition count based on resources."""
        # Auto-scale partition size based on detected resources
        if self.detected_ram >= 7:  # GitHub Actions standard
            nodes_per_partition = 50000  # Optimal for 7 GB
        elif self.detected_ram >= 4:
            nodes_per_partition = 30000  # Conservative for 4 GB
        else:
            nodes_per_partition = 10000  # Minimal for 2 GB
        
        return math.ceil(total_nodes / nodes_per_partition)
    
    def partition_graph(self, graph: nx.DiGraph, num_partitions: int):
        """Partition using METIS to minimize edge cuts."""
        # Use METIS or similar to create balanced partitions
        # Minimize cross-partition edges
        # Preserve community structure
        return partitions
    
    def save_partition(self, partition: nx.DiGraph, partition_id: int):
        """Save partition to artifact for matrix job."""
        # Save as compressed pickle or msgpack
        # Upload as GitHub Actions artifact
```

**Impact:** Enables processing beyond single-runner memory limits

#### 1.2 Partition Analysis Worker (NEW - Core Requirement)
**Problem:** Each partition needs independent analysis  
**Solution:** Worker that analyzes partition with auto-scaled resources

```python
class PartitionAnalysisWorker:
    """Analyze graph partition with auto-scaling."""
    
    def __init__(self, partition_id: int):
        self.partition_id = partition_id
        self.parallel_manager = ParallelProcessingManager()
        # Auto-detects 1-4 cores and scales accordingly
    
    def analyze_partition(self, partition: nx.DiGraph) -> PartitionResults:
        """Analyze partition using auto-scaled workers."""
        # Get auto-scaled parallel config
        config = self.parallel_manager.get_parallel_config(
            operation_type='analysis',
            graph_size=partition.number_of_nodes()
        )
        
        # Use detected cores for parallel processing
        with ProcessPoolExecutor(max_workers=config.cores_used) as executor:
            # Community detection on partition
            communities = self._detect_communities(partition)
            
            # Centrality calculation (parallelized)
            centrality = self._calculate_centrality(partition, executor)
            
            # Layout calculation
            layout = self._calculate_layout(partition)
        
        return PartitionResults(
            partition_id=self.partition_id,
            communities=communities,
            centrality=centrality,
            layout=layout,
            boundary_nodes=self._identify_boundary_nodes(partition)
        )
```

**Impact:** Each runner auto-scales to available resources (1-4 cores)

#### 1.3 Results Merger (NEW - Core Requirement)
**Problem:** Need to combine results from 20+ partitions  
**Solution:** Merge partition results into final graph

```python
class PartitionResultsMerger:
    """Merge results from distributed partition analysis."""
    
    def merge_communities(self, partition_results: List[PartitionResults]) -> dict:
        """Merge community assignments across partitions."""
        # Combine local communities
        # Resolve boundary node communities
        # Renumber communities globally
        return global_communities
    
    def merge_centrality(self, partition_results: List[PartitionResults]) -> dict:
        """Merge centrality scores across partitions."""
        # Aggregate betweenness scores
        # Normalize across full graph
        # Handle boundary nodes specially
        return global_centrality
    
    def merge_layouts(self, partition_results: List[PartitionResults]) -> dict:
        """Merge layout positions across partitions."""
        # Use community-based hierarchical layout
        # Position partitions relative to each other
        # Refine boundary node positions
        return global_layout
    
    def create_final_graph(self, original_graph: nx.DiGraph, 
                          merged_results: MergedResults) -> nx.DiGraph:
        """Create final graph with merged analysis results."""
        # Add community attributes
        # Add centrality attributes
        # Add layout positions
        return final_graph
```

**Impact:** Enables combining distributed analysis into coherent results

#### 1.4 GitHub Actions Workflow (NEW - Core Requirement)
**Problem:** Need to orchestrate distributed processing  
**Solution:** Matrix workflow with partition/analyze/merge steps

```yaml
# .github/workflows/large-graph-analysis.yml
name: Large Graph Analysis

jobs:
  partition:
    name: Partition Graph
    runs-on: ubuntu-latest
    outputs:
      num_partitions: ${{ steps.partition.outputs.num_partitions }}
      partition_ids: ${{ steps.partition.outputs.partition_ids }}
    steps:
      - name: Partition graph with auto-scaling
        id: partition
        run: |
          # Auto-calculate partitions based on graph size
          python scripts/partition_graph.py \
            --input graph.gpickle \
            --auto-scale \
            --output-dir partitions/
          
          # Output partition info for matrix
          echo "num_partitions=20" >> $GITHUB_OUTPUT
          echo "partition_ids=[0,1,2,...,19]" >> $GITHUB_OUTPUT
      
      - name: Upload partitions as artifacts
        uses: actions/upload-artifact@v4
        with:
          name: graph-partitions
          path: partitions/
  
  analyze:
    name: Analyze Partition ${{ matrix.partition_id }}
    needs: partition
    runs-on: ubuntu-latest
    strategy:
      matrix:
        partition_id: ${{ fromJson(needs.partition.outputs.partition_ids) }}
      max-parallel: 20  # All 20 run concurrently
      fail-fast: false  # Continue even if one fails
    steps:
      - name: Download partition
        uses: actions/download-artifact@v4
        with:
          name: graph-partitions
      
      - name: Analyze partition (auto-scaled)
        run: |
          # Worker auto-detects 4 cores and scales
          python scripts/analyze_partition.py \
            --partition-id ${{ matrix.partition_id }} \
            --auto-scale
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: partition-results-${{ matrix.partition_id }}
          path: results/partition-${{ matrix.partition_id }}.pkl
  
  merge:
    name: Merge Results
    needs: analyze
    runs-on: ubuntu-latest
    steps:
      - name: Download all partition results
        uses: actions/download-artifact@v4
        with:
          pattern: partition-results-*
          merge-multiple: true
      
      - name: Merge results
        run: |
          python scripts/merge_results.py \
            --input-dir results/ \
            --output final_graph.gpickle
      
      - name: Generate visualization
        run: |
          python scripts/visualize.py \
            --input final_graph.gpickle \
            --output visualization.html
```

**Impact:** Enables distributed processing across 20+ runners

#### 1.5 Checkpoint-Based Processing
**Problem:** 30-minute processing can fail, losing all progress  
**Solution:** Checkpoint system (similar to Freesound pipeline)

```python
class GraphAnalysisCheckpoint:
    """Save progress during long-running analysis"""
    
    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_interval = 50000  # Every 50K nodes
    
    def save_checkpoint(self, phase: str, graph: nx.DiGraph, metadata: dict):
        """Save analysis state"""
        checkpoint_file = self.checkpoint_dir / f"{phase}_checkpoint.pkl"
        joblib.dump({
            'graph': graph,
            'metadata': metadata,
            'timestamp': datetime.now()
        }, checkpoint_file, compress=3)
    
    def load_checkpoint(self, phase: str) -> Optional[dict]:
        """Resume from checkpoint"""
        
    def clear_checkpoint(self, phase: str):
        """Remove checkpoint after successful completion"""
```

**Impact:** Enables resumption after failures

#### 1.6 Optimized Visualization Strategy
**Problem:** 600K nodes won't render in browser  
**Solution:** Multi-tier visualization approach

```python
class LargeGraphVisualizer:
    """Visualization strategies for large graphs"""
    
    def create_overview_visualization(self, graph: nx.DiGraph, max_nodes: int = 5000):
        """Create simplified overview with top nodes"""
        # Strategy 1: Show only high-degree nodes
        # Strategy 2: Show community representatives
        # Strategy 3: Hierarchical aggregation
        
    def create_interactive_explorer(self, graph: nx.DiGraph):
        """Create drill-down interface"""
        # Save full graph to disk
        # Generate overview visualization
        # Enable on-demand subgraph loading
        
    def export_for_gephi(self, graph: nx.DiGraph, output_path: str):
        """Export to Gephi for desktop visualization"""
        nx.write_gexf(graph, output_path)
```

**Impact:** Enables visualization of large graphs through sampling/aggregation

---

### Phase 2: Scale to 1M+ Nodes (Target: <60 min processing)

#### 2.1 Distributed Graph Processing
**Problem:** Single machine can't handle 1M+ nodes efficiently  
**Solution:** Distributed processing framework

**Options:**
- **GraphX (Spark)**: Distributed graph processing
- **Dask + NetworkX**: Distributed NetworkX operations
- **Custom sharding**: Partition graph across multiple processes

```python
class DistributedGraphProcessor:
    """Process graphs across multiple workers"""
    
    def partition_graph(self, graph: nx.DiGraph, num_partitions: int):
        """Partition graph using METIS or similar"""
        
    def distributed_analysis(self, partitions: List[nx.DiGraph]):
        """Analyze partitions in parallel, merge results"""
```

**Impact:** Enables processing beyond single-machine limits

#### 2.2 Graph Database Backend
**Problem:** SQLite not optimized for graph queries  
**Solution:** Use graph database (Neo4j, ArangoDB, or DGraph)

```python
class GraphDatabaseBackend:
    """Use graph database for storage and queries"""
    
    def __init__(self, db_url: str):
        self.driver = neo4j.GraphDatabase.driver(db_url)
    
    def run_cypher_query(self, query: str):
        """Execute Cypher query for graph operations"""
        
    def calculate_centrality_in_db(self):
        """Use database's built-in graph algorithms"""
```

**Impact:** Optimized storage and query performance

#### 2.3 Incremental Analysis
**Problem:** Reanalyzing 1M nodes after small changes is wasteful  
**Solution:** Incremental update algorithms

```python
class IncrementalAnalyzer:
    """Update analysis incrementally as graph changes"""
    
    def update_community_detection(self, graph: nx.DiGraph, 
                                   new_nodes: List[str], 
                                   removed_nodes: List[str]):
        """Update communities without full recomputation"""
        
    def update_centrality(self, graph: nx.DiGraph, changed_edges: List[tuple]):
        """Incrementally update centrality scores"""
```

**Impact:** 10-100x faster for small graph changes

#### 2.4 Compressed Graph Representation
**Problem:** 1M nodes × 1KB = 1GB just for node storage  
**Solution:** Compressed graph formats

```python
class CompressedGraph:
    """Memory-efficient graph representation"""
    
    def __init__(self):
        # Use compressed sparse row (CSR) format
        # Store node IDs as integers, not strings
        # Compress attributes with msgpack or similar
        
    def to_networkx(self) -> nx.DiGraph:
        """Convert to NetworkX for analysis"""
        
    def from_networkx(self, graph: nx.DiGraph):
        """Convert from NetworkX to compressed format"""
```

**Impact:** 50-70% memory reduction

#### 2.5 Streaming Visualization
**Problem:** Can't load 1M nodes in browser  
**Solution:** Server-side rendering with streaming

```python
class StreamingVisualizer:
    """Stream visualization data to browser"""
    
    def create_tile_based_visualization(self, graph: nx.DiGraph):
        """Render graph in tiles, load on-demand"""
        
    def create_lod_visualization(self, graph: nx.DiGraph):
        """Level-of-detail rendering (zoom to see more nodes)"""
```

**Impact:** Enables browser-based exploration of massive graphs

---

## Implementation Roadmap

### Milestone 1: 100K Nodes (2-3 weeks)
- [ ] Implement streaming graph loading
- [ ] Add approximate betweenness centrality
- [ ] Optimize community detection for large graphs
- [ ] Add progress checkpoints
- [ ] Test with 100K node synthetic graph

**Success Criteria:** Process 100K nodes in <10 minutes

### Milestone 2: 300K Nodes (2-3 weeks)
- [ ] Implement disk-backed graph storage (SQLite)
- [ ] Add parallel graph processing
- [ ] Implement sampling-based centrality
- [ ] Optimize visualization for large graphs
- [ ] Test with 300K node synthetic graph

**Success Criteria:** Process 300K nodes in <20 minutes

### Milestone 3: 600K Nodes (2-3 weeks)
- [ ] Optimize memory usage across all components
- [ ] Implement hierarchical visualization
- [ ] Add export to Gephi for desktop analysis
- [ ] Performance tuning and optimization
- [ ] Test with 600K node real-world graph

**Success Criteria:** Process 600K nodes in <30 minutes, <15 GB RAM

### Milestone 4: 1M+ Nodes (4-6 weeks)
- [ ] Evaluate distributed processing frameworks
- [ ] Implement graph database backend (optional)
- [ ] Add incremental analysis capabilities
- [ ] Implement compressed graph representation
- [ ] Test with 1M+ node graph

**Success Criteria:** Process 1M nodes in <60 minutes

---

## Technical Decisions

### Libraries to Add

**Graph Processing:**
- `graph-tool`: Fast C++ graph library with Python bindings (alternative to NetworkX)
- `networkit`: High-performance graph algorithms
- `python-igraph`: Fast graph library
- `dask`: Distributed computing (if going distributed)

**Storage:**
- `sqlalchemy`: ORM for SQLite backend
- `neo4j-driver`: If using Neo4j graph database
- `pyarrow`: Columnar storage for graph data

**Compression:**
- `msgpack`: Fast serialization
- `zstandard`: Fast compression

**Visualization:**
- `datashader`: Render large datasets to images
- `holoviews`: High-level visualization

### Algorithms to Replace

**Current → Large-Scale Alternative:**
- Louvain communities → Leiden algorithm (faster)
- Exact betweenness → Approximate betweenness (k-sampling)
- Eigenvector centrality → PageRank (faster convergence)
- Spring layout → ForceAtlas2 (faster for large graphs)
- Full graph analysis → Sampling + extrapolation

### Memory Budget

**Target Memory Usage:**
- 100K nodes: <2 GB RAM
- 300K nodes: <5 GB RAM
- 600K nodes: <15 GB RAM
- 1M nodes: <25 GB RAM

**Strategies:**
- Streaming: Process in chunks
- Disk-backing: Store on disk, load working set
- Compression: Reduce in-memory footprint
- Sampling: Analyze representative subset

---

## Integration with Repository Cleanup Spec

This large-scale graph handling will be added to the repository-cleanup spec as **Requirement 20: Large-Scale Graph Analysis**.

### Why Add to Repository Cleanup Spec?

1. **Scalability patterns already established**: Requirement 19 covers 10K+ file handling with:
   - Streaming architecture
   - SQLite state database
   - Checkpoint/resume
   - Parallel processing
   - Progress tracking

2. **Same architectural patterns apply**:
   - 10K+ files → 600K+ nodes
   - File operations → Graph operations
   - State database → Graph database
   - Checkpoints → Analysis checkpoints

3. **Reuse existing utilities**:
   - ParallelProcessingManager
   - ProgressTracker
   - Checkpoint patterns from Freesound pipeline
   - SQLite patterns from MetadataCache

4. **Consistent implementation approach**:
   - Always-on optimizations (all scales)
   - Automatic large-scale optimizations (600K+ threshold)
   - Configuration and metrics

### Proposed Requirement 20 Structure

**Requirement 20: Large-Scale Graph Analysis (600K+ Nodes)**

**User Story:** As a network analyst, I want FollowWeb to handle graphs with 600,000+ nodes efficiently, so that I can analyze massive social networks and audio sample collections without memory exhaustion or excessive processing time.

**Acceptance Criteria:**

**Always-On Optimizations (All Graph Sizes):**
1. Centralized caching for graph conversions
2. Parallel processing with auto-detection
3. Progress tracking with ETA
4. Optimized algorithms (Louvain, approximate betweenness)

**Automatic Large-Scale Optimizations (600K+ Nodes):**
5. Streaming graph loading with batching
6. Disk-backed graph storage (SQLite)
7. Checkpoint/resume for long-running analysis
8. Sampling-based centrality calculations
9. Hierarchical visualization strategies

**Configuration and Metrics:**
10. Configurable thresholds, batch sizes, sample sizes
11. Performance metrics (nodes/second, memory usage, checkpoint count)
12. Target: 600K nodes in <30 minutes, <15 GB RAM

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Create detailed spec** as Requirement 20 in repository-cleanup
3. **Prototype streaming loader** with 100K synthetic graph
4. **Benchmark current vs. optimized** approaches
5. **Implement Milestone 1** (100K nodes)

---

## GitHub Actions Constraints (Free Tier)

### Current Runner Limits

**GitHub-hosted runners (free tier) - VERIFIED FROM CI LOGS:**
- **CPU**: 4 cores per runner (detected: `os.cpu_count()` returns 4)
- **RAM**: 7 GB per runner (GitHub standard)
- **Disk**: 14 GB SSD per runner
- **Timeout**: 6 hours max (360 minutes)
- **Concurrent jobs**: 20 for free accounts
- **Matrix parallelism**: Up to 256 jobs in matrix
- **Auto-scaling**: System automatically detects 1-4 cores and adjusts workers

**Current workflow timeouts:**
- Freesound nightly: 120 minutes (2 hours)
- Full validation: 180 minutes (3 hours)
- Test suite: 30 minutes
- CI matrix: 30 minutes per job

### Distributed Processing Strategy for 1M+ Nodes (Free GitHub ✅)

**Key Insight:** We can use GitHub Actions matrix strategy to split work across multiple runners!

**Available Resources with Matrix:**
- 20 concurrent runners × 7 GB RAM = **140 GB total RAM**
- 20 concurrent runners × 4 cores = **80 cores total**
- Each runner processes a partition independently
- **Auto-scaling**: Each runner auto-detects 1-4 cores and scales workers accordingly

**Graph Partitioning Approach:**

```yaml
# .github/workflows/large-graph-analysis.yml
jobs:
  partition-graph:
    runs-on: ubuntu-latest
    outputs:
      partitions: ${{ steps.partition.outputs.partitions }}
    steps:
      - name: Partition graph into chunks
        id: partition
        run: |
          # Split 1M nodes into 20 partitions of 50K nodes each
          # Each partition fits in 7 GB RAM
          python scripts/partition_graph.py --nodes 1000000 --partitions 20
  
  analyze-partition:
    needs: partition-graph
    runs-on: ubuntu-latest
    strategy:
      matrix:
        partition: ${{ fromJson(needs.partition-graph.outputs.partitions) }}
      max-parallel: 20  # All 20 run concurrently
    steps:
      - name: Analyze partition ${{ matrix.partition }}
        run: |
          # Each runner processes 50K nodes (fits in 7 GB)
          python scripts/analyze_partition.py --partition ${{ matrix.partition }}
  
  merge-results:
    needs: analyze-partition
    runs-on: ubuntu-latest
    steps:
      - name: Merge partition results
        run: |
          # Combine results from all 20 partitions
          python scripts/merge_results.py
```

**Partitioning Strategy:**

1. **Node Partitioning** (50K nodes per runner)
   - 1M nodes ÷ 20 runners = 50K nodes per partition
   - 50K nodes × 1KB = ~50 MB base
   - With edges: ~2-3 GB per partition ✅ Fits in 7 GB

2. **Community Detection** (Distributed Louvain)
   - Each partition runs local community detection
   - Merge communities across partitions
   - Refinement pass on merged graph

3. **Centrality Calculation** (Distributed Betweenness)
   - Each runner calculates betweenness for subset of nodes
   - Aggregate results in merge step
   - Use sampling for approximate results

4. **Layout Calculation** (Hierarchical Layout)
   - Each partition calculates local layout
   - Merge layouts using force-directed refinement
   - Or use community-based hierarchical layout

**Memory Budget per Partition (Auto-Scaling):**
- 50K nodes: ~50 MB
- Edges (avg 50 per node): ~250 MB
- Community detection overhead: ~1 GB
- Centrality calculation: ~1 GB
- Working memory: ~500 MB
- **Total: ~3 GB per partition** ✅ Well under 7 GB limit

**Auto-Scaling Capabilities:**
- **CPU Detection**: `ParallelProcessingManager` auto-detects 1-4 cores via `os.cpu_count()`
- **Worker Scaling**: Automatically adjusts workers based on detected cores
- **CI Detection**: Recognizes GitHub Actions and applies "moderate" strategy
- **Memory Adaptation**: Can scale down to 1 core / 2 GB RAM if needed
- **Partition Sizing**: Dynamically adjusts partition size based on available resources
  - 4 cores + 7 GB RAM: 50K nodes per partition (optimal)
  - 2 cores + 4 GB RAM: 30K nodes per partition (conservative)
  - 1 core + 2 GB RAM: 10K nodes per partition (minimal)

**Revised Feasibility:**
- ✅ **100K nodes**: 2 partitions × 50K = 10 minutes total
- ✅ **300K nodes**: 6 partitions × 50K = 15 minutes total
- ✅ **600K nodes**: 12 partitions × 50K = 20 minutes total
- ✅ **1M nodes**: 20 partitions × 50K = 25 minutes total
- ✅ **2M nodes**: 40 partitions (2 waves) = 50 minutes total
- ✅ **5M nodes**: 100 partitions (5 waves) = 120 minutes total

### Revised Architecture for GitHub Free Tier (With Matrix Distribution)

#### Tier 1: Up to 100K Nodes (Single Runner ✅)
- **Memory**: <2 GB per runner
- **Time**: <10 minutes
- **Strategy**: In-memory processing with optimizations
- **Runners**: 1-2 runners
- **Use case**: Most Instagram networks, small Freesound collections

#### Tier 2: 100K-500K Nodes (Matrix 2-10 runners ✅)
- **Memory**: 2-4 GB per partition
- **Time**: 15-20 minutes
- **Strategy**: Graph partitioning across 2-10 runners
- **Runners**: 2-10 concurrent runners
- **Use case**: Large Instagram networks, medium Freesound collections

#### Tier 3: 500K-1M Nodes (Matrix 10-20 runners ✅)
- **Memory**: 3-4 GB per partition
- **Time**: 20-30 minutes
- **Strategy**: Graph partitioning across 10-20 runners
- **Runners**: 10-20 concurrent runners (50K nodes each)
- **Use case**: Very large networks, large Freesound collections

#### Tier 4: 1M-2M Nodes (Matrix 20-40 runners ✅)
- **Memory**: 3-4 GB per partition
- **Time**: 40-60 minutes
- **Strategy**: Graph partitioning in 2 waves (20 runners × 2)
- **Runners**: 40 total (20 concurrent, 2 waves)
- **Use case**: Massive networks

#### Tier 5: 2M-5M Nodes (Matrix 40-100 runners ✅)
- **Memory**: 3-4 GB per partition
- **Time**: 90-120 minutes
- **Strategy**: Graph partitioning in 5 waves (20 runners × 5)
- **Runners**: 100 total (20 concurrent, 5 waves)
- **Use case**: Extreme scale networks

### Recommended Approach (Matrix Distribution)

**For Free GitHub Actions (Up to 5M nodes!):**
1. **Implement graph partitioning** to split work across runners
2. **Use matrix strategy** to run partitions in parallel
3. **Optimize partition size** to fit in 7 GB per runner (50K nodes ideal)
4. **Merge results** efficiently after parallel processing
5. **Handle cross-partition edges** in merge step

**Key Algorithms for Distribution:**

1. **Graph Partitioning** (METIS or similar)
   - Minimize cross-partition edges
   - Balance partition sizes
   - Preserve community structure

2. **Distributed Community Detection**
   - Local Louvain on each partition
   - Merge communities across partitions
   - Refinement pass on boundary nodes

3. **Distributed Centrality**
   - Approximate betweenness using sampling
   - Each runner calculates for subset
   - Aggregate and normalize results

4. **Distributed Layout**
   - Community-based hierarchical layout
   - Each partition calculates local positions
   - Global refinement in merge step

### Updated Memory Budget (GitHub Free Tier with Matrix)

**Per-Partition Memory Usage (7 GB limit per runner):**
- 50K nodes partition: ~3 GB RAM ✅ (ideal partition size)
- 100K nodes partition: ~5 GB RAM ✅ (acceptable)
- 150K nodes partition: ~7 GB RAM ⚠️ (at limit)

**Total Graph Capacity (with matrix distribution):**
- 100K nodes: 2 partitions × 50K = 6 GB total (2 runners)
- 500K nodes: 10 partitions × 50K = 30 GB total (10 runners)
- 1M nodes: 20 partitions × 50K = 60 GB total (20 runners)
- 2M nodes: 40 partitions × 50K = 120 GB total (40 runners, 2 waves)
- 5M nodes: 100 partitions × 50K = 300 GB total (100 runners, 5 waves)

**Strategies for Efficient Partitioning:**
1. **METIS partitioning**: Minimize cross-partition edges
2. **Balanced partitions**: Equal node distribution
3. **Community-aware**: Keep communities together
4. **Minimal edge cuts**: Reduce merge complexity
5. **Compressed storage**: Use efficient formats for partition data

### Updated Milestones (Matrix Distribution)

**Milestone 1: 100K Nodes (Single Runner ✅)**
- Target: <2 GB RAM, <10 minutes
- Strategy: Optimized in-memory with caching
- Runners: 1 runner
- **Status**: Already achievable with current architecture

**Milestone 2: 300K Nodes (Matrix 6 runners ✅)**
- Target: 6 × 3 GB = 18 GB total, <15 minutes
- Strategy: Graph partitioning + matrix distribution
- Runners: 6 concurrent runners (50K nodes each)
- **New capability**: Implement partitioning system

**Milestone 3: 600K Nodes (Matrix 12 runners ✅)**
- Target: 12 × 3 GB = 36 GB total, <20 minutes
- Strategy: Graph partitioning + matrix distribution
- Runners: 12 concurrent runners (50K nodes each)
- **New capability**: Distributed community detection

**Milestone 4: 1M Nodes (Matrix 20 runners ✅)**
- Target: 20 × 3 GB = 60 GB total, <25 minutes
- Strategy: Graph partitioning + matrix distribution
- Runners: 20 concurrent runners (50K nodes each)
- **New capability**: Distributed centrality calculation

**Milestone 5: 2M Nodes (Matrix 40 runners ✅)**
- Target: 40 × 3 GB = 120 GB total, <50 minutes
- Strategy: Graph partitioning in 2 waves
- Runners: 40 total (20 concurrent × 2 waves)
- **New capability**: Multi-wave processing

**Milestone 6: 5M Nodes (Matrix 100 runners ✅)**
- Target: 100 × 3 GB = 300 GB total, <120 minutes
- Strategy: Graph partitioning in 5 waves
- Runners: 100 total (20 concurrent × 5 waves)
- **New capability**: Extreme-scale processing

---

## Summary: What Changed

### Key Insights from CI Log Analysis

1. **GitHub runners have 4 cores** (not 2) - verified from CI logs showing `os.cpu_count()` returns 4
2. **Auto-scaling already works** - `ParallelProcessingManager` detects 1-4 cores and scales automatically
3. **Matrix distribution is the key** - 20 concurrent runners × 4 cores = 80 total cores, 140 GB total RAM
4. **1M+ nodes is achievable on free GitHub** - with graph partitioning and matrix distribution

### Revised Feasibility (Free GitHub Actions)

| Graph Size | Partitions | Runners | Time | Status |
|------------|-----------|---------|------|--------|
| 100K nodes | 2 | 2 | 10 min | ✅ Single runner works |
| 300K nodes | 6 | 6 | 15 min | ✅ Matrix distribution |
| 600K nodes | 12 | 12 | 20 min | ✅ Matrix distribution |
| 1M nodes | 20 | 20 | 25 min | ✅ Matrix distribution |
| 2M nodes | 40 | 20×2 waves | 50 min | ✅ Multi-wave |
| 5M nodes | 100 | 20×5 waves | 120 min | ✅ Multi-wave |

### What Needs to Be Built

**Core Components (NEW):**
1. **GraphPartitioner** - Split graph into balanced partitions (METIS)
2. **PartitionAnalysisWorker** - Analyze partition with auto-scaled workers
3. **PartitionResultsMerger** - Combine results from distributed analysis
4. **GitHub Actions Workflow** - Orchestrate partition/analyze/merge

**Existing Components (REUSE ✅):**
1. **ParallelProcessingManager** - Already auto-scales to 1-4 cores
2. **ProgressTracker** - Already tracks progress with ETA
3. **Checkpoint system** - Already implemented in Freesound pipeline
4. **SQLite patterns** - Already implemented in MetadataCache

### Integration with Repository Cleanup Spec

**Recommendation:** Add as **Requirement 20: Large-Scale Graph Analysis (600K+ Nodes)**

This fits perfectly because:
- Repository cleanup spec already has Requirement 19 for 10K+ file scalability
- Same patterns apply: streaming, checkpoints, SQLite, parallel processing, auto-scaling
- Same utilities: ParallelProcessingManager, ProgressTracker, checkpoint patterns
- Consistent architecture: always-on optimizations + automatic large-scale optimizations

**Where to Update Existing Spec:**

📋 **`.kiro/specs/repository-cleanup/requirements.md`**
- Add Requirement 20 after Requirement 19
- Follow same structure: User Story + Acceptance Criteria
- Organize into: Always-On Optimizations, Automatic Large-Scale Optimizations, Configuration

📋 **`.kiro/specs/repository-cleanup/design.md`**
- Add "Graph Analysis Components" section
- Add GraphPartitioner, PartitionAnalysisWorker, PartitionResultsMerger
- Add data models: PartitionInfo, PartitionResults, MergedResults
- Add GitHub Actions workflow design

📋 **`.kiro/specs/repository-cleanup/tasks.md`**
- Add Phase 6: Large-Scale Graph Analysis Implementation
- Tasks for partitioning, worker, merger, workflow
- Tests for 100K, 300K, 600K, 1M node graphs

---

## Next Steps

1. **Review this plan** - Confirm approach and feasibility
2. **Decide on integration** - Add to repository-cleanup spec as Requirement 20?
3. **Prototype partitioner** - Test METIS partitioning with 100K synthetic graph
4. **Implement Milestone 1** - 100K nodes with basic partitioning
5. **Scale to 1M nodes** - Full matrix distribution implementation

---

**Status:** Ready for Review  
**Next Update:** After confirmation to integrate with repository-cleanup spec
