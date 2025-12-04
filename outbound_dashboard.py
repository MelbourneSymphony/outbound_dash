import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(page_title="Campaign Year Comparison", layout="wide")

st.title("🎺🥁📯🎶 Outbound Campaign Comparison Dashboard")
st.markdown("### Performance across campaign years")

# --- Helper Function to Load & Clean Data ---
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    
# Extract just the date for daily aggregation
    df['close_date'] = df['plan_close_dt'].dt.date

    # Date Conversion
    df['plan_close_dt'] = pd.to_datetime(df['plan_close_dt'], errors='coerce')
    df['order_dt'] = pd.to_datetime(df['order_dt'], errors='coerce')
    
    # Map Contacts Count
    contact_map = {
        'TKT - To start': 0,
        'TKT - 1st contact complete': 1,
        'TKT - 2nd contact complete': 2,
        'TKT - 3rd contact complete': 3,
        'TKT - 4th contact complete': 4,
        'TKT - 5th contact complete': 5
    }
    df['contact_count'] = df['previous_step_at_closure'].map(contact_map).fillna(0)
    
    # Ensure campaign_year is treated as a string/category for plotting colors
    df['campaign_year'] = df['campaign_year'].astype(str)
    
    return df

# --- Sidebar: Data Upload & Filters ---
st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your campaign data (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load Data
        if uploaded_file.name.endswith('.csv'):
            df = load_data(uploaded_file)
        else:
            # Simple excel loader logic for demo
            df = pd.read_excel(uploaded_file)
            df['plan_close_dt'] = pd.to_datetime(df['plan_close_dt'], errors='coerce')
            df['order_dt'] = pd.to_datetime(df['order_dt'], errors='coerce')
            contact_map = {'TKT - To start': 0, 'TKT - 1st contact complete': 1, 
                           'TKT - 2nd contact complete': 2, 'TKT - 3rd contact complete': 3}
            df['contact_count'] = df['previous_step_at_closure'].map(contact_map).fillna(0)
            df['campaign_year'] = df['campaign_year'].astype(str)

        st.sidebar.header("2. Comparison Settings")
        
        # Filter: Campaign Year (Select at least 2 for good comparison)
        all_years = sorted(df['campaign_year'].unique())
        selected_years = st.sidebar.multiselect("Select Years to Compare", all_years, default=all_years)
        
        # Filter: Series
        all_series = sorted(df['campaign_series'].unique())
        selected_series = st.sidebar.multiselect("Filter by Series (Optional)", all_series, default=all_series)
        
        # Apply Filters
        filtered_df = df[
            (df['campaign_year'].isin(selected_years)) & 
            (df['campaign_series'].isin(selected_series))
        ]
        
        if len(filtered_df) == 0:
            st.warning("No data found for the selected filters.")
        else:
            # --- Main Dashboard Area ---

            # 1. Comparative KPI Table
            st.subheader("📊 Year-over-Year KPI Comparison")
            
            # Group by year to get summary stats
            kpi_df = filtered_df.groupby('campaign_year').agg(
                Total_Sales=('customer_no', 'count'),
                Avg_Contacts=('contact_count', 'mean'),
                Avg_Days_to_Close=('days_to_plan_close', 'mean'),
                Median_Days_to_Close=('days_to_plan_close', 'median')
            )
            
            # Calculate % Zero Touch (Sales with 0 contacts)
            zero_touch = filtered_df[filtered_df['contact_count'] == 0].groupby('campaign_year')['customer_no'].count()
            kpi_df['Zero_Touch_Count'] = zero_touch
            kpi_df['%_Zero_Touch'] = (kpi_df['Zero_Touch_Count'] / kpi_df['Total_Sales'] * 100).fillna(0)

            # Format for display
            display_kpi = kpi_df[['Total_Sales', 'Avg_Contacts', 'Avg_Days_to_Close', '%_Zero_Touch']].reset_index()
            display_kpi = display_kpi.rename(columns={
                'campaign_year': 'Year',
                'Total_Sales': 'Total Sales', 
                'Avg_Contacts': 'Avg Contacts', 
                'Avg_Days_to_Close': 'Avg Days to Close',
                '%_Zero_Touch': '% Zero-Touch Sales'
            })
            
            # Show as a styled table
            st.dataframe(
                display_kpi.style.format({
                    'Avg Contacts': '{:.2f}',
                    'Avg Days to Close': '{:.1f}',
                    '% Zero-Touch Sales': '{:.1f}%'
                }), 
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")
            st.subheader("📈 Sales per Day")
            
            # Prepare Daily Aggregation
            daily_sales = filtered_df.groupby(['campaign_year', 'plan_close_dt']).size().reset_index(name='daily_sales')
            daily_sales['plan_close_dt'] = pd.to_datetime(daily_sales['plan_close_dt'])
            
            # Sort for cumulative sum
            daily_sales = daily_sales.sort_values(['campaign_year', 'plan_close_dt'])
            daily_sales['cumulative_sales'] = daily_sales.groupby('campaign_year')['daily_sales'].cumsum()

            # Comparison Toggle
            col_toggle, _ = st.columns([1, 3])
            with col_toggle:
                align_dates = st.checkbox("Align Dates for Overlay Comparison", value=False, 
                                          help="Overlays different years on a shared timeline (Month-Day) to compare seasonality.")

            if align_dates:
                # Create a dummy year (e.g., 2020) to overlay plots
                # Logic: Keep Month/Day, replace Year. Handle Leap years if needed (ignoring for simplicity)
                daily_sales['plot_date'] = daily_sales['plan_close_dt'].apply(lambda x: x.replace(year=2020))
                x_axis_col = 'plot_date'
                x_label = 'Date (Month-Day)'
                title_suffix = "(Aligned by Month-Day)"
            else:
                x_axis_col = 'close_date'
                x_label = 'Date'
                title_suffix = "(Actual Dates)"

            tab1, tab2 = st.tabs(["Daily Volume", "Cumulative Performance"])

            with tab1:
                fig_daily = px.line(
                    daily_sales, 
                    x=x_axis_col, 
                    y='daily_sales', 
                    color='campaign_year',
                    markers=True,
                    title=f"Total Sales per Day {title_suffix}",
                    labels={x_axis_col: x_label, 'daily_sales': 'Number of Sales', 'campaign_year': 'Year'}
                )
                if align_dates:
                    fig_daily.update_xaxes(tickformat="%b %d") # Format as Month-Day
                st.plotly_chart(fig_daily, use_container_width=True)
                
            with tab2:
                fig_cum = px.line(
                    daily_sales, 
                    x=x_axis_col, 
                    y='cumulative_sales', 
                    color='campaign_year',
                    title=f"Cumulative Sales Progression {title_suffix}",
                    labels={x_axis_col: x_label, 'cumulative_sales': 'Total Sales to Date', 'campaign_year': 'Year'}
                )
                if align_dates:
                    fig_cum.update_xaxes(tickformat="%b %d")
                st.plotly_chart(fig_cum, use_container_width=True)





            # 2. Charts Row
            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Contacts Distribution by Year")
                # Prepare data for grouped bar chart
                contact_counts = filtered_df.groupby(['campaign_year', 'contact_count']).size().reset_index(name='count')
                
                # Calculate percentages within each year for fairer comparison
                contact_counts['percentage'] = contact_counts.groupby('campaign_year')['count'].transform(lambda x: x / x.sum() * 100)
                
                fig_contacts = px.bar(
                    contact_counts, 
                    x='contact_count', 
                    y='percentage', 
                    color='campaign_year',
                    barmode='group',
                    title="Distribution of Contacts (Percentage of Year's Sales)",
                    labels={'contact_count': 'Number of Contacts', 'percentage': '% of Sales'},
                    text_auto='.1f'
                )
                fig_contacts.update_layout(xaxis=dict(tickmode='linear', dtick=1))
                st.plotly_chart(fig_contacts, use_container_width=True)

            with col2:
                st.subheader("Speed of Conversion by Year")
                # Box plot is excellent for comparing distributions
                fig_box = px.box(
                    filtered_df, 
                    x='campaign_year', 
                    y='days_to_plan_close', 
                    color='campaign_year',
                    title="Days to Close Distribution (Box Plot)",
                    labels={'days_to_plan_close': 'Days', 'campaign_year': 'Year'}
                )
                st.plotly_chart(fig_box, use_container_width=True)

            # 3. Series Performance Comparison
            st.markdown("---")
            st.subheader("Series Performance: Year vs Year")
            
            # Pivot data to compare series side-by-side
            series_stats = filtered_df.groupby(['campaign_series', 'campaign_year'])['contact_count'].mean().reset_index()
            
            fig_series = px.bar(
                series_stats,
                x='campaign_series',
                y='contact_count',
                color='campaign_year',
                barmode='group',
                title="Average Contacts per Series by Year",
                labels={'contact_count': 'Avg Contacts Needed', 'campaign_series': 'Series'}
            )
            st.plotly_chart(fig_series, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("👈 Upload your data file to start the comparison.")