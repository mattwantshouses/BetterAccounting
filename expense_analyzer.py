import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, List
from io import StringIO
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

# =============================================================================
# Plaid API Configuration
# =============================================================================

# Set up the Plaid client with your API credentials
# Note: In a production environment, these should be stored securely (e.g., environment variables)
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': 'YOUR_CLIENT_ID',
        'secret': 'YOUR_SECRET',
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# =============================================================================
# Data Processing Functions
# =============================================================================

def standardize_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize the CSV data format across different bank exports.
    
    Args:
        df (pd.DataFrame): The input DataFrame containing bank transaction data.
    
    Returns:
        pd.DataFrame: Standardized DataFrame with consistent column names and data types.
    """
    if 'Transaction ID' in df.columns:  # VyStar format
        df['Date'] = pd.to_datetime(df['PostingDate'])
        df['Amount'] = df['Amount'].astype(float)
        df['Description'] = df['Description']
        df['Category'] = df['Category']
        df['Running Bal.'] = df['RunningBalance']
    elif 'Summary Amt.' in df.columns:  # Bank of America format
        df = df[df['Date'].notna()]  # Remove summary rows
        df['Date'] = pd.to_datetime(df['Date'])
        df['Amount'] = df['Amount'].str.replace('"', '').astype(float)
        df['Description'] = df['Description'].str.replace('"', '')
        df['Running Bal.'] = df['Running Bal.'].str.replace('"', '').astype(float)
        df['Category'] = 'Uncategorized'  # BoA doesn't provide categories
    else:
        raise ValueError("Unsupported CSV format")
    
    return df[['Date', 'Description', 'Amount', 'Category', 'Running Bal.']]

def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Categorize transactions using the Plaid API.
    
    Args:
        df (pd.DataFrame): The input DataFrame containing standardized transaction data.
    
    Returns:
        pd.DataFrame: DataFrame with categorized transactions.
    """
    # Note: You'd need to implement the Plaid authentication flow to get this access token
    access_token = "YOUR_ACCESS_TOKEN"
    
    request = TransactionsGetRequest(
        access_token=access_token,
        start_date=df['Date'].min().strftime('%Y-%m-%d'),
        end_date=df['Date'].max().strftime('%Y-%m-%d'),
        options=TransactionsGetRequestOptions(
            include_personal_finance_category=True
        )
    )
    response = client.transactions_get(request)
    
    # Create a dictionary mapping transaction descriptions to categories
    categorization = {transaction.name: transaction.personal_finance_category.primary 
                      for transaction in response['transactions']}
    
    # Apply the categorization to our DataFrame
    df['Category'] = df['Description'].map(categorization).fillna('Uncategorized')
    
    return df

def load_and_categorize_csv(uploaded_file: st.UploadedFile) -> pd.DataFrame:
    """
    Load a CSV file, standardize its format, and categorize the transactions.
    
    Args:
        uploaded_file (st.UploadedFile): The uploaded CSV file.
    
    Returns:
        pd.DataFrame: Processed and categorized DataFrame.
    """
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        df = standardize_csv(df)
        df = categorize_transactions(df)
        return df
    except Exception as e:
        st.error(f"Error processing CSV: {str(e)}")
        return pd.DataFrame()

# =============================================================================
# Analysis Functions
# =============================================================================

def analyze_business(df: pd.DataFrame, business_name: str) -> float:
    """
    Analyze business finances and display results.
    
    Args:
        df (pd.DataFrame): The DataFrame containing business transaction data.
        business_name (str): The name of the business being analyzed.
    
    Returns:
        float: The calculated profit/loss for the business.
    """
    st.subheader(f"Analysis for {business_name}")
    
    # Calculate financial metrics
    total_income = df[df['Amount'] > 0]['Amount'].sum()
    total_expenses = abs(df[df['Amount'] < 0]['Amount'].sum())
    profit_loss = total_income - total_expenses
    
    # Display financial metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${total_income:.2f}")
    col2.metric("Total Expenses", f"${total_expenses:.2f}")
    col3.metric("Profit/Loss", f"${profit_loss:.2f}")
    
    # Create and display pie chart for expenses by category
    expenses_by_category = df[df['Amount'] < 0].groupby('Category')['Amount'].sum().abs()
    fig = px.pie(values=expenses_by_category.values, names=expenses_by_category.index, 
                 title='Expenses by Category')
    st.plotly_chart(fig)
    
    # Create and display line chart for transactions over time
    daily_totals = df.groupby('Date')['Amount'].sum().reset_index()
    fig = px.line(daily_totals, x='Date', y='Amount', title='Transactions Over Time')
    st.plotly_chart(fig)
    
    return profit_loss

def analyze_personal_finances(personal_data: pd.DataFrame, business_profits: Dict[str, float]):
    """
    Analyze personal finances and display results.
    
    Args:
        personal_data (pd.DataFrame): The DataFrame containing personal transaction data.
        business_profits (Dict[str, float]): A dictionary of business names and their profits/losses.
    """
    st.subheader("Personal Finance Analysis")
    
    # Display current account balance
    st.metric("Account Balance", f"${personal_data['Running Bal.'].iloc[-1]:.2f}")
    
    # Display business pass-through profits/losses
    if business_profits:
        st.subheader("Business Pass-through")
        for business, profit in business_profits.items():
            st.metric(f"{business} Profit/Loss", f"${profit:.2f}")
    
    # Create and display pie chart for personal expenses by category
    personal_expenses = personal_data[personal_data['Amount'] < 0]
    expenses_by_category = personal_expenses.groupby('Category')['Amount'].sum().abs()
    fig = px.pie(values=expenses_by_category.values, names=expenses_by_category.index, 
                 title='Personal Expenses by Category')
    st.plotly_chart(fig)

# =============================================================================
# Report Generation Functions
# =============================================================================

def generate_report(df: pd.DataFrame) -> str:
    """
    Generate a CSV report from a DataFrame.
    
    Args:
        df (pd.DataFrame): The DataFrame to be converted to a CSV report.
    
    Returns:
        str: CSV-formatted string of the report.
    """
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

# =============================================================================
# Main Application
# =============================================================================

def main():
    st.title('Enhanced Finance Analyzer')
    
    # File uploader for multiple CSV files
    uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type="csv")
    
    if uploaded_files:
        all_data: Dict[str, pd.DataFrame] = {}
        personal_data = pd.DataFrame()
        business_profits: Dict[str, float] = {}
        
        # Process each uploaded file
        for uploaded_file in uploaded_files:
            df = load_and_categorize_csv(uploaded_file)
            if df.empty:
                continue
            
            # Let user categorize the file as personal or business
            category = st.selectbox(f"Categorize {uploaded_file.name}", ["Personal", "Business"])
            
            if category == "Personal":
                personal_data = pd.concat([personal_data, df], ignore_index=True)
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
            analyze_personal_finances(personal_data, business_profits)
        
        # Generate and offer download of complete financial report
        if st.button("Generate Complete Financial Report"):
            all_transactions = pd.concat([personal_data] + list(all_data.values()), ignore_index=True)
            report_csv = generate_report(all_transactions)
            st.download_button(
                label="Download Complete Financial Report",
                data=report_csv,
                file_name="complete_financial_report.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()