# CI and Docs Pipeline Dependency Analysis

## Current Dependency Graph

### What Users See on GitHub (Simplified View)

```
                    ┌─────────────┐
                    │  prebuild   │ (runs independently)
                    └─────────────┘

┌─────────────┐
│ test-quick  │ (smoke test - runs immediately)
└──────┬──────┘
       │
       ├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
       │              │              │              │              │              │
       v              v              v              v              v              v
   ┌──────┐    ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐  ┌──────────────┐
   │ test │    │  security  │  │format-check│  │performance │  │ build  │  │documentation │
   └───┬──┘    └──────┬─────┘  └──────┬─────┘  └──────┬─────┘  └───┬────┘  └──────┬───────┘
       │              │                │                │            │              │
       └──────────────┴────────────────┴────────────────┴────────────┴──────────────┘
                                              │
                                              v
                                      ┌───────────────┐
                                      │  ci-success   │
                                      └───────────────┘
```

**Note:** GitHub's visual graph shows `prebuild` connected to 5 jobs (test, security, format-check, performance, documentation) and `build` connected to 3 jobs (test-quick, format-check, security), creating a complex web of 13+ visible dependency lines.

### Actual Job Dependencies (What GitHub Shows)

```yaml
prebuild:
  # No dependencies - runs immediately

test-quick:
  # No dependencies - runs immediately

test:
  needs: [test-quick, prebuild]  # 2 incoming arrows

security:
  needs: [prebuild]  # 1 incoming arrow

format-check:
  needs: [prebuild]  # 1 incoming arrow

performance:
  needs: [prebuild]  # 1 incoming arrow

build:
  needs: [test-quick, format-check, security]  # 3 incoming arrows

documentation:
  needs: [test-quick, prebuild]  # 2 incoming arrows
  # Calls docs.yml (3 sub-jobs hidden from main graph)

ci-success:
  needs: [test-quick, test, security, format-check, 
          build, performance, documentation]  # 7 incoming arrows
```

### Complexity Count

**Total visible dependency arrows on GitHub:** 17
- prebuild → 5 jobs (test, security, format-check, performance, documentation)
- test-quick → 4 jobs (test, build, documentation, ci-success)
- test → 1 job (ci-success)
- security → 2 jobs (build, ci-success)
- format-check → 2 jobs (build, ci-success)
- performance → 1 job (ci-success)
- build → 1 job (ci-success)
- documentation → 1 job (ci-success)

### Documentation Sub-Pipeline (Hidden in workflow_call)

The `documentation` job calls `docs.yml` which has 3 sequential jobs:

```
documentation-structure
         ↓
docstring-coverage
         ↓
conventional-commits (non-blocking)
```

These 3 jobs are **not visible** in the main CI graph on GitHub.

## ✅ IMPLEMENTED: Simplified Flow (Same Nodes, Fewer Edges)

### Goal: Reduce from 17 arrows to 10 arrows ✅ COMPLETE

All 10 jobs remain, but redundant dependency edges have been removed:

```
┌─────────────┐
│  prebuild   │ (runs independently, no outgoing edges)
└─────────────┘

┌─────────────┐
│ test-quick  │ (smoke test - gates everything)
└──────┬──────┘
       │
       ├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
       │              │              │              │              │              │
       v              v              v              v              v              v
   ┌──────┐    ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐  ┌──────────────┐
   │ test │    │  security  │  │format-check│  │performance │  │ build  │  │documentation │
   └───┬──┘    └──────┬─────┘  └──────┬─────┘  └──────┬─────┘  └───┬────┘  └──────┬───────┘
       │              │                │                │            │              │
       └──────────────┴────────────────┴────────────────┴────────────┴──────────────┘
                                              │
                                              v
                                      ┌───────────────┐
                                      │  ci-success   │
                                      └───────────────┘
```

### ✅ Implemented Changes to Job Dependencies

