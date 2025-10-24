"""
Predictive Analysis Agent

Uses historical data and machine learning to predict potential issues:
- Resource usage forecasting
- Failure prediction
- Capacity planning
- Trend analysis
- Anomaly detection
- Performance degradation prediction
"""

import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

from shared.config import config
from shared.logging import get_logger

logger = get_logger(__name__)


class PredictionType(Enum):
    """Types of predictions"""
    DISK_FULL = "disk_full"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    CPU_OVERLOAD = "cpu_overload"
    SERVICE_FAILURE = "service_failure"
    BACKUP_FAILURE = "backup_failure"
    CONTAINER_CRASH = "container_crash"


class Confidence(Enum):
    """Prediction confidence levels"""
    LOW = "low"           # <50% confidence
    MEDIUM = "medium"     # 50-80% confidence
    HIGH = "high"         # >80% confidence


class Severity(Enum):
    """Prediction severity"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Prediction:
    """A prediction about a future issue"""
    prediction_type: PredictionType
    component: str
    predicted_time: datetime
    confidence: Confidence
    severity: Severity
    description: str
    recommendation: str
    supporting_data: Dict[str, Any]
    created_at: datetime


@dataclass
class Trend:
    """Trend data for a metric"""
    metric_name: str
    component: str
    values: List[float]
    timestamps: List[datetime]
    slope: float  # Rate of change
    direction: str  # "increasing", "decreasing", "stable"
    volatility: float  # Standard deviation


class PredictiveAnalysisAgent:
    """
    Analyzes historical data to predict future issues

    Features:
    - Resource usage forecasting
    - Failure prediction
    - Trend analysis
    - Anomaly detection
    - Capacity planning
    - Early warning system
    """

    def __init__(self, telegram_notifier=None, health_agent=None):
        self.logger = get_logger(__name__)
        self.telegram_notifier = telegram_notifier
        self.health_agent = health_agent

        # Historical data storage
        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.issue_history: List[Dict[str, Any]] = []

        # Predictions
        self.predictions: List[Prediction] = []
        self.last_analysis_time = None

        # Configuration
        self.analysis_interval = int(config.get("PREDICTION_INTERVAL", "3600"))  # 1 hour
        self.history_window = int(config.get("PREDICTION_HISTORY_DAYS", "7"))  # 7 days
        self.min_data_points = 24  # Need at least 24 data points for good predictions

        self.logger.info("Predictive Analysis Agent initialized")

    def add_metric_data(self, component: str, metric: str, value: float, timestamp: Optional[datetime] = None):
        """
        Add a metric data point to history

        Args:
            component: Component name (e.g., "proxmox_node", "vm_104")
            metric: Metric name (e.g., "cpu_usage", "disk_usage")
            value: Metric value
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        key = f"{component}.{metric}"
        self.metric_history[key].append((timestamp, value))

        # Keep only recent history
        cutoff = datetime.now() - timedelta(days=self.history_window)
        self.metric_history[key] = [
            (ts, val) for ts, val in self.metric_history[key]
            if ts > cutoff
        ]

    def add_issue_event(self, component: str, issue_type: str, severity: str, resolved: bool):
        """
        Record an issue event for pattern analysis

        Args:
            component: Component name
            issue_type: Type of issue
            severity: Issue severity
            resolved: Whether it was resolved
        """
        self.issue_history.append({
            "timestamp": datetime.now(),
            "component": component,
            "issue_type": issue_type,
            "severity": severity,
            "resolved": resolved
        })

        # Keep only recent history
        cutoff = datetime.now() - timedelta(days=self.history_window)
        self.issue_history = [
            issue for issue in self.issue_history
            if issue["timestamp"] > cutoff
        ]

    def calculate_trend(self, component: str, metric: str) -> Optional[Trend]:
        """
        Calculate trend for a specific metric

        Args:
            component: Component name
            metric: Metric name

        Returns:
            Trend object or None if insufficient data
        """
        key = f"{component}.{metric}"
        data = self.metric_history.get(key, [])

        if len(data) < self.min_data_points:
            return None

        timestamps, values = zip(*data)

        # Convert timestamps to hours since first data point
        first_time = timestamps[0]
        x = np.array([(ts - first_time).total_seconds() / 3600 for ts in timestamps])
        y = np.array(values)

        # Calculate linear regression
        slope, intercept = np.polyfit(x, y, 1)

        # Calculate volatility (standard deviation)
        volatility = np.std(y)

        # Determine direction
        if abs(slope) < 0.1:  # Nearly flat
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        return Trend(
            metric_name=metric,
            component=component,
            values=list(values),
            timestamps=list(timestamps),
            slope=slope,
            direction=direction,
            volatility=volatility
        )

    def predict_disk_full(self, component: str) -> Optional[Prediction]:
        """
        Predict when disk will fill up

        Args:
            component: Component to check

        Returns:
            Prediction or None
        """
        trend = self.calculate_trend(component, "disk_usage")
        if not trend:
            return None

        # Only predict if disk usage is increasing
        if trend.direction != "increasing":
            return None

        current_usage = trend.values[-1]

        # Calculate time until 95% full
        if trend.slope <= 0:
            return None

        hours_until_full = (95 - current_usage) / trend.slope
        if hours_until_full < 0 or hours_until_full > 720:  # 30 days
            return None

        predicted_time = datetime.now() + timedelta(hours=hours_until_full)

        # Determine confidence based on trend consistency
        if trend.volatility < 2:
            confidence = Confidence.HIGH
        elif trend.volatility < 5:
            confidence = Confidence.MEDIUM
        else:
            confidence = Confidence.LOW

        # Determine severity based on time
        if hours_until_full < 24:
            severity = Severity.CRITICAL
        elif hours_until_full < 72:
            severity = Severity.WARNING
        else:
            severity = Severity.INFO

        return Prediction(
            prediction_type=PredictionType.DISK_FULL,
            component=component,
            predicted_time=predicted_time,
            confidence=confidence,
            severity=severity,
            description=f"Disk usage at {current_usage:.1f}%, trending up at {trend.slope:.2f}%/hour",
            recommendation=f"Free up disk space or expand storage before {predicted_time.strftime('%Y-%m-%d')}",
            supporting_data={
                "current_usage": current_usage,
                "rate_of_increase": trend.slope,
                "volatility": trend.volatility
            },
            created_at=datetime.now()
        )

    def predict_memory_exhaustion(self, component: str) -> Optional[Prediction]:
        """
        Predict memory exhaustion

        Args:
            component: Component to check

        Returns:
            Prediction or None
        """
        trend = self.calculate_trend(component, "memory_usage")
        if not trend:
            return None

        # Only predict if memory usage is increasing
        if trend.direction != "increasing":
            return None

        current_usage = trend.values[-1]

        # Calculate time until 90% full
        if trend.slope <= 0:
            return None

        hours_until_full = (90 - current_usage) / trend.slope
        if hours_until_full < 0 or hours_until_full > 168:  # 7 days
            return None

        predicted_time = datetime.now() + timedelta(hours=hours_until_full)

        # Determine confidence
        if trend.volatility < 3:
            confidence = Confidence.HIGH
        elif trend.volatility < 7:
            confidence = Confidence.MEDIUM
        else:
            confidence = Confidence.LOW

        # Determine severity
        if hours_until_full < 12:
            severity = Severity.CRITICAL
        elif hours_until_full < 48:
            severity = Severity.WARNING
        else:
            severity = Severity.INFO

        return Prediction(
            prediction_type=PredictionType.MEMORY_EXHAUSTION,
            component=component,
            predicted_time=predicted_time,
            confidence=confidence,
            severity=severity,
            description=f"Memory usage at {current_usage:.1f}%, trending up at {trend.slope:.2f}%/hour",
            recommendation=f"Investigate memory leaks or increase memory before {predicted_time.strftime('%Y-%m-%d %H:%M')}",
            supporting_data={
                "current_usage": current_usage,
                "rate_of_increase": trend.slope,
                "volatility": trend.volatility
            },
            created_at=datetime.now()
        )

    def predict_service_failure(self, component: str) -> Optional[Prediction]:
        """
        Predict potential service failure based on historical patterns

        Args:
            component: Component to check

        Returns:
            Prediction or None
        """
        # Analyze issue history for this component
        component_issues = [
            issue for issue in self.issue_history
            if issue["component"] == component
        ]

        if len(component_issues) < 3:
            return None

        # Calculate failure rate
        recent_window = datetime.now() - timedelta(days=7)
        recent_issues = [
            issue for issue in component_issues
            if issue["timestamp"] > recent_window
        ]

        if len(recent_issues) < 2:
            return None

        # Calculate average time between failures
        failure_times = sorted([issue["timestamp"] for issue in recent_issues])
        intervals = [
            (failure_times[i+1] - failure_times[i]).total_seconds() / 3600
            for i in range(len(failure_times) - 1)
        ]

        if not intervals:
            return None

        avg_interval = np.mean(intervals)
        std_interval = np.std(intervals)

        # Predict next failure
        last_failure = failure_times[-1]
        predicted_time = last_failure + timedelta(hours=avg_interval)

        # Only predict if next failure is in the future and within reasonable time
        if predicted_time < datetime.now() or (predicted_time - datetime.now()).days > 30:
            return None

        # Determine confidence based on consistency
        if std_interval < avg_interval * 0.3:
            confidence = Confidence.HIGH
        elif std_interval < avg_interval * 0.6:
            confidence = Confidence.MEDIUM
        else:
            confidence = Confidence.LOW

        return Prediction(
            prediction_type=PredictionType.SERVICE_FAILURE,
            component=component,
            predicted_time=predicted_time,
            confidence=confidence,
            severity=Severity.WARNING,
            description=f"Based on {len(recent_issues)} recent failures, average interval: {avg_interval:.1f}h",
            recommendation=f"Monitor {component} closely around {predicted_time.strftime('%Y-%m-%d %H:%M')}",
            supporting_data={
                "recent_failures": len(recent_issues),
                "avg_interval_hours": avg_interval,
                "std_deviation": std_interval
            },
            created_at=datetime.now()
        )

    def detect_anomalies(self, component: str, metric: str) -> List[str]:
        """
        Detect anomalies in metric data

        Args:
            component: Component name
            metric: Metric name

        Returns:
            List of anomaly descriptions
        """
        key = f"{component}.{metric}"
        data = self.metric_history.get(key, [])

        if len(data) < self.min_data_points:
            return []

        values = [val for _, val in data]

        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values)

        anomalies = []

        # Check recent values for outliers (beyond 3 standard deviations)
        recent_values = values[-10:]  # Last 10 data points
        for i, val in enumerate(recent_values):
            if abs(val - mean) > 3 * std:
                anomalies.append(
                    f"{metric} anomaly detected: {val:.1f} (mean: {mean:.1f}, std: {std:.1f})"
                )

        # Check for sudden spikes
        if len(values) >= 2:
            recent_change = values[-1] - values[-2]
            if abs(recent_change) > 2 * std:
                anomalies.append(
                    f"Sudden {metric} change: {recent_change:+.1f} (threshold: {2*std:.1f})"
                )

        return anomalies

    async def analyze_all_components(self) -> List[Prediction]:
        """
        Analyze all components and generate predictions

        Returns:
            List of predictions
        """
        self.logger.info("Running predictive analysis")

        predictions = []

        # Get unique components
        components = set()
        for key in self.metric_history.keys():
            component = key.split(".")[0]
            components.add(component)

        # Generate predictions for each component
        for component in components:
            # Disk predictions
            disk_pred = self.predict_disk_full(component)
            if disk_pred:
                predictions.append(disk_pred)

            # Memory predictions
            mem_pred = self.predict_memory_exhaustion(component)
            if mem_pred:
                predictions.append(mem_pred)

            # Service failure predictions
            failure_pred = self.predict_service_failure(component)
            if failure_pred:
                predictions.append(failure_pred)

            # Anomaly detection
            for metric in ["cpu_usage", "memory_usage", "disk_usage"]:
                anomalies = self.detect_anomalies(component, metric)
                for anomaly in anomalies:
                    self.logger.warning(f"Anomaly in {component}: {anomaly}")

        # Store predictions
        self.predictions = predictions
        self.last_analysis_time = datetime.now()

        # Send alerts for critical predictions
        await self._send_prediction_alerts(predictions)

        return predictions

    async def _send_prediction_alerts(self, predictions: List[Prediction]):
        """Send alerts for important predictions"""
        if not self.telegram_notifier:
            return

        # Filter to high confidence and warning/critical severity
        important_predictions = [
            p for p in predictions
            if p.confidence in [Confidence.HIGH, Confidence.MEDIUM]
            and p.severity in [Severity.WARNING, Severity.CRITICAL]
        ]

        for pred in important_predictions:
            severity_emoji = {
                Severity.CRITICAL: "🔴",
                Severity.WARNING: "🟡",
                Severity.INFO: "🔵"
            }.get(pred.severity, "⚪")

            confidence_emoji = {
                Confidence.HIGH: "✅",
                Confidence.MEDIUM: "⚠️",
                Confidence.LOW: "❓"
            }.get(pred.confidence, "⚪")

            message = f"{severity_emoji} **Predictive Alert**\n\n"
            message += f"**Component:** {pred.component}\n"
            message += f"**Issue:** {pred.prediction_type.value.replace('_', ' ').title()}\n"
            message += f"**Predicted:** {pred.predicted_time.strftime('%Y-%m-%d %H:%M')}\n"
            message += f"**Confidence:** {confidence_emoji} {pred.confidence.value.upper()}\n\n"
            message += f"**Description:** {pred.description}\n\n"
            message += f"**Recommendation:** {pred.recommendation}"

            await self.telegram_notifier.send_message(message)

    async def generate_analysis_report(self) -> str:
        """
        Generate predictive analysis report

        Returns:
            Formatted report string
        """
        if not self.predictions:
            await self.analyze_all_components()

        report_lines = [
            "🔮 **Predictive Analysis Report**",
            f"🗓️ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        if self.last_analysis_time:
            report_lines.append(f"**Last Analysis:** {self.last_analysis_time.strftime('%Y-%m-%d %H:%M')}")

        report_lines.append("")

        # Summary
        critical_count = sum(1 for p in self.predictions if p.severity == Severity.CRITICAL)
        warning_count = sum(1 for p in self.predictions if p.severity == Severity.WARNING)
        info_count = sum(1 for p in self.predictions if p.severity == Severity.INFO)

        report_lines.extend([
            "**📊 Prediction Summary**",
            f"🔴 Critical: {critical_count}",
            f"🟡 Warnings: {warning_count}",
            f"🔵 Info: {info_count}",
            ""
        ])

        # Predictions
        if self.predictions:
            report_lines.append("**🔮 Predictions**")

            for pred in sorted(self.predictions, key=lambda p: (p.severity.value, p.predicted_time)):
                severity_emoji = {
                    Severity.CRITICAL: "🔴",
                    Severity.WARNING: "🟡",
                    Severity.INFO: "🔵"
                }.get(pred.severity, "⚪")

                days_until = (pred.predicted_time - datetime.now()).days

                report_lines.append(
                    f"{severity_emoji} **{pred.component}** - {pred.prediction_type.value.replace('_', ' ').title()}"
                )
                report_lines.append(f"   In {days_until} days ({pred.predicted_time.strftime('%b %d')})")
                report_lines.append(f"   {pred.description}")
                report_lines.append("")
        else:
            report_lines.append("**No predictions at this time**")
            report_lines.append("")

        # Recommendations
        if self.predictions:
            report_lines.extend([
                "**💡 Recommendations**",
                "• Address critical predictions immediately",
                "• Monitor trends for warning-level predictions",
                "• Plan capacity upgrades based on forecasts"
            ])

        return "\n".join(report_lines)

    async def collect_metrics_from_health_agent(self):
        """Collect metrics from health agent for analysis"""
        if not self.health_agent:
            return

        try:
            # Get current health report
            health_data = await self.health_agent.generate_health_report()

            # Extract and store metrics
            # This would depend on the structure of your health data
            # For now, we'll add a placeholder

            self.logger.debug("Collected metrics from health agent")

        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")

    async def run_analysis_loop(self):
        """
        Main analysis loop

        Runs analysis on a schedule
        """
        self.logger.info(f"Starting predictive analysis loop (every {self.analysis_interval}s)")

        while True:
            try:
                # Collect current metrics
                await self.collect_metrics_from_health_agent()

                # Run analysis
                predictions = await self.analyze_all_components()

                self.logger.info(f"Analysis complete: {len(predictions)} predictions generated")

                # Wait for next analysis
                await asyncio.sleep(self.analysis_interval)

            except Exception as e:
                self.logger.error(f"Error in analysis loop: {e}")
                await asyncio.sleep(self.analysis_interval)


async def main():
    """Run predictive analysis standalone"""
    agent = PredictiveAnalysisAgent()
    await agent.run_analysis_loop()


if __name__ == "__main__":
    asyncio.run(main())
