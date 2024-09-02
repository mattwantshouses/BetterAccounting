import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO

def load_csv(uploaded_file):
    return pd.read_csv(uploaded_file)

def analyze_business(df, business_name):
    st.subheader(f"Analysis for {business_name}")
    
    # Calculate total income and expenses
    total_income = df[df['Amount'] > 0]['Amount'].sum()
    total_expenses = abs(df[df['Amount'] < 0]['Amount'].sum())
    profit_loss = total_income - total_expenses
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${total_income:.2f}")
    col2.metric("Total Expenses", f"${total_expenses:.2f}")
    col3.metric("Profit/Loss", f"${profit_loss:.2f}")
    
    # Expenses by category
    expenses_by_category = df[df['Amount'] < 0].groupby('Category')['Amount'].sum().abs()
    fig = px.pie(values=expenses_by_category.values, names=expenses_by_category.index, title='Expenses by Category')
    st.plotly_chart(fig)
    
    # Transactions over time
    df['Date'] = pd.to_datetime(df['Date'])
    daily_totals = df.groupby('Date')['Amount'].sum().reset_index()
    fig = px.line(daily_totals, x='Date', y='Amount', title='Transactions Over Time')
    st.plotly_chart(fig)
    
    return profit_loss

def main():
    st.title('Advanced Finance Analyzer')
    
    # File uploader for multiple CSV files
    uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type="csv")
    
    if uploaded_files:
        all_data = {}
        personal_data = pd.DataFrame()
        business_profits = {}
        
        for uploaded_file in uploaded_files:
            df = load_csv(uploaded_file)
            
            # Ask user to categorize the file
            category = st.selectbox(f"Categorize {uploaded_file.name}", ["Personal", "Business"])
            
            if category == "Personal":
                personal_data = pd.concat([personal_data, df])
            else:
                business_name = st.text_input(f"Enter business name for {uploaded_file.name}")
                if business_name:
                    all_data[business_name] = df
        
        # Analyze each business
        for business_name, df in all_data.items():
            profit_loss = analyze_business(df, business_name)
            business_profits[business_name] = profit_loss
        
        # Analyze personal finances
        if not personal_data.empty:
            st.subheader("Personal Finance Analysis")
            
            # Separate checking and savings
            checking = personal_data[personal_data['Account Type'] == 'Checking']
            savings = personal_data[personal_data['Account Type'] == 'Savings']
            
            # Display account balances
            col1, col2 = st.columns(2)
            col1.metric("Checking Balance", f"${checking['Amount'].sum():.2f}")
            col2.metric("Savings Balance", f"${savings['Amount'].sum():.2f}")
            
            # Pass-through from businesses
            if business_profits:
                st.subheader("Business Pass-through")
                for business, profit in business_profits.items():
                    st.metric(f"{business} Profit/Loss", f"${profit:.2f}")
            
            # Personal expenses by category
            personal_expenses = personal_data[personal_data['Amount'] < 0]
            expenses_by_category = personal_expenses.groupby('Category')['Amount'].sum().abs()
            fig = px.pie(values=expenses_by_category.values, names=expenses_by_category.index, title='Personal Expenses by Category')
            st.plotly_chart(fig)

if __name__ == "__main__":
    main()