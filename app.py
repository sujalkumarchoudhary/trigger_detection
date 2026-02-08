"""
Real-Time Trigger Detection System - Streamlit Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import sys
import os

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import TriggerDatabase
from monitors import NewsMonitor, RegulatoryMonitor, TenderMonitor, FinancialMonitor

# Page config
st.set_page_config(
    page_title="Trigger Detection System",
    page_icon="🔔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .trigger-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 0.5rem;
    }
    .score-high { color: #28a745; font-weight: bold; }
    .score-medium { color: #ffc107; font-weight: bold; }
    .score-low { color: #dc3545; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 24px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state"""
    if 'db' not in st.session_state:
        st.session_state.db = TriggerDatabase()
    if 'running_monitor' not in st.session_state:
        st.session_state.running_monitor = None


def get_score_class(score: float) -> str:
    """Get CSS class for score"""
    if score >= 7:
        return "score-high"
    elif score >= 4:
        return "score-medium"
    return "score-low"


def render_sidebar():
    """Render sidebar"""
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/radar.png", width=80)
        st.markdown("## 🔔 Trigger Detection")
        st.markdown("---")
        
        # Filters
        st.markdown("### 🔍 Filters")
        
        source_filter = st.selectbox(
            "Source Type",
            ["All", "news", "regulatory", "tender", "financial"]
        )
        
        min_score = st.slider(
            "Minimum Score",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5
        )
        
        company_filter = st.text_input("Company Name", "")
        
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        Real-time monitoring system for:
        - 📰 News & Events
        - 📋 Regulatory Changes
        - 📑 Tenders & Contracts
        - 📊 Financial Indicators
        """)
        
        return source_filter, min_score, company_filter


def render_dashboard(source_filter, min_score, company_filter):
    """Render main dashboard"""
    db = st.session_state.db
    
    # Get stats
    stats = db.get_trigger_stats()
    
    # Header
    st.markdown('<p class="main-header">🔔 Trigger Detection Dashboard</p>', unsafe_allow_html=True)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Triggers", stats['total_triggers'], delta=None)
    with col2:
        st.metric("High Score (≥7)", stats['high_score_count'])
    with col3:
        st.metric("Last 24 Hours", stats['recent_triggers'])
    with col4:
        news_count = stats.get('by_source', {}).get('news', 0)
        st.metric("News Triggers", news_count)
    
    st.markdown("---")
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Triggers by Source")
        source_data = stats.get('by_source', {})
        if source_data:
            fig = px.pie(
                names=list(source_data.keys()),
                values=list(source_data.values()),
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet. Run monitors to collect triggers.")
    
    with col2:
        st.subheader("🏢 Top Companies")
        company_data = stats.get('top_companies', {})
        if company_data:
            fig = px.bar(
                x=list(company_data.values()),
                y=list(company_data.keys()),
                orientation='h',
                color=list(company_data.values()),
                color_continuous_scale='Viridis'
            )
            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=False,
                coloraxis_showscale=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No company data yet.")
    
    st.markdown("---")
    
    # Triggers table
    st.subheader("📋 Recent Triggers")
    
    # Apply filters
    filters = {'limit': 100}
    if source_filter != "All":
        filters['source_type'] = source_filter
    if min_score > 0:
        filters['min_score'] = min_score
    if company_filter:
        filters['company_name'] = company_filter
    
    triggers = db.get_triggers(**filters)
    
    if triggers:
        # Convert to dataframe
        data = []
        for t in triggers:
            data.append({
                'ID': t.id,
                'Score': t.trigger_score,
                'Type': t.source_type,
                'Title': t.title[:80] + '...' if len(t.title) > 80 else t.title,
                'Company': t.company_name or '-',
                'Keywords': ', '.join(t.get_keywords_list()[:3]),
                'Detected': t.detected_at.strftime('%Y-%m-%d %H:%M') if t.detected_at else '-',
                'URL': t.url,
            })
        
        df = pd.DataFrame(data)
        
        # Style the dataframe
        def highlight_score(val):
            if val >= 7:
                return 'background-color: #d4edda; color: #155724'
            elif val >= 4:
                return 'background-color: #fff3cd; color: #856404'
            return ''
        
        styled_df = df.style.applymap(highlight_score, subset=['Score'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Export button
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            "triggers_export.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("No triggers found. Run the monitors to collect data.")


def render_run_pipeline_tab():
    """Render the Run Pipeline tab"""
    st.subheader("🚀 Run Trigger Detection")
    st.markdown("Run monitors to detect new triggers from various sources.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📰 News Monitor")
        st.markdown("RSS feeds + Google News")
        if st.button("Run News Monitor", key="run_news"):
            with st.spinner("Running News Monitor..."):
                try:
                    monitor = NewsMonitor()
                    results = monitor.run()
                    st.success(f"✅ Found {len(results)} triggers!")
                    
                    # Store results
                    db = st.session_state.db
                    for r in results:
                        from database.models import TriggerEvent
                        trigger = TriggerEvent(
                            source_type=r.source_type,
                            source_name=r.source_name,
                            title=r.title,
                            content=r.content,
                            url=r.url,
                            company_name=r.company_name,
                            trigger_keywords=json.dumps(r.trigger_keywords),
                            sentiment_score=r.sentiment_score,
                            trigger_score=r.trigger_score,
                            detected_at=r.detected_at,
                            published_at=r.published_at,
                        )
                        db.insert_trigger(trigger)
                except Exception as e:
                    st.error(f"Error: {e}")
        
        st.markdown("---")
        
        st.markdown("### 📑 Tender Monitor")
        st.markdown("GEM portal + CPPP + Hospitals")
        if st.button("Run Tender Monitor", key="run_tender"):
            with st.spinner("Running Tender Monitor..."):
                try:
                    monitor = TenderMonitor()
                    results = monitor.run()
                    st.success(f"✅ Found {len(results)} triggers!")
                    
                    db = st.session_state.db
                    for r in results:
                        from database.models import TriggerEvent
                        trigger = TriggerEvent(
                            source_type=r.source_type,
                            source_name=r.source_name,
                            title=r.title,
                            content=r.content,
                            url=r.url,
                            company_name=r.company_name,
                            trigger_keywords=json.dumps(r.trigger_keywords),
                            sentiment_score=r.sentiment_score,
                            trigger_score=r.trigger_score,
                            detected_at=r.detected_at,
                            published_at=r.published_at,
                        )
                        db.insert_trigger(trigger)
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col2:
        st.markdown("### 📋 Regulatory Monitor")
        st.markdown("CDSCO + FDA Alerts")
        if st.button("Run Regulatory Monitor", key="run_regulatory"):
            with st.spinner("Running Regulatory Monitor..."):
                try:
                    monitor = RegulatoryMonitor()
                    results = monitor.run()
                    st.success(f"✅ Found {len(results)} triggers!")
                    
                    db = st.session_state.db
                    for r in results:
                        from database.models import TriggerEvent
                        trigger = TriggerEvent(
                            source_type=r.source_type,
                            source_name=r.source_name,
                            title=r.title,
                            content=r.content,
                            url=r.url,
                            company_name=r.company_name,
                            trigger_keywords=json.dumps(r.trigger_keywords),
                            sentiment_score=r.sentiment_score,
                            trigger_score=r.trigger_score,
                            detected_at=r.detected_at,
                            published_at=r.published_at,
                        )
                        db.insert_trigger(trigger)
                except Exception as e:
                    st.error(f"Error: {e}")
        
        st.markdown("---")
        
        st.markdown("### 📊 Financial Monitor")
        st.markdown("Stock filings + Job postings")
        if st.button("Run Financial Monitor", key="run_financial"):
            with st.spinner("Running Financial Monitor..."):
                try:
                    monitor = FinancialMonitor()
                    results = monitor.run()
                    st.success(f"✅ Found {len(results)} triggers!")
                    
                    db = st.session_state.db
                    for r in results:
                        from database.models import TriggerEvent
                        trigger = TriggerEvent(
                            source_type=r.source_type,
                            source_name=r.source_name,
                            title=r.title,
                            content=r.content,
                            url=r.url,
                            company_name=r.company_name,
                            trigger_keywords=json.dumps(r.trigger_keywords),
                            sentiment_score=r.sentiment_score,
                            trigger_score=r.trigger_score,
                            detected_at=r.detected_at,
                            published_at=r.published_at,
                        )
                        db.insert_trigger(trigger)
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.markdown("---")
    
    # Run all button
    if st.button("🚀 Run All Monitors", type="primary", use_container_width=True):
        monitors = [
            ("News", NewsMonitor),
            ("Regulatory", RegulatoryMonitor),
            ("Tender", TenderMonitor),
            ("Financial", FinancialMonitor),
        ]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_triggers = 0
        
        for i, (name, MonitorClass) in enumerate(monitors):
            status_text.text(f"Running {name} Monitor...")
            
            try:
                monitor = MonitorClass()
                results = monitor.run()
                total_triggers += len(results)
                
                db = st.session_state.db
                for r in results:
                    from database.models import TriggerEvent
                    trigger = TriggerEvent(
                        source_type=r.source_type,
                        source_name=r.source_name,
                        title=r.title,
                        content=r.content,
                        url=r.url,
                        company_name=r.company_name,
                        trigger_keywords=json.dumps(r.trigger_keywords),
                        sentiment_score=r.sentiment_score,
                        trigger_score=r.trigger_score,
                        detected_at=r.detected_at,
                        published_at=r.published_at,
                    )
                    db.insert_trigger(trigger)
                    
            except Exception as e:
                st.warning(f"{name} Monitor error: {e}")
            
            progress_bar.progress((i + 1) / len(monitors))
        
        status_text.text("")
        st.success(f"✅ Complete! Found {total_triggers} total triggers.")
        st.balloons()


def render_export_tab():
    """Render export tab"""
    st.subheader("📥 Export Triggers")
    
    db = st.session_state.db
    stats = db.get_trigger_stats()
    
    st.info(f"Total triggers available for export: **{stats['total_triggers']}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_source = st.selectbox(
            "Filter by Source",
            ["All", "news", "regulatory", "tender", "financial"],
            key="export_source"
        )
    
    with col2:
        export_min_score = st.slider(
            "Minimum Score",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            key="export_min_score"
        )
    
    # Preview
    filters = {'limit': 10}
    if export_source != "All":
        filters['source_type'] = export_source
    if export_min_score > 0:
        filters['min_score'] = export_min_score
    
    preview_triggers = db.get_triggers(**filters)
    
    if preview_triggers:
        st.markdown("### Preview (first 10 rows)")
        preview_data = []
        for t in preview_triggers:
            preview_data.append({
                'Score': t.trigger_score,
                'Type': t.source_type,
                'Title': t.title[:50] + '...' if len(t.title) > 50 else t.title,
                'Company': t.company_name or '-',
            })
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
    
    # Full export
    st.markdown("### Full Export")
    
    full_filters = {'limit': 10000}
    if export_source != "All":
        full_filters['source_type'] = export_source
    if export_min_score > 0:
        full_filters['min_score'] = export_min_score
    
    all_triggers = db.get_triggers(**full_filters)
    
    if all_triggers:
        export_data = []
        for t in all_triggers:
            export_data.append({
                'ID': t.id,
                'Source Type': t.source_type,
                'Source Name': t.source_name,
                'Title': t.title,
                'Company': t.company_name,
                'Trigger Score': t.trigger_score,
                'Sentiment Score': t.sentiment_score,
                'Keywords': ', '.join(t.get_keywords_list()),
                'URL': t.url,
                'Detected At': t.detected_at,
                'Content': t.content[:500] if t.content else '',
            })
        
        export_df = pd.DataFrame(export_data)
        
        csv = export_df.to_csv(index=False)
        st.download_button(
            f"📥 Download {len(export_data)} Triggers as CSV",
            csv,
            f"triggers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            use_container_width=True,
            type="primary"
        )
    else:
        st.warning("No triggers match the selected filters.")


def main():
    """Main app entry point"""
    init_session_state()
    
    # Sidebar
    source_filter, min_score, company_filter = render_sidebar()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🚀 Run Pipeline", "📥 Export"])
    
    with tab1:
        render_dashboard(source_filter, min_score, company_filter)
    
    with tab2:
        render_run_pipeline_tab()
    
    with tab3:
        render_export_tab()


if __name__ == "__main__":
    main()