```yaml
prebuild:
  # No dependencies - runs in background
  # ✅ REMOVED: All outgoing dependencies (was connected to 5 jobs)

test-quick:
  # No dependencies - runs immediately

test:
  needs: [test-quick]  # ✅ REMOVED: prebuild dependency
  # Cache restored by key pattern, not job dependency

security:
  needs: [test-quick]  # ✅ CHANGED: was [prebuild], now [test-quick]
  # Cache restored by key pattern, not job dependency

format-check:
  needs: [test-quick]  # ✅ CHANGED: was [prebuild], now [test-quick]
  # Cache restored by key pattern, not job dependency

performance:
  needs: [test-quick]  # ✅ CHANGED: was [prebuild], now [test-quick]
  # Cache restored by key pattern, not job dependency

build:
  needs: [test-quick]  # ✅ CHANGED: was [test-quick, format-check, security]
  # Build doesn't actually need format/security to pass first

documentation:
  needs: [test-quick]  # ✅ CHANGED: was [test-quick, prebuild]
  # Cache restored by key pattern, not job dependency
  # ✅ REMOVED: prebuild-cache-key input to docs.yml

ci-success:
  needs: [test-quick, test, security, format-check, 
          build, performance, documentation]  # UNCHANGED
```

### Complexity Comparison

| Metric | Current | Proposed | Reduction |
|--------|---------|----------|-----------|
| **Total dependency arrows** | 17 | 10 | -41% |
| **Jobs with multiple inputs** | 4 jobs | 1 job | -75% |
| **Max incoming arrows** | 7 (ci-success) | 7 (ci-success) | 0% |
| **Prebuild connections** | 5 outgoing | 0 outgoing | -100% |
| **Build connections** | 3 incoming | 1 incoming | -67% |
| **Visual complexity** | High | Low | Much cleaner |

### Key Simplifications

1. **Remove prebuild job dependencies** (5 edges removed)
   - Jobs still use cache via key pattern matching
   - No visual dependency arrows from prebuild
   - Cache becomes opportunistic optimization, not required

2. **Simplify build dependencies** (2 edges removed)
   - Build only needs test-quick to pass
   - Format-check and security run in parallel
   - All validation still happens before ci-success

3. **Standardize on test-quick as gate** (consistency)
   - All jobs depend on test-quick passing
   - Creates clean 2-level hierarchy
   - Easy to understand: "smoke test gates everything"

### ✅ Implemented Cache Handling Without Job Dependencies

Jobs now restore cache by key pattern instead of job dependency:

```yaml
- name: Restore prebuild cache
  uses: actions/cache/restore@v4
  with:
    path: |
      ~/.cache/pip
      FollowWeb/.venv
      FollowWeb/tests/test_data
      .pytest_cache
      .mypy_cache
      .ruff_cache
    key: prebuild-${{ runner.os }}-py3.12-${{ hashFiles('FollowWeb/requirements-ci.txt', 'FollowWeb/pyproject.toml') }}
    restore-keys: |
      prebuild-${{ runner.os }}-py3.12-
```

**✅ Implemented Benefits:**
- Cache still works if prebuild succeeds
- Jobs don't wait for prebuild to complete
- No visual dependency clutter (7 fewer arrows!)
- Prebuild runs in background as pure optimization
- All jobs in ci.yml updated
- All jobs in docs.yml updated
- docs.yml no longer requires prebuild-cache-key input

## Issues with Current Structure

### 1. **Redundant Cache Dependencies**
- **Problem**: Every job depends on `prebuild` just to get the cache key
- **Impact**: Creates visual clutter in the dependency graph
- **Reality**: Most jobs install dependencies fresh anyway (except Ubuntu 3.12)

### 2. **Documentation Pipeline Isolation**
- **Problem**: Documentation is a separate workflow_call with its own 3-job chain
- **Impact**: 
  - Adds complexity to the graph
  - Requires passing cache-key as input
  - Creates nested dependency visualization
  - Each doc job restores the same cache independently

### 3. **Prebuild Runs in Parallel with Smoke Test**
- **Problem**: Prebuild doesn't gate anything critical
- **Impact**: If prebuild fails, other jobs continue anyway
- **Reality**: Cache is optional - jobs work without it

