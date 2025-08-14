#!/usr/bin/env python3
"""
Simple search tool for USDA carbohydrate data.
Usage: python3 search_carbs.py "apple" or python3 search_carbs.py "chicken breast"
"""

import pandas as pd
import sys
from pathlib import Path

def load_carb_data():
    """Load the most recent carb data file."""
    data_dir = Path("data")
    carb_files = list(data_dir.glob("usda_carbs_*.csv"))
    
    if not carb_files:
        print("❌ No carb data files found. Run extract_carbs_only.py first.")
        return None
    
    # Use the most recent file
    latest_file = max(carb_files, key=lambda f: f.stat().st_mtime)
    print(f"📊 Loading: {latest_file}")
    
    return pd.read_csv(latest_file)

def search_foods(query, data, max_results=10):
    """Search for foods containing the query."""
    query_lower = query.lower()
    
    # Search in food names
    matches = data[data['food_name'].str.lower().str.contains(query_lower, na=False)]
    
    # Sort by name length (shorter names first, usually more relevant)
    matches = matches.copy()
    matches['name_length'] = matches['food_name'].str.len()
    matches = matches.sort_values(['name_length', 'food_name'])
    
    return matches.head(max_results)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 search_carbs.py \"search term\"")
        print("Example: python3 search_carbs.py \"apple\"")
        return 1
    
    query = sys.argv[1]
    
    # Load data
    data = load_carb_data()
    if data is None:
        return 1
    
    print(f"🔍 Searching for: '{query}'")
    print(f"📈 Database: {len(data):,} foods with carb data")
    print("=" * 80)
    
    # Search
    results = search_foods(query, data)
    
    if len(results) == 0:
        print(f"❌ No foods found containing '{query}'")
        return 0
    
    print(f"Found {len(results)} result(s):\n")
    
    # Display results
    for i, (_, food) in enumerate(results.iterrows(), 1):
        name = food['food_name']
        carbs = food['carbohydrates_g']
        serving = food['serving_size']
        
        print(f"{i:2d}. {name}")
        print(f"    Carbohydrates: {carbs}g per {serving}")
        print()
    
    return 0

if __name__ == "__main__":
    exit(main())
