# tests/performance/visualization/chart_generator.py

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

from utils.logger import CustomLogger
from tests.performance.metrics_collector import MetricsCollector
from tests.performance.metrics_analyzer import MetricsAnalyzer, Trend, Anomaly

logger = CustomLogger("chart_generator", "visualization.log")

class ChartGenerator:
    """Generates interactive charts for metric visualization"""
    
    def __init__(
        self,
        collector: MetricsCollector,
        analyzer: MetricsAnalyzer,
        output_dir: str = "test/reports/charts"
    ):
        self.collector = collector
        self.analyzer = analyzer
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Chart configuration
        self.color_scheme = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e',
            'success': '#2ca02c',
            'warning': '#d62728',
            'neutral': '#7f7f7f'
        }
        
        self.default_layout = {
            'template': 'plotly_white',
            'showlegend': True,
            'hovermode': 'x unified',
            'margin': dict(l=50, r=50, t=50, b=50)
        }

    def generate_time_series_chart(
        self,
        category: str,
        name: str,
        show_trend: bool = True,
        show_anomalies: bool = True
    ) -> go.Figure:
        """Generate time series chart for a metric"""
        timeseries = self.collector.get_metric_timeseries(category, name)
        if not timeseries:
            logger.warning(f"No data found for {category}.{name}")
            return None
            
        # Create figure
        fig = go.Figure()
        
        # Add main metric line
        fig.add_trace(go.Scatter(
            x=[datetime.fromtimestamp(t) for t in timeseries.timestamps],
            y=timeseries.values,
            mode='lines',
            name=f"{category}.{name}",
            line=dict(color=self.color_scheme['primary'])
        ))
        
        # Add trend line if requested
        if show_trend:
            trend = self.analyzer.trends.get(category, {}).get(name)
            if trend:
                x_trend = np.array(timeseries.timestamps)
                y_trend = trend.slope * (x_trend - x_trend[0]) + timeseries.values[0]
                
                fig.add_trace(go.Scatter(
                    x=[datetime.fromtimestamp(t) for t in x_trend],
                    y=y_trend,
                    mode='lines',
                    name='Trend',
                    line=dict(
                        color=self.color_scheme['secondary'],
                        dash='dash'
                    )
                ))
        
        # Add anomalies if requested
        if show_anomalies:
            anomalies = self.analyzer.anomalies.get(category, {}).get(name, [])
            if anomalies:
                anomaly_times = [datetime.fromtimestamp(a.timestamp) for a in anomalies]
                anomaly_values = [a.metric_value for a in anomalies]
                anomaly_colors = [
                    self.color_scheme['warning'] if a.severity == 'high'
                    else self.color_scheme['neutral']
                    for a in anomalies
                ]
                
                fig.add_trace(go.Scatter(
                    x=anomaly_times,
                    y=anomaly_values,
                    mode='markers',
                    name='Anomalies',
                    marker=dict(
                        color=anomaly_colors,
                        size=10,
                        symbol='x'
                    )
                ))
        
        # Update layout
        fig.update_layout(
            title=f"{category}.{name} Over Time",
            xaxis_title="Time",
            yaxis_title=self.collector.metric_units.get(category, {}).get(name, "Value"),
            **self.default_layout
        )
        
        return fig

    def generate_correlation_matrix(
        self,
        categories: Optional[List[str]] = None
    ) -> go.Figure:
        """Generate correlation matrix heatmap"""
        # Get correlations
        correlations = self.analyzer.correlations
        if not correlations:
            logger.warning("No correlations found")
            return None
            
        # Create correlation matrix
        metrics = list(set(
            [c.metric1 for c in correlations] +
            [c.metric2 for c in correlations]
        ))
        matrix = pd.DataFrame(
            np.zeros((len(metrics), len(metrics))),
            index=metrics,
            columns=metrics
        )
        
        for corr in correlations:
            matrix.loc[corr.metric1, corr.metric2] = corr.correlation
            matrix.loc[corr.metric2, corr.metric1] = corr.correlation
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            colorscale='RdBu',
            zmid=0,
            text=np.round(matrix.values, 2),
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        # Update layout
        fig.update_layout(
            title="Metric Correlations",
            xaxis_title="Metric",
            yaxis_title="Metric",
            **self.default_layout
        )
        
        return fig

    def generate_anomaly_distribution(
        self,
        category: str,
        name: str
    ) -> go.Figure:
        """Generate anomaly distribution chart"""
        timeseries = self.collector.get_metric_timeseries(category, name)
        anomalies = self.analyzer.anomalies.get(category, {}).get(name, [])
        
        if not timeseries or not anomalies:
            logger.warning(f"No data or anomalies found for {category}.{name}")
            return None
            
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add metric distribution
        values = np.array(timeseries.values)
        kde = stats.gaussian_kde(values)
        x_range = np.linspace(min(values), max(values), 100)
        
        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=kde(x_range),
                name="Value Distribution",
                fill='tozeroy',
                line=dict(color=self.color_scheme['primary'])
            ),
            secondary_y=False
        )
        
        # Add anomaly markers
        fig.add_trace(
            go.Scatter(
                x=[a.metric_value for a in anomalies],
                y=[0] * len(anomalies),  # Place at bottom
                mode='markers',
                name='Anomalies',
                marker=dict(
                    color=[
                        self.color_scheme['warning'] if a.severity == 'high'
                        else self.color_scheme['neutral']
                        for a in anomalies
                    ],
                    size=10,
                    symbol='triangle-up'
                )
            ),
            secondary_y=False
        )
        
        # Update layout
        fig.update_layout(
            title=f"Value Distribution and Anomalies for {category}.{name}",
            xaxis_title="Metric Value",
            yaxis_title="Density",
            **self.default_layout
        )
        
        return fig

    def generate_trend_summary(
        self,
        min_confidence: float = 0.7
    ) -> go.Figure:
        """Generate trend summary chart"""
        # Collect significant trends
        significant_trends = []
        for category, trends in self.analyzer.trends.items():
            for name, trend in trends.items():
                if trend.confidence >= min_confidence:
                    significant_trends.append({
                        'metric': f"{category}.{name}",
                        'slope': trend.slope,
                        'confidence': trend.confidence,
                        'type': trend.trend_type
                    })
        
        if not significant_trends:
            logger.warning("No significant trends found")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(significant_trends)
        
        # Create figure
        fig = go.Figure()
        
        # Add bars for trend slopes
        fig.add_trace(go.Bar(
            x=df['metric'],
            y=df['slope'],
            marker_color=[
                self.color_scheme['success'] if t == 'increasing'
                else self.color_scheme['warning'] if t == 'decreasing'
                else self.color_scheme['neutral']
                for t in df['type']
            ],
            name='Trend Slope'
        ))
        
        # Add confidence markers
        fig.add_trace(go.Scatter(
            x=df['metric'],
            y=df['confidence'],
            mode='markers',
            name='Confidence',
            marker=dict(
                color=self.color_scheme['secondary'],
                size=10,
                symbol='diamond'
            ),
            yaxis='y2'
        ))
        
        # Update layout
        fig.update_layout(
            title="Significant Metric Trends",
            xaxis_title="Metric",
            yaxis_title="Trend Slope",
            yaxis2=dict(
                title="Confidence",
                overlaying='y',
                side='right',
                range=[0, 1]
            ),
            **self.default_layout
        )
        
        return fig

    def save_all_charts(self, prefix: str = ""):
        """Generate and save all charts"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Time series charts
        for category in self.collector.raw_metrics:
            for name in self.collector.raw_metrics[category]:
                fig = self.generate_time_series_chart(category, name)
                if fig:
                    filename = f"{prefix}timeseries_{category}_{name}_{timestamp}.html"
                    fig.write_html(self.output_dir / filename)
        
        # Correlation matrix
        fig = self.generate_correlation_matrix()
        if fig:
            filename = f"{prefix}correlations_{timestamp}.html"
            fig.write_html(self.output_dir / filename)
        
        # Anomaly distributions
        for category, cat_anomalies in self.analyzer.anomalies.items():
            for name in cat_anomalies:
                fig = self.generate_anomaly_distribution(category, name)
                if fig:
                    filename = f"{prefix}anomalies_{category}_{name}_{timestamp}.html"
                    fig.write_html(self.output_dir / filename)
        
        # Trend summary
        fig = self.generate_trend_summary()
        if fig:
            filename = f"{prefix}trends_{timestamp}.html"
            fig.write_html(self.output_dir / filename)
        
        logger.info(f"Charts saved to {self.output_dir}")

if __name__ == "__main__":
    # Test visualization
    from tests.performance.metrics_collector import MetricsCollector
    from tests.performance.metrics_analyzer import MetricsAnalyzer
    
    # Create test data
    collector = MetricsCollector()
    timestamps = list(range(100))
    values = [np.sin(t/10) + np.random.normal(0, 0.1) for t in timestamps]
    
    for t, v in zip(timestamps, values):
        collector.add_metric("test", "metric1", v, float(t))
    
    # Analyze data
    analyzer = MetricsAnalyzer(collector)
    analyzer.analyze_trends("test", "metric1")
    analyzer.detect_anomalies("test", "metric1")
    
    # Generate charts
    generator = ChartGenerator(collector, analyzer)
    generator.save_all_charts("test_")
    print("Test charts generated")