### 4. **Build Job Has Unnecessary Dependencies**
- **Current**: `needs: [test-quick, format-check, security]`
- **Problem**: Build doesn't actually need format-check or security to pass
- **Reality**: Build only needs code to be syntactically valid

## Proposed Simplifications

### Phase 1: Simplify Dependencies (⭐ RECOMMENDED)

**Benefits:**
- Clean 2-level dependency graph
- Maintains workflow separation (best practice)
- True parallel execution
- Minimal code changes
- Cache becomes opportunistic, not required

**Changes:**
```yaml
jobs:
  prebuild:
    # Runs in background, no jobs depend on it
  
  test-quick:
    # Gates everything (no prebuild dependency)
  
  # All jobs run in parallel after smoke test
  test:
    needs: test-quick  # Remove: prebuild
  
  security:
    needs: test-quick  # Remove: prebuild
  
  format-check:
    needs: test-quick  # Remove: prebuild
  
  performance:
    needs: test-quick  # Remove: prebuild
  
  build:
    needs: test-quick  # Remove: format-check, security, prebuild
  
  documentation:
    needs: test-quick  # Remove: prebuild
    uses: ./.github/workflows/docs.yml  # Keep as separate workflow
  
  ci-success:
    needs: [test-quick, test, security, format-check, 
            build, performance, documentation]
```

**New Graph (Phase 1):**
```
┌─────────────┐
│  prebuild   │ (background, optional)
└─────────────┘

┌─────────────┐
│ test-quick  │ ← Stage 1: Smoke test (1-2 min)
└──────┬──────┘
       │
   ┌───┼───┬───┬───┬───┐
   v   v   v   v   v   v
┌────┐┌──┐┌──┐┌──┐┌───┐┌────┐
│test││sc││fm││pf││bld││docs│ ← Stage 2: All parallel (20-25 min)
└─┬──┘└┬─┘└┬─┘└┬─┘└─┬─┘└─┬──┘
  └────┴───┴───┴───┴────┘
              │
              v
       ┌─────────────┐
       │ ci-success  │
       └─────────────┘
```

### Alternative: Flatten Documentation into Main Pipeline

**Benefits:**
- Single workflow file
- No workflow_call overhead
- All jobs visible in one place

**Drawbacks:**
- ❌ Loses separation of concerns
- ❌ Can't reuse docs workflow elsewhere
- ❌ Harder to run docs independently
- ❌ Not following best practices for workflow composition

**Graph (Flattened):**
```
┌─────────────┐
│ test-quick  │
└──────┬──────┘
   ┌───┼───┬───┬───┬───┐
   v   v   v   v   v   v
┌────┐┌──┐┌──┐┌──┐┌───┐┌────┐
│test││sc││fm││pf││bld││d-st│
└─┬──┘└┬─┘└┬─┘└┬─┘└─┬─┘└─┬──┘
  │    │   │   │    │    v
  │    │   │   │    │  ┌────┐
  │    │   │   │    │  │d-cv│
  │    │   │   │    │  └─┬──┘
  │    │   │   │    │    v
  │    │   │   │    │  ┌────┐
  │    │   │   │    │  │d-cm│
  │    │   │   │    │  └─┬──┘
  └────┴───┴───┴────┴────┘
              │
              v
       ┌─────────────┐
       │ ci-success  │
       └─────────────┘
```

### Alternative: Merge Documentation into Existing Jobs

**Benefits:**
- Fewest total jobs (6 instead of 10)
- Simplest possible graph
- Fastest execution

**Drawbacks:**
- ❌ Mixes concerns (code tests + doc checks)
- ❌ Harder to understand what each job does
- ❌ Can't run doc checks independently
- ❌ Violates single responsibility principle

**Graph (Merged):**
```
┌─────────────┐
│ test-quick  │
└──────┬──────┘
   ┌───┼───┬───┬───┐
   v   v   v   v   v
┌────┐┌──┐┌────┐┌──┐┌───┐
│test││sc││fmt+││pf││bld│
│+doc││  ││docs││  ││   │
└─┬──┘└┬─┘└─┬──┘└┬─┘└─┬─┘
  └────┴────┴────┴────┘
            │
            v
     ┌─────────────┐
     │ ci-success  │
     └─────────────┘
```

