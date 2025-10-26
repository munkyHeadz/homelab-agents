"""Incident Memory System - Learn from past incidents using Qdrant vector database."""

import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings


class IncidentMemory:
    """
    Store and retrieve incident history using Qdrant vector database.

    This enables agents to:
    - Learn from past incidents
    - Retrieve similar historical incidents
    - Improve diagnosis accuracy over time
    - Track resolution success rates
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        """Initialize connection to Qdrant and embeddings model."""
        self.client = QdrantClient(url=qdrant_url)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.collection_name = "agent_memory"
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the agent_memory collection exists."""
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # text-embedding-3-small dimension
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"Warning: Could not ensure collection: {e}")

    def store_incident(
        self,
        alert_name: str,
        description: str,
        severity: str,
        affected_systems: List[str],
        root_cause: str,
        remediation_taken: str,
        resolution_status: str,
        resolution_time_seconds: int,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store an incident in memory for future learning.

        Returns the incident ID.
        """
        incident_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Create searchable text representation
        incident_text = f"""
        Alert: {alert_name}
        Description: {description}
        Severity: {severity}
        Affected Systems: {', '.join(affected_systems)}
        Root Cause: {root_cause}
        Remediation: {remediation_taken}
        Status: {resolution_status}
        """

        # Generate embedding for semantic search
        try:
            embedding = self.embeddings.embed_query(incident_text)
        except Exception as e:
            print(f"Warning: Failed to generate embedding: {e}")
            # Use zero vector as fallback
            embedding = [0.0] * 1536

        # Prepare payload with all incident data
        payload = {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "alert_name": alert_name,
            "description": description,
            "severity": severity,
            "affected_systems": affected_systems,
            "root_cause": root_cause,
            "remediation_taken": remediation_taken,
            "resolution_status": resolution_status,
            "resolution_time_seconds": resolution_time_seconds,
            "metadata": metadata or {}
        }

        # Store in Qdrant
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=incident_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            print(f"✓ Stored incident {incident_id} in memory")
        except Exception as e:
            print(f"✗ Failed to store incident: {e}")

        return incident_id

    def find_similar_incidents(
        self,
        query_text: str,
        limit: int = 5,
        severity_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Find similar past incidents using semantic search.

        Args:
            query_text: Description of current incident
            limit: Maximum number of similar incidents to return
            severity_filter: Only return incidents of this severity

        Returns:
            List of similar incidents with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query_text)

            # Build filter if severity specified
            search_filter = None
            if severity_filter:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="severity",
                            match=MatchValue(value=severity_filter)
                        )
                    ]
                )

            # Search for similar incidents
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter
            )

            # Format results
            similar_incidents = []
            for result in results:
                incident = {
                    "score": result.score,
                    "incident_id": result.payload["incident_id"],
                    "timestamp": result.payload["timestamp"],
                    "alert_name": result.payload["alert_name"],
                    "description": result.payload["description"],
                    "root_cause": result.payload["root_cause"],
                    "remediation_taken": result.payload["remediation_taken"],
                    "resolution_status": result.payload["resolution_status"],
                    "resolution_time": result.payload["resolution_time_seconds"]
                }
                similar_incidents.append(incident)

            return similar_incidents

        except Exception as e:
            print(f"✗ Failed to search incidents: {e}")
            return []

    def get_incident_stats(self) -> Dict:
        """Get statistics about stored incidents."""
        try:
            collection_info = self.client.get_collection(self.collection_name)

            # Get all incidents to calculate stats
            all_incidents = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000  # Adjust if you have more incidents
            )[0]

            if not all_incidents:
                return {
                    "total_incidents": 0,
                    "avg_resolution_time": 0,
                    "success_rate": 0,
                    "by_severity": {}
                }

            total = len(all_incidents)
            successful = sum(1 for i in all_incidents
                           if i.payload.get("resolution_status") == "resolved")
            avg_time = sum(i.payload.get("resolution_time_seconds", 0)
                          for i in all_incidents) / total if total > 0 else 0

            # Count by severity
            by_severity = {}
            for incident in all_incidents:
                sev = incident.payload.get("severity", "unknown")
                by_severity[sev] = by_severity.get(sev, 0) + 1

            return {
                "total_incidents": total,
                "avg_resolution_time": int(avg_time),
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "by_severity": by_severity
            }

        except Exception as e:
            print(f"✗ Failed to get stats: {e}")
            return {}

    def format_historical_context(self, similar_incidents: List[Dict]) -> str:
        """
        Format similar incidents as context for agents.

        Returns markdown-formatted historical context.
        """
        if not similar_incidents:
            return "No similar historical incidents found."

        context = "## Historical Context\n\n"
        context += f"Found {len(similar_incidents)} similar past incidents:\n\n"

        for i, incident in enumerate(similar_incidents, 1):
            context += f"### {i}. {incident['alert_name']} (Similarity: {incident['score']:.0%})\n"
            context += f"- **Timestamp:** {incident['timestamp']}\n"
            context += f"- **Root Cause:** {incident['root_cause']}\n"
            context += f"- **Resolution:** {incident['remediation_taken']}\n"
            context += f"- **Status:** {incident['resolution_status']}\n"
            context += f"- **Resolution Time:** {incident['resolution_time']}s\n\n"

        return context
