import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(page_title="Symphony Campaign Performance", layout="wide")

st.title("🎻 Symphony Orchestra: Outbound Campaign Dashboard")
st.markdown("### Tracking conversion efficiency for 2027 and beyond")

# --- Helper Function to Load & Clean Data ---
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    
    # Date Conversion
    df['plan_close_dt'] = pd.to_datetime(df['plan_close_dt'], errors='coerce')
    df['order_dt'] = pd.to_datetime(df['order_dt'], errors='coerce')
    
    # Map Contacts Count based on 'previous_step_at_closure'
    # Adjust this map if your CRM terminology changes
    contact_map = {
        'TKT - To start': 0,
        'TKT - 1st contact complete': 1,
        'TKT - 2nd contact complete': 2,
        'TKT - 3rd contact complete': 3,
        'TKT - 4th contact complete': 4,
        'TKT - 5th contact complete': 5
    }
    # Use a regex or map to handle variations if needed, defaulting to map for now
    df['contact_count'] = df['previous_step_at_closure'].map(contact_map).fillna(0)
    
    return df

# --- Sidebar: Data Upload & Filters ---
st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your daily campaign CSV", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # Determine file type
        if uploaded_file.name.endswith('.csv'):
            df = load_data(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            # Re-apply cleaning steps if excel (copy logic from load_data or simplify)
            df['plan_close_dt'] = pd.to_datetime(df['plan_close_dt'], errors='coerce')
            df['order_dt'] = pd.to_datetime(df['order_dt'], errors='coerce')
            contact_map = {'TKT - To start': 0, 'TKT - 1st contact complete': 1, 
                           'TKT - 2nd contact complete': 2, 'TKT - 3rd contact complete': 3}
            df['contact_count'] = df['previous_step_at_closure'].map(contact_map).fillna(0)

        st.sidebar.header("2. Filters")
        
        # Filter: Campaign Year
        years = sorted(df['campaign_year'].unique())
        selected_year = st.sidebar.multiselect("Select Campaign Year", years, default=years)
        
        # Filter: Campaign Series
        series_list = sorted(df['campaign_series'].unique())
        selected_series = st.sidebar.multiselect("Select Series", series_list, default=series_list)
        
        # Apply Filters
        filtered_df = df[
            (df['campaign_year'].isin(selected_year)) & 
            (df['campaign_series'].isin(selected_series))
        ]
        
        # --- Main Dashboard Area ---
        
        # Row 1: Top Level Metrics
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        total_sales = len(filtered_df)
        avg_contacts = filtered_df['contact_count'].mean()
        avg_days = filtered_df['days_to_plan_close'].mean()
        pct_zero_contact = (len(filtered_df[filtered_df['contact_count'] == 0]) / total_sales * 100) if total_sales > 0 else 0
        
        col1.metric("Total Sales Converted", f"{total_sales}")
        col2.metric("Avg Contacts per Sale", f"{avg_contacts:.2f}")
        col3.metric("Avg Days to Convert", f"{avg_days:.1f} days")
        col4.metric("% Zero-Touch Sales", f"{pct_zero_contact:.1f}%")
        
        # Row 2: Charts
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Contacts Required to Convert")
            # Group by contact count
            contact_dist = filtered_df['contact_count'].value_counts().reset_index()
            contact_dist.columns = ['Contacts', 'Count']
            contact_dist = contact_dist.sort_values('Contacts')
            
            fig_contacts = px.bar(
                contact_dist, x='Contacts', y='Count', 
                text='Count', 
                title="Distribution of Contacts per Sale",
                color='Count', color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_contacts, use_container_width=True)
            
        with c2:
            st.subheader("Conversion Speed (Days to Close)")
            fig_days = px.histogram(
                filtered_df, x='days_to_plan_close', nbins=20,
                title="Histogram: Days from First Contact to Sale",
                color_discrete_sequence=['green']
            )
            st.plotly_chart(fig_days, use_container_width=True)

        # Row 3: Time Series & Series Breakdown
        c3, c4 = st.columns(2)

        with c3:
            st.subheader("Sales Over Time")
            # Resample by week or day
            sales_over_time = filtered_df.set_index('plan_close_dt').resample('W').size().reset_index(name='Sales')
            fig_time = px.line(sales_over_time, x='plan_close_dt', y='Sales', title="Weekly Sales Volume", markers=True)
            st.plotly_chart(fig_time, use_container_width=True)

        with c4:
            st.subheader("Performance by Series")
            series_metrics = filtered_df.groupby('campaign_series').agg(
                Avg_Contacts=('contact_count', 'mean'),
                Sales=('customer_no', 'count')
            ).reset_index()
            
            fig_series = px.bar(
                series_metrics, x='campaign_series', y='Avg_Contacts',
                title="Avg Contacts by Series (Bar Height) & Volume (Color)",
                color='Sales', hover_data=['Sales']
            )
            st.plotly_chart(fig_series, use_container_width=True)

        # Raw Data View
        with st.expander("View Raw Data"):
            st.dataframe(filtered_df)

    except Exception as e:
        st.error(f"Error processing file. Please ensure the columns match the 2025/2026 format. Error: {e}")

else:
    st.info("👈 Please upload a CSV file from the sidebar to begin.")