## Comparison Matrix

| Aspect | Current | Phase 1 (Recommended) | Option 1 (Flatten) | Option 3 (Merge) |
|--------|---------|----------------------|-------------------|------------------|
| **Total Jobs** | 10 (7 main + 3 docs) | 10 (7 main + 3 docs) | 10 (all in main) | 6 |
| **Dependency Depth** | 4 levels | 2 levels | 3 levels | 2 levels |
| **Graph Complexity** | High (nested) | Low | Medium | Low |
| **Workflow Files** | 2 (ci.yml + docs.yml) | 2 (ci.yml + docs.yml) | 1 (ci.yml) | 1 (ci.yml) |
| **Cache Handling** | Complex (passed as input) | Simple (restore by key) | Simple (restore by key) | Simple |
| **Execution Time** | ~25-30 min | ~23-28 min | ~25-30 min | ~20-25 min |
| **Maintainability** | Medium | High | High | Highest |
| **Separation of Concerns** | High | High | Medium | Low |
| **Best Practice Alignment** | Medium | ⭐ High | Medium | Low |
| **Code Changes Required** | - | Minimal | Moderate | Significant |

## Best Practices Analysis

### Current Structure (Separate Workflows) - ACTUALLY GOOD PRACTICE ✅

**Pros:**
- **Separation of Concerns**: Documentation checks are logically separate from code tests
- **Reusability**: docs.yml can be called from multiple workflows (CI, nightly, release)
- **Independent Evolution**: Can modify doc checks without touching main CI
- **Clear Ownership**: Different teams can own different workflow files
- **Selective Triggering**: Can run docs independently if needed

**Cons:**
- More complex dependency graph visualization
- Cache-key passing adds boilerplate
- Nested workflow harder to debug

### The Real Problems (Not the Workflow Split)

After reconsidering best practices, the **actual issues** are:

1. **Prebuild is over-connected** - Jobs depend on it but don't use it
2. **Build has wrong dependencies** - Doesn't need format-check/security
3. **Cache handling is complex** - Every job restores cache independently

## REVISED Recommendation

**Keep the workflow split (docs.yml separate), but fix the real issues:**

### Fix 1: Remove Unnecessary Prebuild Dependencies

```yaml
# BEFORE: Everything depends on prebuild
test:
  needs: [test-quick, prebuild]

# AFTER: Only jobs that actually use cache depend on it
test:
  needs: test-quick  # Remove prebuild dependency
  steps:
    - uses: actions/cache/restore@v4
      with:
        # Restore by key pattern, not by dependency
        key: prebuild-${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('**/requirements*.txt') }}
```

### Fix 2: Simplify Build Dependencies

```yaml
# BEFORE: Build waits for unrelated jobs
build:
  needs: [test-quick, format-check, security]

# AFTER: Build only needs smoke test
build:
  needs: test-quick
```

### Fix 3: Make Documentation Dependency Optional

```yaml
# BEFORE: ci-success requires docs to pass
ci-success:
  needs: [test, security, format-check, build, performance, documentation]

# AFTER: Docs can fail without blocking (if desired)
ci-success:
  needs: [test, security, format-check, build, performance]
  # Documentation runs in parallel but doesn't block merge

documentation:
  needs: test-quick
  # Runs independently, reports separately
```

## Updated Recommendation: Minimal Changes

**Keep workflows separate (best practice), simplify dependencies:**

```
┌─────────────┐
│  prebuild   │ (background, no deps)
└─────────────┘

┌─────────────┐
│ test-quick  │ ← Only this gates everything
└──────┬──────┘
   ┌───┼───┬───┬───┬───┐
   v   v   v   v   v   v
┌────┐┌──┐┌──┐┌──┐┌───┐┌────┐
│test││sc││fm││pf││bld││docs│
└─┬──┘└┬─┘└┬─┘└┬─┘└─┬─┘└─┬──┘
  └────┴───┴───┴───┴────┘
              │
              v
       ┌─────────────┐
       │ ci-success  │
       └─────────────┘
```

