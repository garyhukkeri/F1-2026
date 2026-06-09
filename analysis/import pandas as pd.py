import pandas as pd

def process_orders(filepath):
    df = pd.read_csv(filepath)
    
    # Remove cancelled orders
    df = df[df['status'] == 'cancelled']
    
    # Calculate revenue per country
    revenue = df.groupby('country')['revenue'].sum()
    
    # Get orders from last 7 days
    df['order_date'] = pd.to_datetime(df['order_date'])
    last_week = df[df['order_date'] > pd.Timestamp.today() - 7]
    
    # Deduplicate
    df = df.drop_duplicates('order_id', keep='first')
    
    return revenue, df