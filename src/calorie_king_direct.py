#!/usr/bin/env python3
"""
CalorieKing Direct Query System
Single file solution for querying CalorieKing API directly for nutrition information.
"""

import requests
import time
import csv
import pandas as pd
import os
import sys
import re
from typing import Dict, List, Optional, Any, Set
from config import ACCESS_TOKEN

class CalorieKingDirect:
    """Complete CalorieKing direct querying system."""
    
    def __init__(self):
        """Initialize with CalorieKing API configuration."""
        self.base_url = "https://foodapi.calorieking.com/v1"
        self.headers = {'Accept': 'application/json'}
        
        # Read access token from environment variable
        self.access_token = os.getenv('CALORIEKING_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("CALORIEKING_ACCESS_TOKEN environment variable not set. Please set it with your CalorieKing API token.")
        
        # Food taxonomy for better matching
        self.food_types = {
            'fish': {'salmon', 'tuna', 'cod', 'halibut', 'mackerel', 'trout', 'bass', 'sardine', 'anchovy', 'flounder', 'sole', 'tilapia', 'mahi', 'snapper', 'grouper'},
            'meat': {'chicken', 'beef', 'pork', 'turkey', 'lamb', 'duck', 'ham', 'bacon', 'sausage', 'steak', 'ground beef', 'ground turkey'},
            'dairy': {'milk', 'cheese', 'yogurt', 'butter', 'cream', 'cottage cheese', 'mozzarella', 'cheddar', 'swiss'},
            'vegetables': {'broccoli', 'spinach', 'carrot', 'tomato', 'lettuce', 'onion', 'pepper', 'corn', 'peas', 'beans'},
            'fruits': {'apple', 'banana', 'orange', 'grape', 'strawberry', 'blueberry', 'peach', 'pear', 'cherry'},
            'grains': {'rice', 'bread', 'pasta', 'oats', 'quinoa', 'barley', 'wheat', 'cereal'},
            'nuts': {'almond', 'walnut', 'peanut', 'cashew', 'pecan', 'pistachio'},
            'beverages': {'juice', 'soda', 'beer', 'wine', 'coffee', 'tea', 'water', 'smoothie'},
            'desserts': {'cake', 'cookie', 'ice cream', 'chocolate', 'candy', 'pie', 'donut'}
        }
        
        self.cooking_methods = {'baked', 'grilled', 'fried', 'roasted', 'steamed', 'boiled', 'raw', 'broiled', 'sauteed', 'smoked'}
        
        # Measurement words to ignore in matching
        self.measurement_words = {'oz', 'ounce', 'ounces', 'lb', 'pound', 'pounds', 'cup', 'cups', 'tbsp', 'tsp', 'gram', 'grams', 'kg', 'serving', 'piece', 'slice', 'medium', 'large', 'small', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'}
    
    def query_food(self, food_name: str, max_results: int = 1) -> List[Dict[str, Any]]:
        """
        Query nutrition information for a food item by name.
        
        Args:
            food_name (str): Name of the food to search for
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of foods with complete nutrition information
        """
        print(f"🔍 Searching for '{food_name}'...")
        
        # Search for matching foods
        search_results = self._search_foods(food_name, max_results)
        
        if not search_results:
            print(f"❌ No foods found matching '{food_name}'")
            return []
        
        print(f"🔎 Found {len(search_results)} potential matches, getting details...")
        
        # Get detailed nutrition information for each result
        detailed_results = []
        for food in search_results:
            revision_id = food.get('revisionId')
            if revision_id:
                print(f"  📋 Getting details for: {food.get('name', 'Unknown')} (score: {food.get('relevance_score', 0):.3f})")
                details = self._get_food_details(revision_id)
                if details and 'food' in details:
                    food_data = details['food']
                    food_data['relevance_score'] = food.get('relevance_score', 0)
                    detailed_results.append(food_data)
                    
                    # Debug: show what we got
                    carbs = food_data.get('netCarbs', 'Missing')
                    print(f"    ✅ Got nutrition data - Carbs: {carbs}")
                else:
                    print(f"    ❌ No detailed nutrition data")
                time.sleep(0.1)  # Rate limiting
        
        return detailed_results
    
    def _extract_keywords(self, query: str) -> Dict[str, Set[str]]:
        """Extract meaningful keywords from the search query."""
        query_lower = query.lower()
        
        # Remove measurements and common words
        words = re.findall(r'\b\w+\b', query_lower)
        meaningful_words = [w for w in words if w not in self.measurement_words and len(w) > 2]
        
        # Identify food types
        food_types = set()
        for category, foods in self.food_types.items():
            for food in foods:
                if any(food in word or word in food for word in meaningful_words):
                    food_types.add(category)
        
        # Identify cooking methods
        cooking_methods = {method for method in self.cooking_methods if method in query_lower}
        
        # Main food keywords (excluding cooking methods)
        main_keywords = set(meaningful_words) - cooking_methods
        
        return {
            'main_keywords': main_keywords,
            'food_types': food_types,
            'cooking_methods': cooking_methods,
            'all_words': set(meaningful_words)
        }
    
    def _search_foods(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for foods by name using the CalorieKing API."""
        try:
            query_keywords = self._extract_keywords(query)
            matches = []
            offset = 0
            page_limit = 50
            total_checked = 0
            max_to_check = 1000  # Increased search scope
            
            print(f"🔍 Searching CalorieKing database for '{query}'...")
            print(f"📝 Keywords: {query_keywords['main_keywords']}")
            print(f"🍽️  Food types: {query_keywords['food_types']}")
            print(f"👨‍🍳 Cooking methods: {query_keywords['cooking_methods']}")
            
            while len(matches) < limit and total_checked < max_to_check:
                try:
                    # Get a page of foods
                    foods_response = self._get_foods_page(offset, page_limit)
                    
                    if not foods_response or 'foods' not in foods_response:
                        break
                        
                    foods = foods_response['foods']
                    if not foods:
                        break
                    
                    # Filter foods that match our query
                    for food in foods:
                        total_checked += 1
                        food_name = food.get('name', '').lower()
                        
                        # Calculate relevance score with detailed breakdown
                        score, score_breakdown = self._calculate_relevance_detailed(query_keywords, food_name, food)
                        
                        if score > 0.6:  # Much higher threshold
                            food_with_score = food.copy()
                            food_with_score['relevance_score'] = score
                            food_with_score['score_breakdown'] = score_breakdown
                            matches.append(food_with_score)
                            print(f"  📝 Match: {food.get('name', 'Unknown')} (score: {score:.3f})")
                            print(f"      💡 {score_breakdown}")
                            
                            if len(matches) >= limit:
                                break
                    
                    offset += page_limit
                    time.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    print(f"Error fetching foods page at offset {offset}: {str(e)}")
                    break
            
            # Sort by relevance score
            matches.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            print(f"📊 Found {len(matches)} matches after checking {total_checked} foods")
            return matches[:limit]
            
        except Exception as e:
            print(f"Error searching for '{query}': {str(e)}")
            return []
    
    def _get_foods_page(self, offset: int, limit: int) -> Dict:
        """Fetch a page of foods from the API."""
        url = f"{self.base_url}/foods"
        params = {'offset': offset, 'limit': limit}
        response = requests.get(
            url,
            auth=(self.access_token, ''),
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def _get_food_details(self, revision_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed nutrition information for a specific food."""
        try:
            url = f"{self.base_url}/foods/{revision_id}"
            response = requests.get(
                url,
                auth=(self.access_token, ''),
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Debug: show the structure of what we got
            if 'food' in result:
                food_data = result['food']
                print(f"    🔍 API returned food: {food_data.get('name', 'No name')}")
                print(f"    🔍 Available keys: {list(food_data.keys())}")
                if 'nutrients' in food_data:
                    nutrients = food_data['nutrients']
                    print(f"    🔍 Nutrients keys: {list(nutrients.keys())}")
            
            return result
        except Exception as e:
            print(f"Error getting food details for {revision_id}: {str(e)}")
            return None
    
    def _calculate_relevance_detailed(self, query_keywords: Dict[str, Set[str]], food_name: str, food_data: Dict) -> tuple[float, str]:
        """Calculate relevance score with detailed breakdown for debugging."""
        score = 0
        breakdown_parts = []
        
        food_name_words = set(re.findall(r'\b\w+\b', food_name.lower()))
        
        # 1. EXACT keyword match with specificity bonus
        exact_match_score = 0
        specificity_bonus = 0

        for keyword in query_keywords['main_keywords']:
            if keyword in food_name:
                exact_match_score = 1.0
                
                # Add specificity bonus for better matches
                food_words = food_name.split()
                
                # Bonus for exact word match (not just substring)
                if keyword in food_words:
                    specificity_bonus += 0.2
                    
                # Bonus for fewer additional descriptors (simpler = better)
                if len(food_words) <= 3:
                    specificity_bonus += 0.1
                    
                # Penalty for processed/prepared versions when searching for basic food
                if any(prep in food_name for prep in ['fried', 'battered', 'takeaway', 'block']):
                    if not any(prep in query_keywords['all_words'] for prep in ['fried', 'battered', 'takeaway']):
                        specificity_bonus -= 0.3
                        
                breakdown_parts.append(f"exact_match:{exact_match_score:.2f}+specificity:{specificity_bonus:.2f}")
                break

        score += exact_match_score + specificity_bonus
        
        # 2. Only use category matching as fallback with lower score (0.3)
        food_category_score = 0
        if exact_match_score == 0:  # Only if no exact match found
            for category in query_keywords['food_types']:
                category_foods = self.food_types[category]
                if any(food in food_name for food in category_foods):
                    food_category_score = 0.3  # Much lower than exact match
                    breakdown_parts.append(f"category_fallback:{food_category_score:.2f}")
                    break
        score += food_category_score
        
        # 3. Cooking method matches
        cooking_score = 0
        for method in query_keywords['cooking_methods']:
            if method in food_name:
                cooking_score = 0.3
                breakdown_parts.append(f"cooking:{cooking_score:.2f}")
                break
        score += cooking_score
        
        # 4. Partial word matches (only if no exact match)
        partial_score = 0
        if exact_match_score == 0:
            partial_matches = 0
            for query_word in query_keywords['all_words']:
                for food_word in food_name_words:
                    if len(query_word) > 3 and (query_word in food_word or food_word in query_word):
                        partial_matches += 1
            if partial_matches > 0:
                partial_score = min(partial_matches * 0.1, 0.2)
                breakdown_parts.append(f"partial:{partial_score:.2f}")
        score += partial_score
        
        # 5. NEGATIVE SCORING - Penalize wrong categories
        penalty = 0
        
        # If searching for fish/meat, heavily penalize beverages, desserts
        if query_keywords['food_types'].intersection({'fish', 'meat'}):
            if any(beverage in food_name for beverage in self.food_types['beverages']):
                penalty = 0.8
                breakdown_parts.append(f"penalty_beverage:-{penalty:.2f}")
            elif any(dessert in food_name for dessert in self.food_types['desserts']):
                penalty = 0.7
                breakdown_parts.append(f"penalty_dessert:-{penalty:.2f}")
        
        # If searching for non-alcoholic, penalize alcohol
        if 'beer' in food_name or 'wine' in food_name or 'alcohol' in food_name:
            if not any(alcohol_word in query_keywords['all_words'] for alcohol_word in ['beer', 'wine', 'alcohol']):
                penalty = 0.9
                breakdown_parts.append(f"penalty_alcohol:-{penalty:.2f}")
        
        score = max(0, score - penalty)
        
        breakdown = " | ".join(breakdown_parts) if breakdown_parts else "no_matches"
        return score, breakdown
    
    def _calculate_relevance(self, query: str, food_name: str) -> float:
        """Legacy method kept for compatibility - now uses the detailed version."""
        query_keywords = self._extract_keywords(query)
        score, _ = self._calculate_relevance_detailed(query_keywords, food_name, {})
        return score
    
    def print_nutrition_info(self, food_name: str, max_results: int = 1):
        """Print formatted nutrition information for a food search."""
        results = self.query_food(food_name, max_results)
        
        if not results:
            print(f"❌ No results found for '{food_name}'")
            return
        
        print(f"\n📊 Nutrition information for '{food_name}':")
        print("=" * 60)
        
        # Show only the best match
        food = results[0]
        # Try different possible keys for nutrition data
        carbs = food.get('netCarbs', food.get('carbohydrates', 0))
        protein = food.get('protein', 0)
        fat = food.get('fat', 0)
        energy = food.get('energy', 0)
        
        # If nutrients are nested, try to get them
        if carbs == 0 and 'nutrients' in food:
            nutrients = food['nutrients']
            carbs = nutrients.get('netCarbs', nutrients.get('carbohydrates', 0))
            protein = nutrients.get('protein', 0)
            fat = nutrients.get('fat', 0)
            energy = nutrients.get('energy', 0)
        
        print(f"\n{food.get('name', 'Unknown')}")
        if food.get('brandName'):
            print(f"Brand: {food['brandName']}")
        print(f"Relevance: {food.get('relevance_score', 0):.2f}")
        print(f"🥕 Carbs: {carbs}g")
        print(f"🥩 Protein: {protein}g")
        print(f"🥑 Fat: {fat}g")
        if energy > 0:
            print(f"⚡ Energy: {energy} kJ")
    
    def get_best_match(self, food_name: str) -> Dict[str, Any]:
        """Get the best matching nutrition information for a food."""
        results = self.query_food(food_name, max_results=1)
        
        if results:
            best_match = results[0]
            
            # Try different possible keys for nutrition data
            carbs = best_match.get('netCarbs', best_match.get('carbohydrates', 0))
            protein = best_match.get('protein', 0)
            fat = best_match.get('fat', 0)
            energy = best_match.get('energy', 0)
            
            # If nutrients are nested, try to get them
            if carbs == 0 and 'nutrients' in best_match:
                nutrients = best_match['nutrients']
                carbs = nutrients.get('netCarbs', nutrients.get('carbohydrates', 0))
                protein = nutrients.get('protein', 0)
                fat = nutrients.get('fat', 0)
                energy = nutrients.get('energy', 0)
            
            return {
                "food_name": best_match.get('name', ''),
                "carbs": carbs,
                "protein": protein,
                "fat": fat,
                "energy": energy,
                "confidence": best_match.get('relevance_score', 0),
                "brand": best_match.get('brandName', ''),
            }
        
        return {}
    
    def process_csv(self, input_csv: str, output_csv: str, item_column: str = 'Item') -> bool:
        """
        Process a CSV file and add CalorieKing nutrition data.
        
        Args:
            input_csv (str): Path to input CSV file
            output_csv (str): Path to output CSV file
            item_column (str): Column name containing food items
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"📄 Processing CSV: {input_csv}")
            
            # Load the CSV
            df = pd.read_csv(input_csv)
            
            if item_column not in df.columns:
                print(f"❌ Column '{item_column}' not found. Available: {list(df.columns)}")
                return False
            
            # Get unique food items
            unique_items = df[item_column].dropna().unique()
            print(f"📋 Processing {len(unique_items)} unique food items...")
            
            # Query nutrition data for each unique item
            nutrition_cache = {}
            for i, food_item in enumerate(unique_items, 1):
                print(f"\n[{i}/{len(unique_items)}] Querying: {food_item}")
                
                best_match = self.get_best_match(food_item)
                
                if best_match and best_match['carbs'] > 0:
                    nutrition_cache[food_item] = {
                        'ck_name': best_match['food_name'],
                        'ck_brand': best_match['brand'],
                        'ck_carbs': best_match['carbs'],
                        'ck_protein': best_match['protein'],
                        'ck_fat': best_match['fat'],
                        'ck_energy': best_match['energy'],
                        'ck_confidence': best_match['confidence']
                    }
                    print(f"  ✅ Found: {best_match['food_name']} - {best_match['carbs']}g carbs")
                else:
                    nutrition_cache[food_item] = {
                        'ck_name': '', 'ck_brand': '', 'ck_carbs': 0,
                        'ck_protein': 0, 'ck_fat': 0, 'ck_energy': 0, 'ck_confidence': 0
                    }
                    print(f"  ❌ No results found")
                
                time.sleep(0.3)  # Rate limiting
            
            # Add nutrition data to dataframe
            for col in ['ck_name', 'ck_brand', 'ck_carbs', 'ck_protein', 'ck_fat', 'ck_energy', 'ck_confidence']:
                df[col] = df[item_column].map(lambda x: nutrition_cache.get(x, {}).get(col, ''))
            
            # Save enhanced CSV
            os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
            df.to_csv(output_csv, index=False)
            
            successful_matches = len([k for k, v in nutrition_cache.items() if v['ck_carbs'] > 0])
            print(f"\n✅ Enhanced CSV saved to: {output_csv}")
            print(f"📊 Successfully matched: {successful_matches}/{len(unique_items)} items")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing CSV: {str(e)}")
            return False
    
    def interactive_lookup(self):
        """Interactive command-line interface for food lookup."""
        print("🍽️  CalorieKing Direct Lookup")
        print("=" * 40)
        print("Enter food names to search for nutrition information.")
        print("Type 'quit' or 'exit' to stop.\n")
        
        while True:
            try:
                food_name = input("🔍 Enter food name: ").strip()
                
                if food_name.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye! 👋")
                    break
                
                if not food_name:
                    continue
                
                self.print_nutrition_info(food_name)
                print("\n" + "-" * 40)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"Error: {str(e)}")

def main():
    """Main function with different usage modes."""
    querier = CalorieKingDirect()
    
    if len(sys.argv) == 1:
        # Interactive mode
        querier.interactive_lookup()
        
    elif len(sys.argv) == 2:
        # Single food lookup
        food_name = sys.argv[1]
        querier.print_nutrition_info(food_name)
        
    elif len(sys.argv) == 3 and sys.argv[1] == 'csv':
        # CSV processing mode
        input_file = sys.argv[2]
        output_file = input_file.replace('.csv', '_with_nutrition.csv')
        querier.process_csv(input_file, output_file)
        
    else:
        print("Usage:")
        print("  python3 calorie_king_direct.py                    # Interactive mode")
        print("  python3 calorie_king_direct.py 'salmon'           # Single lookup")
        print("  python3 calorie_king_direct.py csv input.csv      # Process CSV")

if __name__ == "__main__":
    main() 