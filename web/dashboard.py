"""
Web Dashboard for Homelab Agent System

Provides a real-time web interface for monitoring:
- System health status
- Active issues and resolutions
- Predictive analysis
- Service health
- Backup status
- Resource metrics
- Alert history
"""

import asyncio
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Store references to agents (will be set when dashboard starts)
health_agent = None
backup_agent = None
service_health_agent = None
predictive_agent = None
infrastructure_agent = None


def set_agents(health, backup, service, predictive, infrastructure):
    """Set agent references"""
    global health_agent, backup_agent, service_health_agent, predictive_agent, infrastructure_agent
    health_agent = health
    backup_agent = backup
    service_health_agent = service
    predictive_agent = predictive
    infrastructure_agent = infrastructure


@app.route('/')
def index():
    """Render main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
async def api_status():
    """Get overall system status"""
    try:
        status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "uptime": 0,
            "active_issues": 0,
            "resolved_today": 0,
            "services_up": 0,
            "services_total": 0
        }

        # Get health agent data
        if health_agent:
            health_data = await health_agent.generate_health_report()
            status["active_issues"] = health_data.get("active_issues", 0)
            status["resolved_today"] = health_data.get("resolved_today", 0)

            # Overall status based on active issues
            if status["active_issues"] > 0:
                critical = sum(1 for i in health_agent.active_issues
                             if i.severity.value == "critical")
                if critical > 0:
                    status["status"] = "critical"
                else:
                    status["status"] = "warning"

        # Get service health data
        if service_health_agent:
            services = await service_health_agent.check_all_services()
            status["services_total"] = len(services)
            status["services_up"] = sum(1 for s in services.values()
                                       if s.status.value == "healthy")

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health')
async def api_health():
    """Get detailed health information"""
    try:
        if not health_agent:
            return jsonify({"error": "Health agent not available"}), 503

        health_data = await health_agent.generate_health_report()

        # Format active issues
        active_issues = []
        for issue in health_agent.active_issues:
            active_issues.append({
                "component": issue.component,
                "type": issue.issue_type,
                "severity": issue.severity.value,
                "description": issue.description,
                "detected_at": issue.detected_at.isoformat() if issue.detected_at else None,
                "risk_level": issue.risk_level.value if issue.risk_level else None
            })

        # Format resolved issues (last 10)
        resolved_issues = []
        for issue in health_agent.resolved_issues[-10:]:
            resolved_issues.append({
                "component": issue.component,
                "type": issue.issue_type,
                "description": issue.description,
                "detected_at": issue.detected_at.isoformat() if issue.detected_at else None,
                "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
                "resolution": issue.resolution
            })

        return jsonify({
            "active_issues": active_issues,
            "resolved_issues": resolved_issues,
            "summary": health_data
        })

    except Exception as e:
        logger.error(f"Error getting health: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/predictions')
async def api_predictions():
    """Get predictive analysis data"""
    try:
        if not predictive_agent:
            return jsonify({"error": "Predictive agent not available"}), 503

        predictions = await predictive_agent.analyze_all_components()

        # Format predictions
        pred_list = []
        for pred in predictions:
            pred_list.append({
                "type": pred.prediction_type.value,
                "component": pred.component,
                "predicted_time": pred.predicted_time.isoformat(),
                "confidence": pred.confidence.value,
                "severity": pred.severity.value,
                "description": pred.description,
                "recommendation": pred.recommendation,
                "created_at": pred.created_at.isoformat()
            })

        return jsonify({"predictions": pred_list})

    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/services')
async def api_services():
    """Get service health data"""
    try:
        if not service_health_agent:
            return jsonify({"error": "Service health agent not available"}), 503

        services = await service_health_agent.check_all_services()

        # Format services
        service_list = []
        for service_id, health in services.items():
            service_list.append({
                "id": service_id,
                "name": health.service_name,
                "type": health.service_type.value,
                "status": health.status.value,
                "response_time": health.response_time,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "error_message": health.error_message,
                "metrics": health.metrics or {}
            })

        return jsonify({"services": service_list})

    except Exception as e:
        logger.error(f"Error getting services: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/backups')
async def api_backups():
    """Get backup verification data"""
    try:
        if not backup_agent:
            return jsonify({"error": "Backup agent not available"}), 503

        results = await backup_agent.verify_all_backups()

        # Get detailed backup info
        backups = []
        for vm_id, backup_info in backup_agent.verification_results.items():
            backups.append({
                "vm_id": backup_info.vm_id,
                "vm_name": backup_info.vm_name,
                "backup_time": backup_info.backup_time.isoformat(),
                "backup_size": backup_info.backup_size,
                "status": backup_info.status.value,
                "verification_level": backup_info.verification_level.value if backup_info.verification_level else None,
                "restore_test_passed": backup_info.restore_test_passed
            })

        return jsonify({
            "summary": results,
            "backups": backups
        })

    except Exception as e:
        logger.error(f"Error getting backups: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/infrastructure')
async def api_infrastructure():
    """Get infrastructure metrics"""
    try:
        if not infrastructure_agent:
            return jsonify({"error": "Infrastructure agent not available"}), 503

        # Get node status
        node_result = await infrastructure_agent.execute("Show node status")

        # Get VM/Container stats
        vms_result = await infrastructure_agent.execute("List all VMs and containers")

        # Get Docker stats
        docker_result = await infrastructure_agent.execute("Show Docker system info")

        return jsonify({
            "node": node_result,
            "vms": vms_result,
            "docker": docker_result
        })

    except Exception as e:
        logger.error(f"Error getting infrastructure: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/metrics/history')
async def api_metrics_history():
    """Get historical metrics for charting"""
    try:
        if not predictive_agent:
            return jsonify({"error": "Predictive agent not available"}), 503

        component = request.args.get('component', 'proxmox_node')
        metric = request.args.get('metric', 'cpu_usage')
        limit = int(request.args.get('limit', '50'))

        key = f"{component}.{metric}"
        data = predictive_agent.metric_history.get(key, [])

        # Get last N data points
        recent_data = data[-limit:] if len(data) > limit else data

        # Format for charting
        timestamps = [ts.isoformat() for ts, _ in recent_data]
        values = [val for _, val in recent_data]

        return jsonify({
            "component": component,
            "metric": metric,
            "timestamps": timestamps,
            "values": values
        })

    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/trends')
async def api_trends():
    """Get trend analysis for multiple metrics"""
    try:
        if not predictive_agent:
            return jsonify({"error": "Predictive agent not available"}), 503

        components = ["proxmox_node", "docker_daemon"]
        metrics = ["cpu_usage", "memory_usage", "disk_usage"]

        trends = []
        for component in components:
            for metric in metrics:
                trend = predictive_agent.calculate_trend(component, metric)
                if trend:
                    trends.append({
                        "component": component,
                        "metric": metric,
                        "direction": trend.direction,
                        "slope": trend.slope,
                        "volatility": trend.volatility,
                        "current_value": trend.values[-1] if trend.values else None
                    })

        return jsonify({"trends": trends})

    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        return jsonify({"error": str(e)}), 500


def run_dashboard(host='0.0.0.0', port=5000):
    """
    Run the dashboard web server

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    logger.info(f"Starting dashboard web server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run_dashboard()
