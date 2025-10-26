#!/usr/bin/env python3
"""Test script for crew + incident memory integration."""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, '/home/munky/homelab-agents')

# Load environment
load_dotenv('/home/munky/homelab-agents/.env')

from crews.infrastructure_health.crew import handle_alert
from crews.memory.incident_memory import IncidentMemory

def test_crew_with_memory():
    """Test the crew with incident memory integration."""

    print("=" * 70)
    print("Testing Crew + Incident Memory Integration")
    print("=" * 70)

    # Initialize memory to check initial state
    print("\n1. Checking initial memory state...")
    try:
        memory = IncidentMemory(qdrant_url="http://localhost:6333")
        stats = memory.get_incident_stats()
        print(f"✓ Current memory state:")
        print(f"   Total incidents: {stats['total_incidents']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   By severity: {stats['by_severity']}")
    except Exception as e:
        print(f"✗ Failed to check memory: {e}")
        return False

    # Simulate a test alert (similar to previous incidents in memory)
    print("\n2. Sending test alert to crew...")
    test_alert = {
        'alerts': [{
            'labels': {
                'alertname': 'TraefikHealthCheckFailed',
                'severity': 'critical'
            },
            'annotations': {
                'description': 'Traefik reverse proxy health check is failing'
            },
            'status': 'firing'
        }]
    }

    print(f"   Alert: TraefikHealthCheckFailed")
    print(f"   Severity: critical")
    print(f"   Description: Traefik reverse proxy health check is failing")

    # This should:
    # 1. Find similar past incidents (TraefikDown from test_incident_memory.py)
    # 2. Provide historical context to Analyst
    # 3. Execute crew workflow
    # 4. Store new incident in memory

    print("\n3. Running crew workflow with memory integration...")
    print("   (This will take 30-90 seconds...)\n")

    try:
        result = handle_alert(test_alert)
        print("\n✓ Crew workflow completed!")
        print(f"   Result preview: {str(result)[:200]}...")
    except Exception as e:
        print(f"\n✗ Crew workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Check memory after incident
    print("\n4. Checking memory after incident...")
    try:
        stats = memory.get_incident_stats()
        print(f"✓ Updated memory state:")
        print(f"   Total incidents: {stats['total_incidents']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   Avg resolution time: {stats['avg_resolution_time']}s")
        print(f"   By severity: {stats['by_severity']}")
    except Exception as e:
        print(f"✗ Failed to check updated memory: {e}")

    # Verify similar incident retrieval
    print("\n5. Verifying similar incident retrieval...")
    try:
        similar = memory.find_similar_incidents(
            query_text="Traefik proxy health check failing",
            limit=3,
            severity_filter="critical"
        )
        print(f"✓ Found {len(similar)} similar incidents:")
        for i, incident in enumerate(similar[:3], 1):
            print(f"   {i}. {incident['alert_name']} "
                  f"(similarity: {incident['score']:.1%}, "
                  f"resolved in {incident['resolution_time']}s)")
    except Exception as e:
        print(f"✗ Similar incident retrieval failed: {e}")

    print("\n" + "=" * 70)
    print("Crew + Memory Integration Test Complete!")
    print("=" * 70)
    print("\nKey Observations:")
    print("- Crew should have retrieved similar TraefikDown incidents")
    print("- Historical context should have been provided to Analyst")
    print("- New incident should have been stored in memory")
    print("- Statistics should show updated counts")

    return True

if __name__ == "__main__":
    print("\n⚠️  NOTE: This test will execute a full crew workflow")
    print("   It requires all services to be running:")
    print("   - Qdrant vector database (localhost:6333)")
    print("   - OpenAI API access")
    print("   - Prometheus (for tools)")
    print()

    success = test_crew_with_memory()
    sys.exit(0 if success else 1)
