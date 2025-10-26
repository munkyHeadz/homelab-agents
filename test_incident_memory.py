#!/usr/bin/env python3
"""Test script for incident memory system."""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, '/home/munky/homelab-agents')

# Load environment
load_dotenv('/home/munky/homelab-agents/.env')

from crews.memory.incident_memory import IncidentMemory

def test_incident_memory():
    """Test the incident memory system."""

    print("=" * 60)
    print("Testing Incident Memory System")
    print("=" * 60)

    # Initialize memory
    print("\n1. Initializing incident memory...")
    try:
        memory = IncidentMemory(qdrant_url="http://localhost:6333")
        print("✓ Memory system initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False

    # Store test incidents
    print("\n2. Storing test incidents...")

    test_incidents = [
        {
            "alert_name": "TraefikDown",
            "description": "Traefik reverse proxy is not responding",
            "severity": "critical",
            "affected_systems": ["traefik", "web-gateway"],
            "root_cause": "Container crashed due to memory limit",
            "remediation_taken": "Restarted Traefik container",
            "resolution_status": "resolved",
            "resolution_time_seconds": 45
        },
        {
            "alert_name": "HighMemoryUsage",
            "description": "Container memory usage above 90%",
            "severity": "warning",
            "affected_systems": ["traefik"],
            "root_cause": "Memory leak in application",
            "remediation_taken": "Restarted container and increased memory limit",
            "resolution_status": "resolved",
            "resolution_time_seconds": 120
        },
        {
            "alert_name": "ContainerDown",
            "description": "Docker container unexpectedly stopped",
            "severity": "critical",
            "affected_systems": ["nginx"],
            "root_cause": "Configuration error in nginx.conf",
            "remediation_taken": "Fixed configuration and restarted container",
            "resolution_status": "resolved",
            "resolution_time_seconds": 300
        }
    ]

    incident_ids = []
    for incident in test_incidents:
        try:
            incident_id = memory.store_incident(**incident)
            incident_ids.append(incident_id)
            print(f"✓ Stored incident: {incident['alert_name']} ({incident_id})")
        except Exception as e:
            print(f"✗ Failed to store {incident['alert_name']}: {e}")

    # Test similarity search
    print("\n3. Testing similarity search...")

    queries = [
        ("Traefik proxy is down and not responding", "critical"),
        ("Container using too much memory", "warning"),
    ]

    for query_text, severity in queries:
        print(f"\n   Query: '{query_text}' (severity: {severity})")
        try:
            similar = memory.find_similar_incidents(
                query_text=query_text,
                limit=3,
                severity_filter=severity
            )
            print(f"   Found {len(similar)} similar incidents:")
            for i, incident in enumerate(similar, 1):
                print(f"   {i}. {incident['alert_name']} "
                      f"(similarity: {incident['score']:.1%}, "
                      f"resolved in {incident['resolution_time']}s)")
        except Exception as e:
            print(f"   ✗ Search failed: {e}")

    # Test historical context formatting
    print("\n4. Testing historical context formatting...")
    try:
        similar = memory.find_similar_incidents(
            query_text="Traefik proxy crashed",
            limit=2
        )
        context = memory.format_historical_context(similar)
        print("✓ Historical context generated:")
        print(context[:300] + "..." if len(context) > 300 else context)
    except Exception as e:
        print(f"✗ Context formatting failed: {e}")

    # Get statistics
    print("\n5. Getting incident statistics...")
    try:
        stats = memory.get_incident_stats()
        print(f"✓ Statistics retrieved:")
        print(f"   Total incidents: {stats['total_incidents']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   Avg resolution time: {stats['avg_resolution_time']}s")
        print(f"   By severity: {stats['by_severity']}")
    except Exception as e:
        print(f"✗ Stats retrieval failed: {e}")

    print("\n" + "=" * 60)
    print("Incident Memory Test Complete!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = test_incident_memory()
    sys.exit(0 if success else 1)
