import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

st.set_page_config(
    page_title="Dashboard Analytics",
    page_icon="📊",
    layout="wide"
)

#Connecting dashboard to database
@st.cache_resource(ttl=300)
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'db'),
            database=os.getenv('DB_NAME', 'mydatabase'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'root'),
            port=os.getenv('DB_PORT', '3306')
        )
        return connection
    except Error as e:
        st.error(f"Database connection failed: {e}")
        return None
    

#Political spectrum data
@st.cache_data(ttl=60)
def get_political_spectrum_data():
    connection = get_db_connection()
    if connection is None:
        return None
    
    try:
        query = """
        SELECT 
            bias_label,
            COUNT(*) as post_count,
            COUNT(DISTINCT user_id) as unique_users
        FROM user_activity 
        WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY bias_label
        ORDER BY post_count DESC
        """
        
        df = pd.read_sql(query, connection, params=[days_back])
        
        return df
    except Error as e:
        st.error(f"Error fetching political data: {e}")
        return None
    finally:
        if connection.is_connected():
            connection.close()

#top subreddit data           
@st.cache_data(ttl=60)
def get_top_categories_data():
    connection = get_db_connection()
    if connection is None:
        return None
    
    try:
        query = """
        SELECT 
            bias_label,
            COUNT(*) as post_count,
            AVG(LENGTH(title)) as avg_title_length
        FROM user_activity 
        WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY bias_label
        ORDER BY post_count DESC
        LIMIT 10
        """
        
        df = pd.read_sql(query, connection)
        return df
    except Error as e:
        st.error(f"Error fetching categories data: {e}")
        return None
    finally:
        if connection.is_connected():
            connection.close()

# Static screentime data
def get_static_screentime_data():
    return {
        'modes': ['Skeptical Mode', 'Vibes Mode'],
        'hours': [4.22, 6.5],
        'time_display': ['4h 13m', '6h 30m'],
        'total_display': '10h 43m'
    }
    


# Clean CSS with minimal spacing
st.markdown("""
<style>
    .header-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .header-icon {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        object-fit: contain;
        background: white;
        padding: 8px;
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
        margin-bottom: 0.5rem;
        font-family: 'Arial', sans-serif;
        text-align: center;
    }
    
    /* Clean white background */
    .main {
        background-color: white !important;
    }
    .stApp {
        background-color: white !important;
    }
    
    .stPlotlyChart {
        border-radius: 0px;
    }
    
    /* Reduce space between columns */
    [data-testid="column"] {
        gap: 0rem;
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

# Create two main columns with minimal gap
col1, col2 = st.columns([1, 1], gap="small")

with col1:
    # Get live data from user_activity table
    political_data = get_political_spectrum_data()
    
    if political_data is not None and not political_data.empty:
        # Process database data for the chart
        spectrum = []
        post_counts = []
        time_displays = []
        
        for _, row in political_data.iterrows():
            spectrum.append(row['bias_label'].title())
            post_counts.append(row['post_count'])
            time_displays.append(count_to_time_display(row['post_count']))
        
        # If no data, use fallback
        if not spectrum:
            spectrum = ['Left', 'Right', 'Neutral']
            post_counts = [42, 65, 20]  
            time_displays = ['1h 24m', '2h 10m', '0h 40m']
            
    else:
        # Fallback data if database is unavailable
        spectrum = ['Left', 'Right', 'Neutral']
        post_counts = [42, 65, 20]  
        time_displays = ['1h 24m', '2h 10m', '0h 40m']
    
    # Pie chart for political spectrum
    fig_spectrum = go.Figure(data=[go.Pie(
        labels=spectrum,
        values=post_counts,
        textinfo='percent+label',
        textposition='inside',
        hovertemplate='<b>%{label}</b><br>Posts: %{value}<br>%{customdata}<extra></extra>',
        customdata=time_displays,
        marker=dict(
            colors=['#ff4500', '#0079d3', '#46d160'],
            line=dict(color='white', width=2)
        )
    )])
    
    fig_spectrum.update_layout(
        height=300,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family='Arial', size=12),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig_spectrum, use_container_width=True, key="political_spectrum_pie")

    # Screentime Analysis Section
    st.markdown('<div class="section-header">⏰ Screentime Analysis</div>', unsafe_allow_html=True)
    
    # Mode Breakdown Donut Chart
    modes = ['Skeptical Mode', 'Vibes Mode']
    hours = [4.22, 6.5]
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
        height=300,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family='Arial', size=12),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
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

with col2:
    # Top Subreddits Bar Chart section 
    st.markdown('<div class="section-header">🏆 Top Subreddits Engagement</div>', unsafe_allow_html=True)
    st.markdown('*Posts and engagement across your most visited communities*')
    
    # Get categories data from database
    categories_data = get_top_categories_data()
    
    if categories_data is not None and not categories_data.empty:
        # Use database data
        y_data = [f"{row['bias_label'].title()}" for _, row in categories_data.iterrows()]
        x_data = categories_data['post_count'].tolist()
    else:
        # Fallback data
        categories_data = pd.DataFrame({
            'bias_label': ['/politics', '/USpolitics', 'Askpolitics'],
            'post_count': [42, 65, 20]
        })
        y_data = [f"{label}" for label in categories_data['bias_label']]
        x_data = categories_data['post_count'].tolist()

    
    # Horizontal bar chart
    fig_categories = go.Figure()
    
    fig_categories.add_trace(go.Bar(
        y=y_data,
        x=x_data,
        orientation='h',
        name='Posts',
        marker_color='#ff4500',
        text=x_data,
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Posts: %{x:,}<extra></extra>'
    ))
    
    fig_categories.update_layout(
        height=400,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family='Arial', size=12),
        xaxis_title="Number of Posts",
        yaxis_title="",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            gridcolor='#f0f0f0',
            showgrid=True
        ),
        yaxis=dict(
            categoryorder='total ascending'
        )
    )
    
    st.plotly_chart(fig_categories, use_container_width=True, key="categories_bar")
