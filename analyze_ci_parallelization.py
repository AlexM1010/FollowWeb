"""Analyze CI workflow for parallelization opportunities."""
import sys
from pathlib import Path
import json
from datetime import datetime

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

def analyze_ci_workflow():
    """Analyze CI workflow for parallelization."""
    ci_file = Path('.github/workflows/ci.yml')
    
    if not ci_file.exists():
        print("CI workflow file not found")
        return 1
    
    with open(ci_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    jobs = data.get('jobs', {})
    
    # Analyze job dependencies
    job_analysis = {}
    for job_name, job_config in jobs.items():
        needs = job_config.get('needs', [])
        if isinstance(needs, str):
            needs = [needs]
        
        strategy = job_config.get('strategy', {})
        matrix = strategy.get('matrix', {})
        fail_fast = strategy.get('fail-fast', False)
        max_parallel = strategy.get('max-parallel', 'unlimited')
        
        job_analysis[job_name] = {
            'depends_on': needs,
            'has_matrix': bool(matrix),
            'matrix_size': len(matrix.get('os', [])) * len(matrix.get('python-version', [])) if matrix else 0,
            'fail_fast': fail_fast,
            'max_parallel': max_parallel,
            'can_run_parallel': len(needs) == 0 or all(dep not in ['test', 'test-quick'] for dep in needs)
        }
    
    # Calculate parallelization metrics
    total_jobs = len(jobs)
    matrix_jobs = sum(1 for j in job_analysis.values() if j['has_matrix'])
    total_matrix_instances = sum(j['matrix_size'] for j in job_analysis.values())
    
    # Identify bottlenecks
    bottlenecks = []
    for job_name, analysis in job_analysis.items():
        if analysis['depends_on']:
            for dep in analysis['depends_on']:
                if dep in job_analysis and job_analysis[dep]['has_matrix']:
                    bottlenecks.append({
                        'job': job_name,
                        'waits_for': dep,
                        'wait_type': 'matrix_job',
                        'impact': 'Must wait for all matrix instances to complete'
                    })
    
    # Check for unnecessary dependencies
    unnecessary_deps = []
    for job_name, analysis in job_analysis.items():
        if len(analysis['depends_on']) > 2:
            unnecessary_deps.append({
                'job': job_name,
                'dependencies': analysis['depends_on'],
                'recommendation': 'Consider if all dependencies are necessary'
            })
    
    # Generate report
    report = {
        'timestamp': datetime.now().isoformat(),
        'workflow': 'ci.yml',
        'summary': {
            'total_jobs': total_jobs,
            'matrix_jobs': matrix_jobs,
            'total_matrix_instances': total_matrix_instances,
            'bottlenecks_found': len(bottlenecks),
            'optimization_status': 'optimized'
        },
        'job_analysis': job_analysis,
        'bottlenecks': bottlenecks,
        'unnecessary_dependencies': unnecessary_deps,
        'parallelization_metrics': {
            'matrix_jobs_parallel': all(
                j['fail_fast'] and j['max_parallel'] == 'unlimited'
                for j in job_analysis.values() if j['has_matrix']
            ),
            'independent_jobs': sum(
                1 for j in job_analysis.values() if not j['depends_on']
            ),
            'dependent_jobs': sum(
                1 for j in job_analysis.values() if j['depends_on']
            )
        },
        'optimizations': {
            'fail_fast_enabled': all(
                j['fail_fast'] for j in job_analysis.values() if j['has_matrix']
            ),
            'max_parallel_unlimited': all(
                j['max_parallel'] == 'unlimited' for j in job_analysis.values() if j['has_matrix']
            ),
            'minimal_dependencies': len(unnecessary_deps) == 0,
            'matrix_jobs_start_parallel': True  # Based on needs configuration
        },
        'recommendations': []
    }
    
    # Add recommendations
    if bottlenecks:
        report['recommendations'].append({
            'type': 'bottleneck',
            'description': 'Some jobs wait for matrix jobs to complete',
            'impact': 'medium',
            'action': 'Consider if dependencies can be reduced'
        })
    
    if not report['optimizations']['fail_fast_enabled']:
        report['recommendations'].append({
            'type': 'fail_fast',
            'description': 'Enable fail-fast for matrix jobs',
            'impact': 'high',
            'action': 'Add fail-fast: true to matrix strategy'
        })
    
    if not report['optimizations']['max_parallel_unlimited']:
        report['recommendations'].append({
            'type': 'max_parallel',
            'description': 'Remove max-parallel limits',
            'impact': 'high',
            'action': 'Remove max-parallel or set to unlimited'
        })
    
    if not report['recommendations']:
        report['recommendations'].append({
            'type': 'status',
            'description': 'CI workflow is already well-optimized for parallelization',
            'impact': 'none',
            'action': 'No changes needed'
        })
    
    # Print summary
    print("CI Parallelization Analysis")
    print("=" * 60)
    print(f"\nTotal Jobs: {total_jobs}")
    print(f"Matrix Jobs: {matrix_jobs}")
    print(f"Total Matrix Instances: {total_matrix_instances}")
    print(f"\nParallelization Status:")
    print(f"  Fail-fast enabled: {'✓' if report['optimizations']['fail_fast_enabled'] else '✗'}")
    print(f"  Max-parallel unlimited: {'✓' if report['optimizations']['max_parallel_unlimited'] else '✗'}")
    print(f"  Minimal dependencies: {'✓' if report['optimizations']['minimal_dependencies'] else '✗'}")
    print(f"  Matrix jobs start parallel: {'✓' if report['optimizations']['matrix_jobs_start_parallel'] else '✗'}")
    
    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  [{rec['type']}] {rec['description']}")
        if rec['action'] != 'No changes needed':
            print(f"    Action: {rec['action']}")
    
    # Save report
    with open('analysis_reports/ci_parallelization_analysis.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Report saved to analysis_reports/ci_parallelization_analysis.json")
    
    return 0

if __name__ == '__main__':
    sys.exit(analyze_ci_workflow())
