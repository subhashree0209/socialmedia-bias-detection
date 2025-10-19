import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


st.set_page_config(
    page_title="Dashboard Analytics",
    page_icon="📊",
    layout="wide"
)

#CSS
st.markdown("""
<style>
    .header-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .header-icon {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        object-fit: contain;
        background: white;
        padding: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #ff4500;
        font-family: 'Arial', sans-serif;
        margin: 0;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #1a1a1b;
        margin-bottom: 1rem;
        border-left: 4px solid #ff4500;
        padding-left: 0.8rem;
        background-color: #f6f7f8;
        padding: 0.8rem;
        border-radius: 4px;
        font-family: 'Arial', sans-serif;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid #edeff1;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .time-metric {
        font-size: 2rem;
        font-weight: bold;
        color: #1a1a1b;
        font-family: 'Arial', sans-serif;
    }
    .time-label {
        font-size: 0.9rem;
        color: #7c7c7c;
        font-family: 'Arial', sans-serif;
    }
    .subreddit-item {
        background-color: #ffffff;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        border: 1px solid #edeff1;
        margin-bottom: 0.5rem;
        font-family: 'Arial', sans-serif;
        color: #1a1a1b;
        transition: background-color 0.2s;
    }
    .subreddit-item:hover {
        background-color: #f6f7f8;
    }
    .subreddit-prefix {
        color: #ff4500;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    .channel-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #edeff1;
        text-align: center;
        font-family: 'Arial', sans-serif;
        color: #1a1a1b;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        height: 100%;
    }
    .stats-badge {
        background-color: #ff4500;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    .total-time-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #ff4500;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .combined-screentime-section {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #edeff1;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .screentime-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .total-time-compact {
        font-size: 1.5rem;
        font-weight: bold;
        color: #ff4500;
        font-family: 'Arial', sans-serif;
    }
    .time-label-compact {
        font-size: 0.8rem;
        color: #7c7c7c;
        font-family: 'Arial', sans-serif;
    }
    .header-image {
        width: 100%;
        max-height: 200px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 3px solid #ff4500;
    }
    
    .main {
        background-color: #dae0e6;
    }
    .stApp {
        background-color: #dae0e6;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(
    '''
    <div class="header-container">
        <div><img class="header-icon" src="https://www.redditstatic.com/shreddit/assets/favicon/64x64.png"></div>
        <div class="main-header">DASHBOARD ANALYTICS</div>
        <div><img class="header-icon" src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png"></div>
    </div>
    ''', 
    unsafe_allow_html=True
)

# Create two main columns
col1, col2 = st.columns([1, 1])

with col1:
    # Political Spectrum Pie Chart 
    st.markdown('<div class="section-header">🎯 Political Spectrum</div>', unsafe_allow_html=True)
    
    #pie chart data for political spectrum
    spectrum = ['Left Wing', 'Right Wing', 'Neutral']
    spectrum_hours = [4.22, 6.5, 2.0]  
    spectrum_display = ['4h 13m', '6h 30m', '2h 0m']
    
    #pie chart for political spectrum
    fig_spectrum = go.Figure(data=[go.Pie(
        labels=spectrum,
        values=spectrum_hours,
        textinfo='percent',
        textposition='inside',
        hovertemplate='<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>',
        customdata=spectrum_display,
        marker=dict(
            colors=['#ff4500', '#0079d3', '#46d160'],  # Red for left, Blue for right, Green for neutral
            line=dict(color='white', width=2)
        )
    )])
    
    fig_spectrum.update_layout(
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=0, b=40),
        font=dict(family='Arial', size=12)
    )
    
    st.plotly_chart(fig_spectrum, use_container_width=True, key="political_spectrum_pie")

with col2:
    # Screentime Analysis Section - Donut chart only, no extra container
    st.markdown('<div class="section-header">⏰ Screentime Analysis</div>', unsafe_allow_html=True)
    
    # Mode Breakdown Donut Chart with Total Time in Center
    modes = ['Skeptical Mode', 'Vibes Mode']
    hours = [4.22, 6.5]
    # Convert decimal hours to hours and minutes for display
    time_display = ['4h 13m', '6h 30m']
    
    fig_modes = go.Figure(data=[go.Pie(
        labels=modes,
        values=hours,
        textinfo='label+text',  
        text=time_display, 
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>%{customdata}<extra></extra>',
        customdata=time_display,
        marker=dict(colors=['#ff4500', '#0079d3'], line=dict(color='white', width=2)),
        hole=0.7, 
        textfont=dict(size=12)
    )])
    
    fig_modes.update_layout(
        height=400,
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family='Arial', size=12),
        annotations=[
            dict(
                text='10h 43m',
                x=0.5, y=0.5,
                font=dict(size=24, color='#ff4500', family='Arial', weight='bold'),
                showarrow=False
            ),
            dict(
                text='Total Screentime',
                x=0.5, y=0.42,
                font=dict(size=14, color='#7c7c7c', family='Arial'),
                showarrow=False
            )
        ]
    )
    
    st.plotly_chart(fig_modes, use_container_width=True, key="mode_breakdown_pie")
    
    # Top Subreddits Bar Chart section 
    st.markdown('<div class="section-header">🏆 Top Subreddits Engagement</div>', unsafe_allow_html=True)
    st.markdown('*Posts and engagement across your most visited communities*')
    
    # Data for bar chart (TO BE CHANGED)
    subreddit_data = pd.DataFrame({
        'Subreddit': ['r/Singapore', 'r/askSingapore', 'r/SGexams', 'r/SingaporeFI'],
        'Posts': [1200, 845, 612, 398],
        'Engagement_Score': [85, 72, 68, 45]  # Combined metric of upvotes, comments, etc.
    })
    
    #horizontal bar chart
    fig_bar = go.Figure()
    
    # Add bars for posts
    fig_bar.add_trace(go.Bar(
        y=subreddit_data['Subreddit'],
        x=subreddit_data['Posts'],
        orientation='h',
        name='Posts',
        marker_color='#ff4500',
        text=subreddit_data['Posts'],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Posts: %{x:,}<extra></extra>'
    ))
    

    fig_bar.update_layout(
        height=400,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family='Arial', size=12),
        xaxis_title="Number of Posts",
        yaxis_title="",
        plot_bgcolor='white',
        xaxis=dict(
            gridcolor='#edeff1',
            showgrid=True
        ),
        yaxis=dict(
            categoryorder='total ascending'
        )
    )
    
    st.plotly_chart(fig_bar, use_container_width=True, key="top_subreddits_bar")


st.markdown("<br><br>", unsafe_allow_html=True)
