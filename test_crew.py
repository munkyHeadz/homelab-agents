#!/usr/bin/env python3
"""
Test script to verify the Infrastructure Health Crew works correctly.

This simulates an alert being received and tests the full workflow:
Monitor -> Analyst -> Healer -> Communicator
"""

import sys
from dotenv import load_dotenv
from crews.infrastructure_health import handle_alert

# Load environment variables
load_dotenv('/home/munky/homelab-agents/.env')

# Simulated alert from Alertmanager
test_alert = {
    'alerts': [{
        'status': 'firing',
        'labels': {
            'alertname': 'ContainerDown',
            'container': 'test',
            'severity': 'warning'
        },
        'annotations': {
            'description': 'Container test has been down for 5 minutes',
            'summary': 'Test alert for crew validation'
        }
    }]
}

if __name__ == '__main__':
    print("=" * 80)
    print("TESTING INFRASTRUCTURE HEALTH CREW")
    print("=" * 80)
    print("\nSimulating Alertmanager webhook with test alert...")
    print(f"Alert: {test_alert['alerts'][0]['labels']['alertname']}")
    print(f"Description: {test_alert['alerts'][0]['annotations']['description']}")
    print("\nStarting crew execution...\n")
    print("=" * 80)

    try:
        result = handle_alert(test_alert)
        print("\n" + "=" * 80)
        print("CREW EXECUTION COMPLETED")
        print("=" * 80)
        print(f"\nResult:\n{result}")
        print("\n✓ Test completed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
