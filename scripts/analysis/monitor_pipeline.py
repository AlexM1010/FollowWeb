#!/usr/bin/env python3
"""
Monitor GitHub Actions CI pipeline and report status.
"""
import subprocess
import time
import json
from datetime import datetime

def get_latest_run():
    """Get the latest CI run status."""
    result = subprocess.run(
        ["gh", "run", "list", "--workflow=ci.yml", "--limit", "1", "--json", 
         "databaseId,status,conclusion,createdAt,headBranch"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        runs = json.loads(result.stdout)
        return runs[0] if runs else None
    return None

def monitor_pipeline(check_interval=30, timeout_minutes=30):
    """Monitor the pipeline until completion or timeout."""
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    print(f"🔍 Monitoring CI pipeline (timeout: {timeout_minutes} minutes)")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}\n")
    
    last_status = None
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"\n⏱️  Timeout reached ({timeout_minutes} minutes)")
            break
            
        run = get_latest_run()
        if not run:
            print("❌ No CI runs found")
            break
            
        status = run['status']
        conclusion = run['conclusion']
        run_id = run['databaseId']
        
        if status != last_status:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] Status: {status} | Run ID: {run_id}")
            last_status = status
        
        if status == 'completed':
            print(f"\n✅ Pipeline completed with conclusion: {conclusion}")
            print(f"🔗 View run: https://github.com/AlexM1010/FollowWeb/actions/runs/{run_id}")
            
            if conclusion == 'success':
                print("🎉 All checks passed!")
                return True
            else:
                print(f"❌ Pipeline failed with conclusion: {conclusion}")
                # Get failed jobs
                result = subprocess.run(
                    ["gh", "run", "view", str(run_id), "--json", "jobs"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    failed_jobs = [j['name'] for j in data.get('jobs', []) 
                                 if j.get('conclusion') == 'failure']
                    if failed_jobs:
                        print(f"\n📋 Failed jobs:")
                        for job in failed_jobs:
                            print(f"   - {job}")
                return False
        
        time.sleep(check_interval)
    
    return False

if __name__ == "__main__":
    success = monitor_pipeline(check_interval=20, timeout_minutes=30)
    exit(0 if success else 1)
