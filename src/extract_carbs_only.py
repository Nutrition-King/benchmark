#!/usr/bin/env python3
"""
Ultra-fast USDA Carbohydrate Data Extractor
Extracts only: Food Name, Carbohydrates, Serving Size
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CarbDataExtractor:
    """Extract only carbohydrate data from USDA database."""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        
    def find_usda_dir(self) -> Path:
        """Find the best USDA directory to use."""
        # Look for directories with USDA data
        patterns = [
            "FoodData_Central_csv_*",
            "FoodData_Central_foundation_food_csv_*"
        ]
        
        usda_dirs = []
        for pattern in patterns:
            matching_dirs = list(self.base_dir.glob(pattern))
            for dir_path in matching_dirs:
                if dir_path.is_dir():
                    if (dir_path / "food.csv").exists() and (dir_path / "food_nutrient.csv").exists():
                        usda_dirs.append(dir_path)
        
        if not usda_dirs:
            raise FileNotFoundError("No USDA data directories found")
        
        # Use the largest directory (full dataset preferred)
        largest_dir = max(usda_dirs, key=lambda d: (d / "food.csv").stat().st_size)
        logger.info(f"Using USDA directory: {largest_dir}")
        return largest_dir
    
    def load_csv_fast(self, csv_path: Path) -> pd.DataFrame:
        """Load CSV with best encoding."""
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                return pd.read_csv(csv_path, encoding=encoding, low_memory=False)
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise ValueError(f"Could not load {csv_path}")
    
    def extract_carb_data(self, max_foods: int = None) -> List[Dict[str, str]]:
        """Extract only the 3 required fields."""
        start_time = time.time()
        
        # Find USDA directory
        usda_dir = self.find_usda_dir()
        
        # Load only the files we need
        logger.info("Loading essential files...")
        
        load_start = time.time()
        foods_df = self.load_csv_fast(usda_dir / "food.csv")
        logger.info(f"✅ Loaded {len(foods_df):,} foods in {time.time() - load_start:.1f}s")
        
        load_start = time.time()
        nutrients_df = self.load_csv_fast(usda_dir / "food_nutrient.csv")
        logger.info(f"✅ Loaded {len(nutrients_df):,} nutrients in {time.time() - load_start:.1f}s")
        
        load_start = time.time()
        nutrient_names_df = self.load_csv_fast(usda_dir / "nutrient.csv")
        logger.info(f"✅ Loaded {len(nutrient_names_df):,} nutrient names in {time.time() - load_start:.1f}s")
        
        # Load branded foods for serving sizes (if exists)
        branded_df = None
        branded_path = usda_dir / "branded_food.csv"
        if branded_path.exists():
            load_start = time.time()
            branded_df = self.load_csv_fast(branded_path)
            logger.info(f"✅ Loaded {len(branded_df):,} branded foods in {time.time() - load_start:.1f}s")
        
        # Find carbohydrate nutrient IDs
        carb_nutrients = nutrient_names_df[
            nutrient_names_df['name'].str.contains('carbohydrate', case=False, na=False)
        ]
        logger.info(f"Found {len(carb_nutrients)} carbohydrate nutrient types:")
        for _, nutrient in carb_nutrients.iterrows():
            logger.info(f"  ID {nutrient['id']}: {nutrient['name']}")
        
        # Get the main carbohydrate nutrient ID (usually "Carbohydrate, by difference")
        main_carb_id = None
        for _, nutrient in carb_nutrients.iterrows():
            if 'by difference' in nutrient['name'].lower():
                main_carb_id = nutrient['id']
                logger.info(f"Using main carb nutrient: {nutrient['name']} (ID: {main_carb_id})")
                break
        
        if main_carb_id is None and len(carb_nutrients) > 0:
            main_carb_id = carb_nutrients.iloc[0]['id']
            logger.info(f"Using first carb nutrient: {carb_nutrients.iloc[0]['name']} (ID: {main_carb_id})")
        
        if main_carb_id is None:
            raise ValueError("No carbohydrate nutrients found!")
        
        # Filter nutrients to only carbohydrates
        logger.info("Filtering to carbohydrate data only...")
        carb_data = nutrients_df[nutrients_df['nutrient_id'] == main_carb_id]
        logger.info(f"Found carbohydrate data for {len(carb_data):,} foods")
        
        # Create serving size lookup
        serving_lookup = {}
        if branded_df is not None:
            for _, row in branded_df.iterrows():
                fdc_id = row['fdc_id']
                serving_size = row.get('serving_size', '')
                serving_unit = row.get('serving_size_unit', '')
                
                if pd.notna(serving_size) and serving_size != '':
                    serving_text = f"{serving_size} {serving_unit}".strip()
                else:
                    serving_text = "100g"  # Default
                
                serving_lookup[fdc_id] = serving_text
        
        # Limit foods if specified
        if max_foods and len(foods_df) > max_foods:
            foods_df = foods_df.head(max_foods)
            logger.info(f"Limited to {max_foods:,} foods for processing")
        
        # Extract the 3 required fields
        logger.info("Extracting carbohydrate data...")
        results = []
        
        # Create carb lookup for faster access
        carb_lookup = dict(zip(carb_data['fdc_id'], carb_data['amount']))
        
        batch_size = 10000
        total_foods = len(foods_df)
        processed = 0
        
        for _, food_row in foods_df.iterrows():
            fdc_id = food_row['fdc_id']
            
            # Get food name
            food_name = food_row.get('description', 'Unknown')
            
            # Get carbohydrate amount
            carb_amount = carb_lookup.get(fdc_id, 0)
            if pd.isna(carb_amount):
                carb_amount = 0
            
            # Get serving size
            serving_size = serving_lookup.get(fdc_id, "100g")
            
            # Only include foods that have carbohydrate data
            if carb_amount > 0:
                results.append({
                    'food_name': food_name,
                    'carbohydrates_g': f"{carb_amount:.1f}",
                    'serving_size': serving_size
                })
            
            processed += 1
            if processed % batch_size == 0:
                logger.info(f"Processed {processed:,}/{total_foods:,} foods, found {len(results):,} with carb data")
        
        total_time = time.time() - start_time
        logger.info(f"✅ Extracted {len(results):,} foods with carbohydrate data in {total_time:.1f}s")
        
        return results
    
    def save_carb_data(self, carb_data: List[Dict[str, str]], filename: str = None) -> Path:
        """Save carbohydrate data to CSV."""
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"usda_carbs_{timestamp}.csv"
        
        output_path = self.base_dir / "data" / filename
        output_path.parent.mkdir(exist_ok=True)
        
        df = pd.DataFrame(carb_data)
        df.to_csv(output_path, index=False)
        
        logger.info(f"💾 Saved {len(carb_data):,} foods to {output_path}")
        return output_path

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract carbohydrate data from USDA database")
    parser.add_argument("--max-foods", type=int, help="Limit number of foods to process")
    parser.add_argument("--output", help="Output filename (default: auto-generated)")
    
    args = parser.parse_args()
    
    print("🥖 USDA Carbohydrate Data Extractor")
    print("=" * 50)
    print("Extracting: Food Name, Carbohydrates, Serving Size")
    print("=" * 50)
    
    try:
        extractor = CarbDataExtractor()
        
        # Extract data
        carb_data = extractor.extract_carb_data(max_foods=args.max_foods)
        
        if not carb_data:
            print("❌ No foods with carbohydrate data found!")
            return 1
        
        # Save data
        output_path = extractor.save_carb_data(carb_data, args.output)
        
        print(f"\n✅ Success!")
        print(f"📊 Foods with carb data: {len(carb_data):,}")
        print(f"📄 Saved to: {output_path}")
        
        # Show sample
        print(f"\n📋 Sample data:")
        for i, item in enumerate(carb_data[:5]):
            print(f"{i+1:2d}. {item['food_name'][:60]:<60} | {item['carbohydrates_g']:>6}g | {item['serving_size']}")
        
        if len(carb_data) > 5:
            print(f"... and {len(carb_data) - 5:,} more foods")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Full error details:")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
