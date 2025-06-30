import requests
import csv
import time
from typing import Dict, List
import json
import os
from config import ACCESS_TOKEN

# API Configuration
BASE_URL = "https://foodapi.calorieking.com/v1"
HEADERS = {
    'Accept': 'application/json'
}

def get_foods(offset: int = 0, limit: int = 10) -> Dict:
    """Fetch a page of foods from the API."""
    url = f"{BASE_URL}/foods"
    params = {
        'offset': offset,
        'limit': limit
    }
    response = requests.get(
        url,
        auth=(ACCESS_TOKEN, ''),
        headers=HEADERS,
        params=params
    )
    return response.json()

def get_food_details(revision_id: str) -> Dict:
    """Fetch detailed information for a specific food."""
    url = f"{BASE_URL}/foods/{revision_id}"
    response = requests.get(
        url,
        auth=(ACCESS_TOKEN, ''),
        headers=HEADERS
    )
    return response.json()

def save_to_csv(foods_data: List[Dict], filename: str = '../data/calorie_king_data.csv'):
    """Save the collected data to a CSV file."""
    if not foods_data:
        print("No data to save!")
        return

    # Ensure the data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Define the fields we want to save
    fieldnames = [
        'name', 'brand_name', 'classification',
        'energy', 'fat', 'netCarbs', 'protein', 'sugar',
        'fiber', 'calcium', 'sodium', 'satFat', 'transFat',
        'polyUnsatFat', 'monoUnsatFat', 'omega3Fat',
        'cholesterol', 'alcohol', 'potassium', 'iron', 'vitaminC'
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for food in foods_data:
            try:
                row = {
                    'name': food.get('name', ''),
                    'brand_name': food.get('brand', {}).get('name', ''),
                    'classification': food.get('classification', ''),
                }
                
                # Add nutrients if they exist
                nutrients = food.get('nutrients', {})
                for field in fieldnames[3:]:  # Skip the first 3 fields which are not nutrients
                    row[field] = nutrients.get(field, '')
                
                writer.writerow(row)
            except Exception as e:
                print(f"Error writing row for {food.get('name', 'unknown')}: {str(e)}")

def main():
    all_foods_data = []
    offset = 0
    limit = 10
    total_processed = 0
    max_items = 10

    print("Starting data collection from CalorieKing API...")

    try:
        # Get the first page to determine total number of foods
        initial_response = get_foods(offset, limit)
        total_foods = min(max_items, initial_response['metadata']['total'])
        
        while offset < total_foods:
            print(f"Fetching foods {offset + 1} to {min(offset + limit, total_foods)} of {total_foods}...")
            
            # Get the list of foods
            foods_response = get_foods(offset, limit)
            
            # Get detailed information for each food
            for food in foods_response['foods']:
                if total_processed >= max_items:
                    break
                    
                try:
                    food_details = get_food_details(food['revisionId'])
                    if 'food' in food_details:
                        all_foods_data.append(food_details['food'])
                        total_processed += 1
                        print(f"Processed {food['name']}")
                    
                    # Add a small delay to avoid overwhelming the API
                    time.sleep(0.5)
                
                except Exception as e:
                    print(f"Error processing food {food.get('name', 'unknown')}: {str(e)}")
            
            if total_processed >= max_items:
                break
                
            offset += limit

        # Save final results
        save_to_csv(all_foods_data)
        print(f"\nData collection completed! Total foods processed: {total_processed}")
        print("Data saved to '../data/calorie_king_data.csv'")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Save whatever data we collected before the error
        if all_foods_data:
            save_to_csv(all_foods_data, '../data/calorie_king_data_error.csv')
            print("Partial data saved to '../data/calorie_king_data_error.csv'")

if __name__ == "__main__":
    main() 