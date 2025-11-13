"""Analyze workflow schedules for conflicts."""
import sys
from pathlib import Path
import json
from datetime import datetime

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

def parse_cron(cron_str):
    """Parse cron expression to human-readable format."""
    parts = cron_str.split()
    if len(parts) != 5:
        return None
    
    minute, hour, day, month, weekday = parts
    
    # Convert to readable format
    time_str = f"{hour.zfill(2) if hour != '*' else 'XX'}:{minute.zfill(2) if minute != '*' else 'XX'}"
    
    # Day of week
    days = {
        '0': 'Sunday',
        '1': 'Monday',
        '2': 'Tuesday',
        '3': 'Wednesday',
        '4': 'Thursday',
        '5': 'Friday',
        '6': 'Saturday',
        '*': 'Daily'
    }
    
    if '-' in weekday:
        start, end = weekday.split('-')
        day_str = f"{days.get(start, start)}-{days.get(end, end)}"
    else:
        day_str = days.get(weekday, weekday)
    
    return {
        'time': time_str,
        'day': day_str,
        'cron': cron_str
    }

def analyze_schedules():
    """Analyze all workflow schedules."""
    workflows_dir = Path('.github/workflows')
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    schedules = []
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                continue
            
            # Check for schedule trigger
            # Note: 'on' is a reserved word in YAML, so it's stored as True (boolean)
            on_config = data.get(True, data.get('on', {}))
            if on_config and 'schedule' in on_config:
                schedule_list = on_config['schedule']
                if isinstance(schedule_list, list):
                    for schedule in schedule_list:
                        if isinstance(schedule, dict):
                            cron = schedule.get('cron')
                            if cron:
                                parsed = parse_cron(cron)
                                if parsed:
                                    schedules.append({
                                        'workflow': workflow_file.name,
                                        'name': data.get('name', workflow_file.stem),
                                        **parsed
                                    })
        except Exception as e:
            print(f"Error processing {workflow_file.name}: {e}")
    
    # Sort by time
    schedules.sort(key=lambda x: x['time'])
    
    # Detect conflicts (same time)
    conflicts = []
    for i, sched1 in enumerate(schedules):
        for sched2 in schedules[i+1:]:
            if sched1['time'] == sched2['time']:
                # Check if they run on same days
                if sched1['day'] == sched2['day'] or sched1['day'] == 'Daily' or sched2['day'] == 'Daily':
                    conflicts.append({
                        'time': sched1['time'],
                        'workflows': [sched1['name'], sched2['name']],
                        'days': [sched1['day'], sched2['day']]
                    })
    
    # Generate report
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_scheduled_workflows': len(schedules),
        'schedules': schedules,
        'conflicts': conflicts,
        'analysis': {
            'has_conflicts': len(conflicts) > 0,
            'conflict_count': len(conflicts),
            'recommendation': 'Stagger workflows by at least 15 minutes' if conflicts else 'No conflicts detected'
        }
    }
    
    # Print summary
    print(f"Workflow Schedule Analysis")
    print(f"=" * 60)
    print(f"\nScheduled Workflows: {len(schedules)}")
    print(f"\nSchedule Details:")
    for sched in schedules:
        print(f"  {sched['time']} UTC - {sched['day']}: {sched['name']}")
    
    if conflicts:
        print(f"\n⚠️  Conflicts Detected: {len(conflicts)}")
        for conflict in conflicts:
            print(f"  {conflict['time']} UTC: {', '.join(conflict['workflows'])}")
    else:
        print(f"\n✓ No schedule conflicts detected")
    
    # Save report
    with open('analysis_reports/workflow_schedule_analysis.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Report saved to analysis_reports/workflow_schedule_analysis.json")
    
    return 0

if __name__ == '__main__':
    sys.exit(analyze_schedules())