**Why this is better:**

1. ✅ **Maintains separation of concerns** (docs.yml separate)
2. ✅ **Follows GitHub Actions best practices** (reusable workflows)
3. ✅ **Simpler graph** (2 levels instead of 4)
4. ✅ **Faster execution** (true parallelism, no waiting for prebuild)
5. ✅ **Easier to maintain** (clear dependencies)
6. ✅ **More flexible** (can run docs independently)

**Quick wins to implement immediately:**

1. **Remove prebuild from job dependencies** - make cache opportunistic
2. **Simplify build dependencies** - only needs test-quick
3. **Keep docs.yml separate** - it's actually good practice
4. **Optional: Make docs non-blocking** - if you want faster merges

## Implementation Priority

### Phase 1: Simplify Dependencies (10 min) ⭐ RECOMMENDED
**Goal**: Clean up the dependency graph without changing workflow structure

**Changes to ci.yml:**
```yaml
# 1. Remove prebuild from all job dependencies except those that actually use it
test:
  needs: test-quick  # Remove: prebuild

security:
  needs: test-quick  # Remove: prebuild (uses cache but can restore by key)

format-check:
  needs: test-quick  # Remove: prebuild

performance:
  needs: test-quick  # Remove: prebuild

build:
  needs: test-quick  # Remove: format-check, security, prebuild

documentation:
  needs: test-quick  # Remove: prebuild
```

**Changes to cache restoration in jobs:**
```yaml
# Instead of depending on prebuild job, restore cache opportunistically
- name: Restore prebuild cache
  uses: actions/cache/restore@v4
  with:
    path: |
      ~/.cache/pip
      FollowWeb/.venv
      FollowWeb/tests/test_data
      .pytest_cache
      .mypy_cache
      .ruff_cache
    key: prebuild-${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('FollowWeb/requirements*.txt') }}
    restore-keys: |
      prebuild-${{ runner.os }}-py${{ matrix.python-version }}-
```

**Result**: 2-level dependency graph, all jobs run in parallel after smoke test

---

### Phase 2: Optional - Make Docs Non-Blocking (5 min)
**Goal**: Allow PRs to merge even if documentation checks fail (if desired)

**Changes to ci.yml:**
```yaml
ci-success:
  needs: [test-quick, test, security, format-check, build, performance]
  # Remove: documentation (let it run independently)

# Documentation still runs but doesn't block merges
documentation:
  needs: test-quick
  continue-on-error: true  # Optional: make entire workflow non-blocking
```

**Trade-off**: Faster merges vs. enforced documentation standards

---

### Phase 3: Optional - Optimize Prebuild (5 min)
**Goal**: Make prebuild truly optional background job

**Changes to ci.yml:**
```yaml
# Remove prebuild outputs section (no longer needed)
prebuild:
  name: Prebuild Environment
  uses: ./.github/workflows/codespaces-prebuild.yml
  # Remove: outputs section

# Prebuild runs in background, no jobs depend on it
# Cache is restored opportunistically by key pattern
```

**Result**: Prebuild becomes pure optimization, doesn't affect graph

---

## Summary of Approaches

| Approach | Graph Levels | Workflow Files | Separation | Complexity | Best For |
|----------|--------------|----------------|------------|------------|----------|
| **Current** | 4 | 2 | High | High | Status quo |
| **Phase 1 Only** | 2 | 2 | High | Low | ⭐ **Recommended** |
| **Phase 1 + 2** | 2 | 2 | High | Low | Fast merges |
| **Option 1 (Flatten)** | 3 | 1 | Medium | Medium | Single workflow preference |
| **Option 3 (Merge)** | 2 | 1 | Low | Lowest | Minimal jobs |

## Fail-Fast vs Parallel Execution Trade-offs

### Resource Efficiency Consideration

