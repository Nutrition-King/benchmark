#!/usr/bin/env python3
"""
Batch USDA Nutrition Lookup via Semantic Search
Takes a CSV file with food items and returns complete nutrition information for all foods
using ChromaDB semantic search with properly rescaled nutrition values.
"""

import os
import csv
import re
import logging
import pandas as pd
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchNutritionLookup:
    """
    Batch processor for semantic food search and nutrition lookup with rescaling.
    """
    
    def __init__(
        self,
        collection_name: str = "usda_food_data",
        persist_directory: str = "../data/chroma_db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """Initialize the Batch Nutrition Lookup system."""
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Set up embedding function
        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Get the collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Connected to ChromaDB collection: {collection_name}")
            logger.info(f"Collection count: {self.collection.count()}")
        except Exception as e:
            logger.error(f"Error connecting to collection '{collection_name}': {e}")
            logger.error("Please run 'python src/upload_data_to_chroma.py' first to create the database")
            raise
    
    def parse_serving_size(self, serving_size_str: str) -> float:
        """Parse serving size string to extract gram weight."""
        if not serving_size_str or pd.isna(serving_size_str):
            return 100.0
        
        # Clean the string
        serving_str = str(serving_size_str).strip().lower()
        
        # Look for gram measurements
        gram_patterns = [
            r'(\d+\.?\d*)\s*g\b',  # "5.0 g" or "100g"
            r'(\d+\.?\d*)\s*gram',  # "5.0 gram"
        ]
        
        for pattern in gram_patterns:
            match = re.search(pattern, serving_str)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        # If no grams found, assume 100g (USDA standard reference)
        return 100.0
    
    def rescale_carbohydrates(self, carb_per_100g: float, actual_serving_g: float) -> float:
        """Rescale carbohydrates from per-100g to actual serving size."""
        if actual_serving_g == 0:
            return 0.0
        
        # Scale proportionally
        rescaled_carbs = carb_per_100g * (actual_serving_g / 100.0)
        return round(rescaled_carbs, 1)
    
    def clean_food_query(self, query: str) -> str:
        """Clean the food query to improve search results."""
        # Convert to lowercase
        cleaned = query.lower().strip()
        
        # Remove common quantity prefixes
        prefixes_to_remove = [
            '1 cup of ', '1 cup ', '2 cups of ', '2 cups ',
            '1 slice of ', '1 slice ', '1 piece of ', '1 piece ',
            '1 ', '2 ', '3 ', '4 ', '5 ', '6 ', '7 ', '8 ', '9 ',
            'one ', 'two ', 'three ',
            'a cup of ', 'a piece of ', 'a slice of '
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        
        # Remove parenthetical information that might confuse search
        if '(' in cleaned:
            cleaned = cleaned.split('(')[0].strip()
        
        # Remove common words that don't add semantic value
        words_to_remove = ['with', 'without', 'cooked', 'raw', 'fresh', 'frozen']
        words = cleaned.split()
        cleaned_words = [word for word in words if word not in words_to_remove]
        cleaned = ' '.join(cleaned_words)
        
        return cleaned.strip()
    
    def search_food_batch(self, food_queries: List[str], n_results: int = 1) -> List[Optional[Dict[str, Any]]]:
        """
        Search for multiple foods in batch and return rescaled nutrition information.
        
        Args:
            food_queries: List of food items to search for
            n_results: Number of results per query (default 1 for best match)
            
        Returns:
            List of dictionaries containing rescaled nutrition data
        """
        results = []
        batch_size = 50  # Process in batches to avoid memory issues
        
        logger.info(f"Processing {len(food_queries)} foods in batches of {batch_size}")
        
        for i in range(0, len(food_queries), batch_size):
            batch = food_queries[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, len(food_queries))
            
            logger.info(f"Processing batch {batch_start}-{batch_end}/{len(food_queries)}")
            
            # Clean queries for this batch
            cleaned_queries = [self.clean_food_query(query) for query in batch]
            
            try:
                # Perform batch semantic search
                search_results = self.collection.query(
                    query_texts=cleaned_queries,
                    n_results=n_results,
                    include=["documents", "distances", "metadatas"]
                )
                
                # Process results for this batch
                for j, original_query in enumerate(batch):
                    if j < len(search_results['ids']) and search_results['ids'][j]:
                        # Get the best match
                        metadata = search_results['metadatas'][j][0]
                        distance = search_results['distances'][j][0]
                        
                        # Extract original values
                        food_name = metadata.get('food_name', 'Unknown')
                        carb_per_100g = float(metadata.get('carbohydrates_g', 0))
                        serving_size_str = metadata.get('serving_size', '100g')
                        
                        # Parse serving size to get grams
                        serving_size_g = self.parse_serving_size(serving_size_str)
                        
                        # Rescale carbohydrates
                        rescaled_carbs = self.rescale_carbohydrates(carb_per_100g, serving_size_g)
                        
                        result = {
                            'original_query': original_query,
                            'cleaned_query': cleaned_queries[j],
                            'usda_name': food_name,
                            'carbohydrates_g': rescaled_carbs,
                            'serving_size': serving_size_str,
                            'serving_size_g': serving_size_g,
                            'original_carbs_per_100g': carb_per_100g,
                            'search_distance': distance,
                            'rescaling_applied': serving_size_g != 100.0,
                            'match_found': True
                        }
                    else:
                        # No match found
                        result = {
                            'original_query': original_query,
                            'cleaned_query': cleaned_queries[j],
                            'usda_name': 'No match found',
                            'carbohydrates_g': 'N/A',
                            'serving_size': 'N/A',
                            'serving_size_g': 'N/A',
                            'original_carbs_per_100g': 'N/A',
                            'search_distance': 'N/A',
                            'rescaling_applied': False,
                            'match_found': False
                        }
                    
                    results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_start}-{batch_end}: {e}")
                # Add error results for this batch
                for query in batch:
                    results.append({
                        'original_query': query,
                        'cleaned_query': 'Error',
                        'usda_name': 'Search error',
                        'carbohydrates_g': 'Error',
                        'serving_size': 'Error',
                        'serving_size_g': 'Error',
                        'original_carbs_per_100g': 'Error',
                        'search_distance': 'Error',
                        'rescaling_applied': False,
                        'match_found': False
                    })
        
        return results
    
    def load_foods_from_csv(self, csv_path: str, food_column: str = None) -> List[str]:
        """
        Load food items from CSV file.
        
        Args:
            csv_path: Path to CSV file containing food items
            food_column: Name of column containing food names (auto-detect if None)
            
        Returns:
            List of food item strings
        """
        foods = []
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded CSV with {len(df)} rows and columns: {list(df.columns)}")
            
            # Auto-detect food column if not specified
            if food_column is None:
                # Look for common food column names
                possible_columns = ['food', 'food_name', 'item', 'description', 'name', 'Item']
                for col in possible_columns:
                    if col in df.columns:
                        food_column = col
                        break
                
                # If no match, use first column
                if food_column is None:
                    food_column = df.columns[0]
                    logger.warning(f"No food column specified, using first column: '{food_column}'")
                else:
                    logger.info(f"Auto-detected food column: '{food_column}'")
            
            # Extract food names
            foods = df[food_column].dropna().astype(str).tolist()
            
            # Remove empty strings
            foods = [food.strip() for food in foods if food.strip()]
            
            logger.info(f"Extracted {len(foods)} food items from column '{food_column}'")
            return foods
            
        except Exception as e:
            logger.error(f"Error loading foods from CSV: {e}")
            raise
    
    def save_results_to_csv(self, results: List[Dict[str, Any]], output_path: str, 
                           include_debug_info: bool = False) -> None:
        """
        Save the nutrition lookup results to a CSV file.
        
        Args:
            results: List of nutrition result dictionaries
            output_path: Path to output CSV file
            include_debug_info: Whether to include debug columns (distances, rescaling info)
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as file:
                if include_debug_info:
                    # Full debug output with all information
                    fieldnames = [
                        'original_query', 'usda_name', 'carbohydrates_g', 'serving_size',
                        'search_distance', 'original_carbs_per_100g', 'serving_size_g',
                        'rescaling_applied', 'cleaned_query', 'match_found'
                    ]
                else:
                    # Clean output with just the essential nutrition information
                    fieldnames = ['original_query', 'usda_name', 'carbohydrates_g', 'serving_size']
                
                writer = csv.DictWriter(file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                
                # Write header
                writer.writeheader()
                
                # Write data
                for result in results:
                    # Prepare row data
                    row_data = {}
                    for field in fieldnames:
                        value = result.get(field, '')
                        
                        # Convert numeric values appropriately
                        if field == 'carbohydrates_g' and value != 'N/A' and value != 'Error':
                            try:
                                value = float(value)
                            except (ValueError, TypeError):
                                pass
                        elif field == 'search_distance' and value != 'N/A' and value != 'Error':
                            try:
                                value = round(float(value), 4)
                            except (ValueError, TypeError):
                                pass
                        
                        row_data[field] = value
                    
                    writer.writerow(row_data)
            
            logger.info(f"Results saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving results to CSV: {e}")
            raise
    
    def process_csv_file(self, input_csv: str, output_csv: str, food_column: str = None,
                        include_debug_info: bool = False) -> Dict[str, Any]:
        """
        Complete workflow: load CSV, perform batch lookup, save results.
        
        Args:
            input_csv: Path to input CSV file with food items
            output_csv: Path to output CSV file for results
            food_column: Name of column containing food names (auto-detect if None)
            include_debug_info: Whether to include debug information in output
            
        Returns:
            Dictionary with processing statistics
        """
        start_time = datetime.now()
        
        # Load foods from CSV
        logger.info(f"Loading foods from {input_csv}")
        foods = self.load_foods_from_csv(input_csv, food_column)
        
        if not foods:
            raise ValueError("No foods found in input CSV")
        
        # Perform batch lookup
        logger.info(f"Starting batch nutrition lookup for {len(foods)} foods")
        results = self.search_food_batch(foods)
        
        # Save results
        logger.info(f"Saving results to {output_csv}")
        self.save_results_to_csv(results, output_csv, include_debug_info)
        
        # Calculate statistics
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        successful_matches = sum(1 for r in results if r['match_found'])
        rescaled_items = sum(1 for r in results if r.get('rescaling_applied', False))
        
        stats = {
            'total_foods': len(foods),
            'successful_matches': successful_matches,
            'match_rate': successful_matches / len(foods) * 100,
            'rescaled_items': rescaled_items,
            'processing_time_seconds': processing_time,
            'foods_per_second': len(foods) / processing_time if processing_time > 0 else 0,
            'input_file': input_csv,
            'output_file': output_csv
        }
        
        return stats

def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(
        description="Batch USDA nutrition lookup via semantic search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - auto-detect food column
  python batch_nutrition_lookup.py input_foods.csv output_nutrition.csv
  
  # Specify food column name
  python batch_nutrition_lookup.py input_foods.csv output_nutrition.csv --food-column "Item"
  
  # Include debug information (distances, rescaling details)
  python batch_nutrition_lookup.py input_foods.csv output_nutrition.csv --debug
  
  # Use different ChromaDB database
  python batch_nutrition_lookup.py input_foods.csv output_nutrition.csv --chroma-db ../my_db
        """
    )
    
    parser.add_argument(
        "input_csv",
        help="Input CSV file containing food items"
    )
    parser.add_argument(
        "output_csv", 
        help="Output CSV file for nutrition results"
    )
    parser.add_argument(
        "--food-column",
        help="Name of column containing food items (auto-detect if not specified)"
    )
    parser.add_argument(
        "--chroma-db",
        default="../data/chroma_db",
        help="Path to ChromaDB database directory (default: ../data/chroma_db)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Include debug information in output (search distances, rescaling details)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input_csv).exists():
        logger.error(f"Input file not found: {args.input_csv}")
        return 1
    
    # Validate ChromaDB directory
    if not Path(args.chroma_db).exists():
        logger.error(f"ChromaDB directory not found: {args.chroma_db}")
        logger.error("Please run 'python src/upload_data_to_chroma.py' first to create the database")
        return 1
    
    try:
        # Initialize lookup system
        logger.info("Initializing batch nutrition lookup system...")
        lookup = BatchNutritionLookup(persist_directory=args.chroma_db)
        
        # Process the CSV file
        stats = lookup.process_csv_file(
            input_csv=args.input_csv,
            output_csv=args.output_csv,
            food_column=args.food_column,
            include_debug_info=args.debug
        )
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("BATCH PROCESSING COMPLETE - SUMMARY:")
        logger.info("="*70)
        logger.info(f"Input file: {stats['input_file']}")
        logger.info(f"Output file: {stats['output_file']}")
        logger.info(f"Total foods processed: {stats['total_foods']:,}")
        logger.info(f"Successful matches: {stats['successful_matches']:,} ({stats['match_rate']:.1f}%)")
        logger.info(f"Items rescaled: {stats['rescaled_items']:,}")
        logger.info(f"Processing time: {stats['processing_time_seconds']:.1f} seconds")
        logger.info(f"Speed: {stats['foods_per_second']:.1f} foods/second")
        
        if stats['successful_matches'] < stats['total_foods']:
            failed_count = stats['total_foods'] - stats['successful_matches']
            logger.warning(f"⚠️  {failed_count} foods had no matches - check input data quality")
        
        logger.info(f"\n✅ Results saved to: {args.output_csv}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
