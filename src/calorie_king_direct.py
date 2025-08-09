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
from dotenv import load_dotenv

# Load environment variables from a local .env file if present
load_dotenv()

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
            'vegetables': {'broccoli', 'spinach', 'carrot', 'tomato', 'lettuce', 'onion', 'pepper', 'corn', 'peas', 'beans', 'potato', 'sweet potato', 'cauliflower', 'cabbage', 'celery', 'cucumber', 'zucchini', 'squash', 'beet', 'radish'},
            'fruits': {'apple', 'banana', 'orange', 'grape', 'strawberry', 'blueberry', 'peach', 'pear', 'cherry'},
            'grains': {'rice', 'bread', 'pasta', 'oats', 'quinoa', 'barley', 'wheat', 'cereal'},
            'nuts': {'almond', 'walnut', 'peanut', 'cashew', 'pecan', 'pistachio'},
            'beverages': {'juice', 'soda', 'beer', 'wine', 'coffee', 'tea', 'water', 'smoothie'},
            'desserts': {'cake', 'cookie', 'ice cream', 'chocolate', 'candy', 'pie', 'donut'}
        }
        
        self.cooking_methods = {'baked', 'grilled', 'fried', 'roasted', 'steamed', 'boiled', 'raw', 'broiled', 'sauteed', 'smoked'}
        
        # Measurement words to ignore in matching
        self.measurement_words = {
            'oz', 'ounce', 'ounces', 'lb', 'pound', 'pounds',
            'cup', 'cups', 'tbsp', 'tsp', 'gram', 'grams', 'kg',
            'serving', 'piece', 'slice', 'medium', 'large', 'small',
            'patty', 'bun', 'buns',
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
        }
    
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
                    carbs = food_data.get('netCarbs', food_data.get('totalCarbs', food_data.get('carbohydrates', 0)))
                    if carbs == 0 and 'nutrients' in food_data:
                        nutrients = food_data['nutrients']
                        carbs = nutrients.get('netCarbs', nutrients.get('totalCarbs', nutrients.get('carbohydrates', 0)))
                    print(f"    ✅ Got nutrition data - Carbs: {carbs}g")
                else:
                    print(f"    ❌ No detailed nutrition data")
                time.sleep(0.1)  # Rate limiting
        
        return detailed_results
    
    def _preprocess_query(self, query: str) -> str:
        """Preprocess query to improve search success by simplifying complex descriptions."""
        # Remove portion size patterns like "(3 oz)", "(1 cup)", etc.
        query = re.sub(r'\([^)]*\b(?:oz|cup|slice|piece|serving|gram|g|lb|pound|tbsp|tsp|patty|bun|buns)\b[^)]*\)', '', query)
        
        # Remove standalone measurements
        query = re.sub(r'\b\d+\s*(?:oz|cup|slice|piece|serving|gram|g|lb|pound|tbsp|tsp|patty|bun|buns)\b', '', query)
        
        # Handle multi-ingredient descriptions - extract the main ingredient
        if 'mix of' in query.lower() or 'and' in query.lower():
            # For "mix of broccoli, carrots, and bell peppers" -> focus on first ingredient
            parts = re.split(r',\s*(?:mix of|and|or)\s*|,\s*', query)
            if parts:
                # Take the first substantial ingredient
                for part in parts:
                    part = part.strip()
                    if len(part) > 3 and not any(skip in part.lower() for skip in ['mix', 'cup', 'of']):
                        query = part
                        break
        
        # Handle generic terms that might need to be more specific
        # Removed special-casing that collapsed 'roasted vegetables' to 'vegetables'

        # Apply simple synonyms to match CalorieKing vocabulary better
        query = self._apply_synonyms(query)
        
        # Clean up extra whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query

    def _apply_synonyms(self, text: str) -> str:
        """Apply a small set of synonyms to better match CalorieKing naming."""
        synonyms_map = {
            'burger bun': 'hamburger bun',
        }
        lowered = text.lower()
        for src, dst in synonyms_map.items():
            lowered = re.sub(rf'\b{re.escape(src)}\b', dst, lowered, flags=re.IGNORECASE)
        return lowered

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
        """Search for foods by name using the CalorieKing API's search functionality."""
        try:
            # Preprocess query to improve search success
            processed_query = self._preprocess_query(query)
            if processed_query != query:
                print(f"🔍 Simplified '{query}' → '{processed_query}'")
            # Build fallback query variants
            fallback_queries = self._generate_fallback_queries(processed_query)
            
            # Aggregate foods from all variants instead of stopping at the first
            foods: List[Dict[str, Any]] = []
            seen_ids: Set[str] = set()
            last_error: Optional[Exception] = None
            for attempt_query in fallback_queries:
                print(f"🔍 Searching CalorieKing database for '{attempt_query}'...")
                url = f"{self.base_url}/foods"
                # API only accepts specific limit values: [1, 5, 10, 20, 30, 50, 100, 1000]
                api_limit = min(limit * 3, 100)
                valid_limits = [1, 5, 10, 20, 30, 50, 100, 1000]
                api_limit = min(valid_limits, key=lambda x: abs(x - api_limit))
                params = {
                    'query': attempt_query,
                    'region': 'us',
                    'limit': api_limit
                }
                try:
                    response = requests.get(
                        url,
                        auth=(self.access_token, ''),
                        headers=self.headers,
                        params=params
                    )
                    response.raise_for_status()
                    search_response = response.json()
                    new_foods = search_response.get('foods', []) if search_response else []
                    for f in new_foods:
                        rev = f.get('revisionId')
                        if rev and rev not in seen_ids:
                            foods.append(f)
                            seen_ids.add(rev)
                except Exception as e:
                    last_error = e
                    continue
            
            if not foods:
                if last_error:
                    print(f"Error searching for '{processed_query}': {str(last_error)}")
                print("❌ No search results returned from API")
                return []
            print(f"📋 API returned {len(foods)} aggregated search results")
            
            # Extract keywords for relevance scoring using original query
            query_keywords = self._extract_keywords(query)
            print(f"📝 Keywords: {query_keywords['main_keywords']}")
            print(f"🍽️  Food types: {query_keywords['food_types']}")
            print(f"👨‍🍳 Cooking methods: {query_keywords['cooking_methods']}")
            
            # Score and collect all results
            scored: List[Dict[str, Any]] = []
            for food in foods:
                food_name = food.get('name', '').lower()
                score, score_breakdown = self._calculate_relevance_detailed(query_keywords, food_name, food)
                food_with_score = food.copy()
                food_with_score['relevance_score'] = score
                food_with_score['score_breakdown'] = score_breakdown
                scored.append(food_with_score)

            # Prefer stricter threshold first, then relax if empty
            def filter_and_log(threshold: float) -> List[Dict[str, Any]]:
                filtered = [f for f in scored if f.get('relevance_score', 0) > threshold]
                filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
                for f in filtered[:limit]:
                    print(f"  📝 Match: {f.get('name', 'Unknown')} (score: {f.get('relevance_score', 0):.3f})")
                    print(f"      💡 {f.get('score_breakdown', '')}")
                return filtered

            matches = filter_and_log(0.5)
            if not matches:
                matches = filter_and_log(0.3)
            # Final fallback: pick top scored item if still empty
            if not matches and scored:
                # Prefer items containing any main keyword
                main_words = query_keywords.get('main_keywords', set())
                contains_keyword = [f for f in scored if any(w in f.get('name', '').lower() for w in main_words)]
                candidates = contains_keyword or scored
                candidates.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
                top = candidates[:limit]
                for f in top:
                    print(f"  📝 Fallback: {f.get('name', 'Unknown')} (score: {f.get('relevance_score', 0):.3f})")
                matches = top
            print(f"📊 Found {len(matches)} relevant matches")
            
            return matches[:limit]
            
        except Exception as e:
            print(f"Error searching for '{query}': {str(e)}")
            return []

    def _generate_fallback_queries(self, processed_query: str) -> List[str]:
        """Generate a list of fallback queries from most to least specific."""
        variants: List[str] = []
        s = processed_query.strip()
        if not s:
            return [processed_query]
        
        variants.append(s)
        # Remove trailing "with ..."
        without_with = re.sub(r"\bwith\b.*$", "", s).strip()
        if without_with and without_with not in variants:
            variants.append(without_with)
        
        # Remove leading prep/cooking terms like "slow cooker", "instant pot", "baked", "grilled", etc.
        prep_patterns = [
            r"^slow cooker\s+", r"^slow-cooker\s+", r"^slow\s+", r"^crockpot\s+", r"^instant pot\s+",
            r"^baked\s+", r"^grilled\s+", r"^fried\s+", r"^roasted\s+", r"^steamed\s+", r"^boiled\s+",
            r"^raw\s+", r"^broiled\s+", r"^sauteed\s+", r"^smoked\s+",
        ]
        t = s
        for pat in prep_patterns:
            t = re.sub(pat, "", t, flags=re.IGNORECASE).strip()
        if t and t not in variants:
            variants.append(t)
        if without_with:
            t2 = without_with
            for pat in prep_patterns:
                t2 = re.sub(pat, "", t2, flags=re.IGNORECASE).strip()
            if t2 and t2 not in variants:
                variants.append(t2)
        
        # Fallback to first 1-2 words
        words = s.split()
        if len(words) >= 2:
            first_two = " ".join(words[:2])
            if first_two not in variants:
                variants.append(first_two)
        if len(words) >= 1 and words[0] not in variants:
            variants.append(words[0])

        # Last-word variant (e.g., 'salmon' from 'baked salmon')
        if words:
            last_word = words[-1]
            if last_word and last_word not in variants:
                variants.append(last_word)

        # Targeted variants for common CK naming
        if re.search(r"\broasted vegetables\b", s, flags=re.IGNORECASE):
            v = re.sub(r"\broasted\b", "roast", s, flags=re.IGNORECASE)
            if v and v not in variants:
                variants.append(v)
        if re.search(r"\bvegetables\b", s, flags=re.IGNORECASE) and not re.search(r"\b(mix|mixed|medley)\b", s, flags=re.IGNORECASE):
            v2 = re.sub(r"\bvegetables\b", "mixed vegetables", s, flags=re.IGNORECASE)
            if v2 and v2 not in variants:
                variants.append(v2)
        
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for v in variants:
            if v and v.lower() not in seen:
                ordered.append(v)
                seen.add(v.lower())
        return ordered
    
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
            
            return result
        except Exception as e:
            print(f"Error getting food details for {revision_id}: {str(e)}")
            return None
    
    def _calculate_relevance_detailed(self, query_keywords: Dict[str, Set[str]], food_name: str, food_data: Dict) -> tuple[float, str]:
        """Calculate relevance score with detailed breakdown for debugging."""
        score = 0
        breakdown_parts = []
        
        food_name_words = set(re.findall(r'\b\w+\b', food_name.lower()))
        food_name_lower = food_name.lower()
        
        # 1. EXACT multi-word phrase match (highest priority)
        original_query_words = list(query_keywords['main_keywords'])
        if len(original_query_words) > 1:
            query_phrase = ' '.join(sorted(original_query_words))
            if query_phrase in food_name_lower:
                score += 2.0
                breakdown_parts.append(f"exact_phrase:2.00")
        
        # 2. ALL keywords present (very high priority)
        all_keywords_present = all(keyword in food_name_lower for keyword in query_keywords['main_keywords'])
        if all_keywords_present and len(query_keywords['main_keywords']) > 1:
            score += 1.5
            breakdown_parts.append(f"all_keywords:1.50")
        
        # 3. Individual exact keyword matches with word boundary checking
        exact_match_score = 0
        specificity_bonus = 0
        matched_keywords = 0

        for keyword in query_keywords['main_keywords']:
            if keyword in food_name_lower:
                matched_keywords += 1
                
                # Check if it's an exact word match (not just substring)
                if keyword in food_name_words:
                    exact_match_score += 1.0
                    specificity_bonus += 0.2
                else:
                    # Partial match within a word
                    exact_match_score += 0.5
                
        # Bonus for matching all keywords
        if matched_keywords == len(query_keywords['main_keywords']) and len(query_keywords['main_keywords']) > 1:
            specificity_bonus += 0.3
            
        # Bonus for fewer additional descriptors (simpler = better for basic searches)
        food_words = food_name_lower.split()
        if len(food_words) <= len(query_keywords['main_keywords']) + 1:
            specificity_bonus += 0.2
            
        # Penalty for overly processed/prepared versions when searching for basic food
        processed_terms = ['fried', 'battered', 'takeaway', 'block', 'frozen', 'canned', 'instant']
        if any(term in food_name_lower for term in processed_terms):
            if not any(term in query_keywords['all_words'] for term in processed_terms):
                specificity_bonus -= 0.3
                
        if exact_match_score > 0:
            breakdown_parts.append(f"exact_match:{exact_match_score:.2f}+specificity:{specificity_bonus:.2f}")

        score += exact_match_score + specificity_bonus
        
        # 4. Food category matching (including when searching by category name)
        food_category_score = 0
        
        # Check if this food belongs to a category we're searching for
        food_belongs_to_categories = set()
        for category, foods in self.food_types.items():
            if any(food in food_name_lower for food in foods):
                food_belongs_to_categories.add(category)
        
        # If searching by category name (like "vegetables"), match foods in that category
        if 'vegetables' in query_keywords['main_keywords'] and 'vegetables' in food_belongs_to_categories:
            food_category_score = 0.8  # High score for category match
            breakdown_parts.append(f"category_match:{food_category_score:.2f}")
        elif query_keywords['food_types']:
            # Normal category matching for foods with explicit type detection
            for category in query_keywords['food_types']:
                if category in food_belongs_to_categories:
                    food_category_score = 0.6
                    breakdown_parts.append(f"category_type:{food_category_score:.2f}")
                    break
        elif exact_match_score == 0:
            # Fallback category matching
            for category in query_keywords['food_types']:
                category_foods = self.food_types[category]
                if any(food in food_name_lower for food in category_foods):
                    food_category_score = 0.4
                    breakdown_parts.append(f"category_fallback:{food_category_score:.2f}")
                    break
        
        score += food_category_score
        
        # 5. Cooking method matches
        cooking_score = 0
        for method in query_keywords['cooking_methods']:
            if method in food_name_lower:
                cooking_score = 0.4
                breakdown_parts.append(f"cooking:{cooking_score:.2f}")
                break
        score += cooking_score
        
        # 6. NEGATIVE SCORING - Penalize wrong categories more heavily
        penalty = 0
        
        # Strong penalty for wrong food type
        if query_keywords['food_types']:
            # If searching for a specific food type, penalize results from very different types
            wrong_categories = set()
            if 'vegetables' in query_keywords['food_types']:
                wrong_categories.update(['beverages', 'desserts', 'meat', 'fish', 'dairy'])
            elif 'grains' in query_keywords['food_types']:
                wrong_categories.update(['beverages', 'desserts', 'meat', 'fish', 'dairy'])
            elif 'fish' in query_keywords['food_types']:
                wrong_categories.update(['beverages', 'desserts', 'vegetables', 'fruits', 'grains', 'meat'])
            elif 'meat' in query_keywords['food_types']:
                wrong_categories.update(['beverages', 'desserts', 'vegetables', 'fruits', 'grains', 'fish'])
            elif 'dairy' in query_keywords['food_types']:
                wrong_categories.update(['beverages', 'desserts', 'meat', 'fish', 'vegetables'])
                
            for wrong_cat in wrong_categories:
                if any(item in food_name_lower for item in self.food_types[wrong_cat]):
                    penalty = 1.5  # Stronger penalty
                    breakdown_parts.append(f"penalty_wrong_category:-{penalty:.2f}")
                    break
                    
        # Extra penalty for dishes with multiple components when searching for single ingredient
        if len(query_keywords['main_keywords']) <= 2:
            # If searching for simple terms like "vegetables" or "salmon"
            complex_indicators = ['plus', 'sides', 'prepared', 'chicken', 'harvest']
            if any(indicator in food_name_lower for indicator in complex_indicators):
                penalty = max(penalty, 1.0)
                breakdown_parts.append(f"penalty_complex:-1.00")
        
        # Context-aware penalties/boosts for burger vs sandwich
        query_words = query_keywords['all_words']
        # Hard requirement: if query contains burger/patty, candidate must reflect burger/patty
        if any(w in query_words for w in {'burger', 'patty'}) and not any(
            k in food_name_lower for k in {'burger', 'patty', 'hamburger'}
        ):
            breakdown_parts.append("hard_fail_missing_burger")
            return 0.0, (" | ".join(breakdown_parts) if breakdown_parts else "hard_fail_missing_burger")

        if any(w in query_words for w in {'burger', 'patty'}):
            if 'sandwich' in food_name_lower or 'wrap' in food_name_lower:
                penalty = max(penalty, 0.8)
                breakdown_parts.append("penalty_non_burger:-0.80")
            if 'burger' in food_name_lower or 'patty' in food_name_lower:
                score += 0.6
                breakdown_parts.append("boost_burger:0.60")

        # Respect plural/general dish terms for vegetables and fries
        if 'vegetables' in query_keywords['all_words']:
            if not any(k in food_name_lower for k in ['vegetables', 'mixed', 'mix', 'medley']):
                penalty = max(penalty, 0.8)
                breakdown_parts.append("penalty_not_plural_mix:-0.80")

        if 'fries' in query_keywords['all_words']:
            if 'fries' not in food_name_lower:
                penalty = max(penalty, 1.2)
                breakdown_parts.append("penalty_missing_fries:-1.20")

        # Penalty for alcohol when not searching for it
        if any(alcohol_word in food_name_lower for alcohol_word in ['beer', 'wine', 'alcohol', 'liquor']):
            if not any(alcohol_word in query_keywords['all_words'] for alcohol_word in ['beer', 'wine', 'alcohol', 'liquor']):
                penalty = max(penalty, 0.9)
                breakdown_parts.append(f"penalty_alcohol:-0.90")

        # Hard negatives for packets/mixes/etc unless explicitly requested
        hard_negative_terms = ['seasoning', 'mix', 'packet', 'dry', 'powder',
                               'base', 'bouillon', 'condensed', 'dressing', 'gravy', 'sauce']
        if any(t in food_name_lower for t in hard_negative_terms) and not any(
            t in query_keywords['all_words'] for t in hard_negative_terms
        ):
            # Make it a strong penalty rather than absolute block to still allow true dishes like 'Chili, large'
            penalty = max(penalty, 2.0)
            breakdown_parts.append("penalty_hard_negatives:-2.00")
        
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
        self._display_nutrition_details(food)
    
    def _display_nutrition_details(self, food: Dict[str, Any]):
        """Display detailed nutrition information for a food item."""
        # Get base nutrition values (per 100g)
        base_carbs = food.get('netCarbs', food.get('totalCarbs', food.get('carbohydrates', 0)))
        base_protein = food.get('protein', 0)
        base_fat = food.get('fat', 0)
        base_energy = food.get('energy', 0)
        base_fiber = food.get('fiber', 0)
        
        # If nutrients are nested, try to get them
        if base_carbs == 0 and 'nutrients' in food:
            nutrients = food['nutrients']
            base_carbs = nutrients.get('netCarbs', nutrients.get('totalCarbs', nutrients.get('carbohydrates', 0)))
            base_protein = nutrients.get('protein', 0)
            base_fat = nutrients.get('fat', 0)
            base_energy = nutrients.get('energy', 0)
            base_fiber = nutrients.get('fiber', 0)
        
        print(f"\n{food.get('name', 'Unknown')}")
        if food.get('brandName'):
            print(f"Brand: {food['brandName']}")
        
        # Get serving size information and calculate scaled nutrition
        base_mass = food.get('mass', 100)
        serving_scale = 1.0
        
        if 'defaultServing' in food:
            default_serving = food['defaultServing']
            serving_name = default_serving.get('name', 'Unknown serving')
            serving_scale = default_serving.get('scale', 1.0)
            calculated_mass = base_mass * serving_scale
            
            print(f"📏 Serving size: {serving_name} ({calculated_mass:.0f}g)")
        elif 'servings' in food and food['servings']:
            # Use first serving if no default
            first_serving = food['servings'][0]
            serving_name = first_serving.get('name', 'Unknown serving')
            serving_scale = first_serving.get('scale', 1.0)
            calculated_mass = base_mass * serving_scale
            print(f"📏 Serving size: {serving_name} ({calculated_mass:.0f}g)")
        else:
            print(f"📏 Serving size: Per 100g")
        
        # Calculate actual serving nutrition by applying scale factor
        carbs = base_carbs * serving_scale
        protein = base_protein * serving_scale
        fat = base_fat * serving_scale
        fiber = base_fiber * serving_scale
        energy = base_energy * serving_scale
        
        print(f"Relevance: {food.get('relevance_score', 0):.2f}")
        print(f"🥕 Carbs: {carbs:.1f}g")
        print(f"🥩 Protein: {protein:.1f}g")
        print(f"🥑 Fat: {fat:.1f}g")
        if fiber > 0:
            print(f"🌾 Fiber: {fiber:.1f}g")
        if energy > 0:
            print(f"⚡ Energy: {energy:.0f} kJ")
        
        # Show nutrition per 100g for comparison
        if serving_scale != 1.0:
            print(f"\n📐 Per 100g (base values):")
            print(f"🥕 Carbs: {base_carbs:.1f}g")
            print(f"🥩 Protein: {base_protein:.1f}g") 
            print(f"🥑 Fat: {base_fat:.1f}g")
            if base_fiber > 0:
                print(f"🌾 Fiber: {base_fiber:.1f}g")
    
    def _parse_requested_serving(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse serving size from free-text, e.g., '3 oz', '1 cup', 'medium serving'."""
        s = text.lower()
        # Fractions like 1/2, 3/4
        m = re.search(r"(\d+)\s*/\s*(\d+)\s*(cup|cups|oz|ounce|ounces|g|gram|grams)\b", s)
        if m:
            num, den = float(m.group(1)), float(m.group(2))
            amount = num / den
            unit = m.group(3)
            if unit in ('oz', 'ounce', 'ounces'):
                grams = amount * 28.3495
                return {"type": "mass", "grams": grams, "label": f"{amount:g} oz"}
            if unit in ('g', 'gram', 'grams'):
                grams = amount
                return {"type": "mass", "grams": grams, "label": f"{grams:g} g"}
            if unit in ('cup', 'cups'):
                return {"type": "volume", "unit": "cup", "amount": amount, "label": f"{amount:g} cup" + ("s" if amount != 1 else "")}
        # Prefer explicit masses
        m = re.search(r"(\d+(?:\.\d+)?)\s*(oz|ounce|ounces)\b", s)
        if m:
            ounces = float(m.group(1))
            grams = ounces * 28.3495
            return {"type": "mass", "grams": grams, "label": f"{ounces:g} oz"}
        m = re.search(r"(\d+(?:\.\d+)?)\s*(g|gram|grams)\b", s)
        if m:
            grams = float(m.group(1))
            return {"type": "mass", "grams": grams, "label": f"{grams:g} g"}

        # Volumes
        m = re.search(r"(\d+(?:\.\d+)?)\s*(cup|cups)\b", s)
        if m:
            amount = float(m.group(1))
            return {"type": "volume", "unit": "cup", "amount": amount, "label": f"{amount:g} cup" + ("s" if amount != 1 else "")}

        # Generic units
        for unit in ["slice", "piece", "serving", "patty", "bun", "buns"]:
            m = re.search(rf"(\d+(?:\.\d+)?)\s*{unit}\b", s)
            if m:
                amount = float(m.group(1))
                return {"type": "keyword", "keyword": unit, "amount": amount, "label": f"{amount:g} {unit}"}

        # Size adjectives
        for size_word in ["small", "medium", "large"]:
            if re.search(rf"\b{size_word}\b", s):
                return {"type": "keyword", "keyword": size_word, "amount": 1.0, "label": size_word}

        return None

    def _choose_serving_scale(self, food: Dict[str, Any], requested: Optional[Dict[str, Any]]) -> tuple[float, str]:
        """Choose serving scale and label based on requested serving and available servings."""
        base_mass = food.get('mass', 100) or 100
        servings = food.get('servings', []) or []
        default_serving = food.get('defaultServing')

        # Default
        scale = 1.0
        label = 'Per 100g'
        if default_serving:
            scale = float(default_serving.get('scale', 1.0) or 1.0)
            label = default_serving.get('name', 'serving')

        if not requested:
            return scale, label

        # Mass-based request
        if requested['type'] == 'mass':
            grams = float(requested['grams'])
            return grams / base_mass, requested.get('label', f"{grams:g} g")

        # Volume-based request: attempt to find a matching serving name
        if requested['type'] == 'volume' and requested['unit'] == 'cup':
            # Prefer servings that contain 'cup'
            cup_servings = [s for s in servings if 'name' in s and 'cup' in s['name'].lower()]
            if cup_servings:
                cup_scale = float(cup_servings[0].get('scale', 1.0) or 1.0)
                amount = float(requested.get('amount', 1.0) or 1.0)
                return cup_scale * amount, requested.get('label', 'cup')
            # Fallback: use default scale as one cup if no explicit cup serving
            amount = float(requested.get('amount', 1.0) or 1.0)
            return scale * amount, requested.get('label', 'cup')

        # Keyword-based request: try to match serving names
        if requested['type'] == 'keyword':
            keyword = requested['keyword']
            amount = float(requested.get('amount', 1.0) or 1.0)
            candidates = [s for s in servings if 'name' in s and keyword in s['name'].lower()]
            if candidates:
                k_scale = float(candidates[0].get('scale', 1.0) or 1.0)
                return k_scale * amount, requested.get('label', keyword)
            # Special-case: generic 'serving' maps to default
            if keyword == 'serving' and default_serving:
                d_scale = float(default_serving.get('scale', 1.0) or 1.0)
                return d_scale * amount, requested.get('label', 'serving')
            # Size words
            size_candidates = [s for s in servings if 'name' in s and keyword in s['name'].lower()]
            if size_candidates:
                s_scale = float(size_candidates[0].get('scale', 1.0) or 1.0)
                return s_scale * amount, requested.get('label', keyword)

        # Fallback to default
        return scale, label

    def get_best_match(self, food_name: str, requested_serving: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get the best matching nutrition information for a food, with optional serving override."""
        results = self.query_food(food_name, max_results=1)
        
        if results:
            best_match = results[0]
            
            # Get base nutrition values (per 100g)
            base_carbs = best_match.get('netCarbs', best_match.get('totalCarbs', best_match.get('carbohydrates', 0)))
            base_protein = best_match.get('protein', 0)
            base_fat = best_match.get('fat', 0)
            base_energy = best_match.get('energy', 0)
            
            # If nutrients are nested, try to get them
            if base_carbs == 0 and 'nutrients' in best_match:
                nutrients = best_match['nutrients']
                base_carbs = nutrients.get('netCarbs', nutrients.get('totalCarbs', nutrients.get('carbohydrates', 0)))
                base_protein = nutrients.get('protein', 0)
                base_fat = nutrients.get('fat', 0)
                base_energy = nutrients.get('energy', 0)
            
            # Choose serving scale based on requested serving
            serving_scale, quantity = self._choose_serving_scale(best_match, requested_serving)
            
            # Apply scaling to get actual serving nutrition
            carbs = base_carbs * serving_scale
            protein = base_protein * serving_scale
            fat = base_fat * serving_scale
            energy = base_energy * serving_scale
            
            return {
                "food_name": best_match.get('name', ''),
                "carbs": carbs,
                "protein": protein,
                "fat": fat,
                "energy": energy,
                "confidence": best_match.get('relevance_score', 0),
                "brand": best_match.get('brandName', ''),
                "quantity": quantity,
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
                # Fallback to the first column if specified one is missing
                item_column = df.columns[0]
                print(f"ℹ️ Using first column '{item_column}' for items")
            
            # Get unique food items
            unique_items = df[item_column].dropna().unique()
            print(f"📋 Processing {len(unique_items)} unique food items...")
            
            # Query nutrition data for each unique item
            nutrition_cache = {}
            for i, food_item in enumerate(unique_items, 1):
                print(f"\n[{i}/{len(unique_items)}] Querying: {food_item}")
                # Parse requested serving from the text
                requested_serving = self._parse_requested_serving(str(food_item))
                
                # Try normal lookup first
                best_match = self.get_best_match(food_item, requested_serving=requested_serving)
                
                # If still not found and phrase has "with", attempt composite calculation
                if (not best_match or not best_match.get('food_name')) and ' with ' in str(food_item).lower():
                    composite = self._composite_nutrition_from_phrase(str(food_item), requested_serving)
                    if composite:
                        nutrition_cache[food_item] = {
                            'ck_name': composite['food_name'],
                            'ck_carbs': composite['carbs'],
                            'ck_quantity': composite.get('quantity', '')
                        }
                        print(f"  ✅ Composed: {composite['food_name']} - {composite['carbs']:.1f}g carbs")
                        time.sleep(0.3)
                        continue
                
                if best_match and best_match.get('food_name'):
                    nutrition_cache[food_item] = {
                        'ck_name': best_match['food_name'],
                        'ck_carbs': best_match['carbs'],
                        'ck_quantity': best_match.get('quantity', ''),
                    }
                    print(f"  ✅ Found: {best_match['food_name']} - {best_match['carbs']:.1f}g carbs")
                else:
                    nutrition_cache[food_item] = {'ck_name': '', 'ck_carbs': 0, 'ck_quantity': ''}
                    print(f"  ❌ No results found")
                
                time.sleep(0.3)  # Rate limiting
            
            # Add nutrition data to dataframe
            for col in ['ck_name', 'ck_carbs', 'ck_quantity']:
                df[col] = df[item_column].map(lambda x: nutrition_cache.get(x, {}).get(col, ''))
            
            # Save CSV with only requested columns
            os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
            df_out = df[['ck_name', 'ck_carbs', 'ck_quantity']]
            df_out.to_csv(output_csv, index=False)
            
            successful_matches = len([k for k, v in nutrition_cache.items() if v['ck_name']])
            print(f"\n✅ Enhanced CSV saved to: {output_csv}")
            print(f"📊 Successfully matched: {successful_matches}/{len(unique_items)} items")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing CSV: {str(e)}")
            return False

    def _composite_nutrition_from_phrase(self, text: str, requested_serving: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Compose nutrition by summing major components (e.g., 'chili with quinoa')."""
        s = text.lower()
        if ' with ' not in s:
            return None
        base_part, tail = s.split(' with ', 1)
        # Extract first component noun from tail (before comma/parenthesis)
        tail_clean = re.split(r'[,(]', tail)[0].strip()
        if not tail_clean:
            return None

        # Look up base and component
        base = self.get_best_match(base_part, requested_serving=requested_serving)
        component = self.get_best_match(tail_clean, requested_serving=None)
        if not base or not base.get('food_name') or not component or not component.get('food_name'):
            return None
        
        # Sum carbs; keep quantity from base
        carbs = float(base.get('carbs') or 0) + float(component.get('carbs') or 0)
        name = f"{base['food_name']} + {component['food_name']}"
        return {
            'food_name': name,
            'carbs': carbs,
            'quantity': base.get('quantity', '')
        }
    
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