You mentioned preferring the **fail-early mentality** to conserve resources. This is a valid concern!

**Current behavior (implicit fail-fast):**
- If test-quick fails, nothing else runs ✅
- If any parallel job fails, others continue running ❌ (wastes resources)

**Phase 1 behavior (full parallel):**
- All jobs run simultaneously after test-quick
- If one fails, others keep running until completion
- **Resource waste**: Could run 6 jobs when first one fails

### Hybrid Option: Staged Gates (⭐ BEST OF BOTH WORLDS)

**Add strategic gates to fail fast while maintaining clean graph:**

```yaml
jobs:
  # Stage 1: Quick validation (1-2 min)
  test-quick:
    # Fast smoke test
  
  # Stage 2: Fast checks (3-5 min) - run in parallel
  format-check:
    needs: test-quick
  
  security:
    needs: test-quick
  
  # Stage 3: Gate - only proceed if fast checks pass
  fast-checks-gate:
    needs: [test-quick, format-check, security]
    runs-on: ubuntu-latest
    steps:
      - run: echo "Fast checks passed, proceeding with expensive jobs"
  
  # Stage 4: Expensive jobs (15-25 min) - only run if Stage 3 passes
  test:
    needs: fast-checks-gate  # Won't run if format/security fail
  
  performance:
    needs: fast-checks-gate
  
  build:
    needs: fast-checks-gate
  
  documentation:
    needs: fast-checks-gate
  
  ci-success:
    needs: [test, performance, build, documentation]
```

**Hybrid Graph:**
```
┌─────────────┐
│ test-quick  │ ← Stage 1: Smoke test (1-2 min)
└──────┬──────┘
    ┌──┴──┐
    v     v
┌──────┐┌────┐
│format││sec │ ← Stage 2: Fast checks (3-5 min, parallel)
└───┬──┘└─┬──┘
    └──┬──┘
       v
  ┌────────┐
  │  gate  │ ← Stage 3: Fail-fast checkpoint
  └────┬───┘
   ┌───┼──┬──┬──┐
   v   v  v  v  v
┌────┐┌──┐┌──┐┌────┐
│test││pf││bl││docs│ ← Stage 4: Expensive (15-25 min)
└─┬──┘└┬─┘└┬─┘└─┬──┘
  └────┴───┴────┘
         │
         v
  ┌─────────────┐
  │ ci-success  │
  └─────────────┘
```

**Resource Savings:**
- ✅ Fails in 3-7 minutes if format/security issues (saves 15-25 min of test/perf/build)
- ✅ Fast feedback on common issues (linting, security)
- ✅ Expensive jobs only run when likely to succeed
- ✅ Still maintains clean 3-level graph

**Comparison:**

| Approach | Levels | Fail Time | Resource Waste | Complexity |
|----------|--------|-----------|----------------|------------|
| **Current** | 4 | Varies | Medium | High |
| **Phase 1 (Full Parallel)** | 2 | 25-30 min | High | Low |
| **Hybrid (Staged Gates)** | 3 | 3-7 min | Low | Medium |

### Updated Recommendation

**Choose based on your priority:**

1. **Hybrid (Staged Gates)** ⭐ - If resource efficiency is important
   - Fails fast on common issues
   - Saves CI minutes
   - Still cleaner than current structure

2. **Phase 1 (Full Parallel)** - If speed is more important than resources
   - Fastest possible feedback
   - Simpler graph
   - May waste resources on failures

3. **Current** - If you want maximum fail-fast
   - Most resource efficient
   - But complex graph and slower overall

## Final Recommendation

**Implement Hybrid (Staged Gates)** - this gives you:
- ✅ Fail-fast on common issues (format, security) - saves resources
- ✅ Clean 3-level dependency graph
- ✅ Maintains workflow separation (best practice)
- ✅ Expensive jobs only run when likely to succeed
- ✅ Minimal code changes
- ✅ Best balance of speed and resource efficiency

**Skip Phase 2** unless you specifically want docs to be non-blocking.

**Skip Phase 3** unless prebuild is causing issues (it's not).
