#!/usr/bin/env python3
"""
Homelab AI Agent Server

This server receives alerts from Alertmanager and dispatches them to CrewAI agents
for autonomous diagnosis and remediation. It also runs scheduled proactive health checks.
"""

import os
import logging
import threading
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from crews.infrastructure_health import handle_alert, scheduled_health_check, incident_memory

# Load environment variables
load_dotenv()  # Will automatically look for .env in current directory

# Configure logging
log_handlers = [logging.StreamHandler()]
log_file = os.getenv('LOG_FILE', '/tmp/agent_server.log')
try:
    log_handlers.append(logging.FileHandler(log_file))
except Exception:
    pass  # If file logging fails, just use stdout

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize scheduler for proactive checks
scheduler = BackgroundScheduler()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    memory_status = 'connected' if incident_memory else 'disconnected'
    memory_incidents = 0
    if incident_memory:
        try:
            stats = incident_memory.get_incident_stats()
            memory_incidents = stats['total_incidents']
        except Exception:
            memory_status = 'error'

    return jsonify({
        'status': 'healthy',
        'service': 'homelab-ai-agents',
        'version': '1.1.0',
        'memory': {
            'status': memory_status,
            'incidents': memory_incidents
        }
    }), 200


@app.route('/alert', methods=['POST'])
def receive_alert():
    """
    Receive alert from Alertmanager and dispatch to CrewAI agents.

    Alertmanager sends alerts in this format:
    {
        "alerts": [
            {
                "labels": {"alertname": "...", ...},
                "annotations": {"description": "...", ...},
                "status": "firing|resolved"
            }
        ]
    }
    """
    try:
        alert_data = request.json
        logger.info(f"Received alert: {alert_data}")

        # Only process firing alerts (ignore resolved alerts)
        alerts = alert_data.get('alerts', [])
        firing_alerts = [a for a in alerts if a.get('status') == 'firing']

        if not firing_alerts:
            logger.info("No firing alerts, skipping")
            return jsonify({'status': 'no_action', 'message': 'No firing alerts'}), 200

        # Process alerts in background thread to avoid blocking HTTP response
        def process_alert():
            try:
                result = handle_alert(alert_data)
                logger.info(f"Alert processing complete: {result}")
            except Exception as e:
                logger.error(f"Error processing alert: {e}", exc_info=True)

        thread = threading.Thread(target=process_alert)
        thread.daemon = True
        thread.start()

        return jsonify({
            'status': 'accepted',
            'message': 'Alert dispatched to AI agents'
        }), 202

    except Exception as e:
        logger.error(f"Error receiving alert: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/trigger-health-check', methods=['POST'])
def trigger_health_check():
    """Manually trigger a proactive health check."""
    try:
        logger.info("Manual health check triggered")

        def run_check():
            try:
                result = scheduled_health_check()
                logger.info(f"Manual health check complete: {result}")
            except Exception as e:
                logger.error(f"Error in manual health check: {e}", exc_info=True)

        thread = threading.Thread(target=run_check)
        thread.daemon = True
        thread.start()

        return jsonify({
            'status': 'accepted',
            'message': 'Health check started'
        }), 202

    except Exception as e:
        logger.error(f"Error triggering health check: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get incident memory statistics."""
    try:
        if not incident_memory:
            return jsonify({
                'status': 'error',
                'message': 'Incident memory not initialized'
            }), 503

        stats = incident_memory.get_incident_stats()
        return jsonify({
            'status': 'success',
            'memory': stats,
            'service': 'homelab-ai-agents',
            'version': '1.1.0'
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving stats: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/incidents', methods=['GET'])
def get_recent_incidents():
    """Get recent incidents with optional limit."""
    try:
        if not incident_memory:
            return jsonify({
                'status': 'error',
                'message': 'Incident memory not initialized'
            }), 503

        limit = request.args.get('limit', 10, type=int)

        # Query all incidents from Qdrant
        similar = incident_memory.find_similar_incidents(
            query_text="",  # Empty query returns all by default
            limit=limit
        )

        return jsonify({
            'status': 'success',
            'count': len(similar),
            'incidents': similar
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving incidents: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    try:
        metrics_lines = [
            "# HELP ai_agents_incidents_total Total number of incidents stored",
            "# TYPE ai_agents_incidents_total gauge",
        ]

        if incident_memory:
            stats = incident_memory.get_incident_stats()
            # Handle case where stats may be empty dict if Qdrant errors occur
            total_incidents = stats.get('total_incidents', 0)
            success_rate = stats.get('success_rate', 0)
            avg_resolution_time = stats.get('avg_resolution_time', 0)
            by_severity = stats.get('by_severity', {})

            metrics_lines.append(f"ai_agents_incidents_total {total_incidents}")

            metrics_lines.append("# HELP ai_agents_success_rate Incident resolution success rate")
            metrics_lines.append("# TYPE ai_agents_success_rate gauge")
            metrics_lines.append(f"ai_agents_success_rate {success_rate / 100}")

            metrics_lines.append("# HELP ai_agents_avg_resolution_seconds Average incident resolution time in seconds")
            metrics_lines.append("# TYPE ai_agents_avg_resolution_seconds gauge")
            metrics_lines.append(f"ai_agents_avg_resolution_seconds {avg_resolution_time}")

            # Per-severity metrics
            metrics_lines.append("# HELP ai_agents_incidents_by_severity Number of incidents by severity")
            metrics_lines.append("# TYPE ai_agents_incidents_by_severity gauge")
            for severity, count in by_severity.items():
                metrics_lines.append(f'ai_agents_incidents_by_severity{{severity="{severity}"}} {count}')

        metrics_lines.append("")  # Prometheus expects trailing newline

        return "\n".join(metrics_lines), 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        return f"# Error: {str(e)}\n", 500, {'Content-Type': 'text/plain; charset=utf-8'}


def run_scheduled_health_check():
    """Wrapper for scheduled health checks with error handling."""
    try:
        logger.info("Starting scheduled health check")
        result = scheduled_health_check()
        logger.info(f"Scheduled health check complete: {result}")
    except Exception as e:
        logger.error(f"Error in scheduled health check: {e}", exc_info=True)


if __name__ == '__main__':
    # Schedule proactive health checks every 5 minutes
    scheduler.add_job(
        run_scheduled_health_check,
        'interval',
        minutes=5,
        id='health_check',
        name='Proactive Health Check',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started - proactive health checks every 5 minutes")

    # Start Flask server
    logger.info("Starting agent server on 0.0.0.0:5000")
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down agent server")
        scheduler.shutdown()
