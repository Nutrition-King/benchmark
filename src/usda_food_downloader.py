#!/usr/bin/env python3
"""
USDA Food Database Downloader and Consolidator
Downloads and consolidates USDA FoodData Central database for nutrition analysis.

Based on the pipeline from: https://github.com/jack-tol/usda-food-data-pipeline
"""

import os
import requests
import zipfile
import pandas as pd
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('usda_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class USDAFoodDownloader:
    """
    Downloads and consolidates USDA FoodData Central database.
    """
    
    def __init__(self, data_dir: str = "../data", download_dir: str = "../downloads"):
        """
        Initialize the USDA Food Downloader.
        
        Args:
            data_dir: Directory to save processed data
            download_dir: Directory for temporary downloads
        """
        self.data_dir = Path(data_dir)
        self.download_dir = Path(download_dir)
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # USDA FoodData Central URLs
        self.base_url = "https://fdc.nal.usda.gov"
        self.download_urls = {
            "full": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_csv_.zip",
            "foundation": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_.zip",
            "branded": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_csv_.zip"
        }
        
        logger.info(f"Initialized USDA Food Downloader")
        logger.info(f"Data directory: {self.data_dir.absolute()}")
        logger.info(f"Download directory: {self.download_dir.absolute()}")

    def get_latest_download_url(self, dataset_type: str = "full") -> str:
        """
        Get the latest download URL for USDA FoodData Central.
        
        Args:
            dataset_type: Type of dataset ('full', 'foundation', 'branded')
            
        Returns:
            Latest download URL with date
        """
        today = datetime.now()
        
        # Try current month first, then previous months
        for month_offset in range(6):  # Check last 6 months
            try_date = datetime(today.year, today.month - month_offset, 1)
            if try_date.month <= 0:
                try_date = datetime(try_date.year - 1, 12 + try_date.month, 1)
            
            date_str = try_date.strftime("%Y-%m-%d")
            
            if dataset_type == "full":
                url = f"https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_csv_{date_str}.zip"
            elif dataset_type == "foundation":
                url = f"https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_{date_str}.zip"
            elif dataset_type == "branded":
                url = f"https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_csv_{date_str}.zip"
            else:
                raise ValueError(f"Unknown dataset type: {dataset_type}")
            
            # Test if URL exists
            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"Found latest dataset: {url}")
                    return url
            except requests.RequestException:
                continue
        
        # Fallback to generic URL without date
        fallback_url = self.download_urls.get(dataset_type)
        logger.warning(f"Could not find dated URL, using fallback: {fallback_url}")
        return fallback_url

    def download_file(self, url: str, filename: str) -> Path:
        """
        Download a file with progress tracking.
        
        Args:
            url: URL to download from
            filename: Local filename to save as
            
        Returns:
            Path to downloaded file
        """
        file_path = self.download_dir / filename
        
        # Skip if file already exists and is recent (less than 7 days old)
        if file_path.exists():
            file_age = time.time() - file_path.stat().st_mtime
            if file_age < 7 * 24 * 3600:  # 7 days in seconds
                logger.info(f"Using existing file: {file_path}")
                return file_path
        
        logger.info(f"Downloading {url} to {file_path}")
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {percent:.1f}% ({downloaded:,} / {total_size:,} bytes)")
            
            logger.info(f"Download completed: {file_path}")
            return file_path
            
        except requests.RequestException as e:
            logger.error(f"Download failed: {e}")
            raise

    def extract_zip(self, zip_path: Path, extract_to: Optional[Path] = None) -> Path:
        """
        Extract ZIP file.
        
        Args:
            zip_path: Path to ZIP file
            extract_to: Directory to extract to (default: same directory as ZIP)
            
        Returns:
            Path to extracted directory
        """
        if extract_to is None:
            extract_to = zip_path.parent
        
        extract_dir = extract_to / zip_path.stem
        
        if extract_dir.exists() and any(extract_dir.iterdir()):
            logger.info(f"Using existing extracted directory: {extract_dir}")
            return extract_dir
        
        logger.info(f"Extracting {zip_path} to {extract_dir}")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            logger.info(f"Extraction completed: {extract_dir}")
            return extract_dir
            
        except zipfile.BadZipFile as e:
            logger.error(f"Bad ZIP file: {e}")
            raise

    def load_csv_with_fallback(self, csv_path: Path, encoding_list: List[str] = None) -> pd.DataFrame:
        """
        Load CSV file with multiple encoding fallbacks.
        
        Args:
            csv_path: Path to CSV file
            encoding_list: List of encodings to try
            
        Returns:
            Pandas DataFrame
        """
        if encoding_list is None:
            encoding_list = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encoding_list:
            try:
                logger.debug(f"Trying to load {csv_path} with encoding: {encoding}")
                df = pd.read_csv(csv_path, encoding=encoding, low_memory=False)
                logger.info(f"Successfully loaded {csv_path} with encoding: {encoding}")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError) as e:
                logger.debug(f"Failed with encoding {encoding}: {e}")
                continue
        
        raise ValueError(f"Could not load {csv_path} with any of the encodings: {encoding_list}")

    def consolidate_food_data(self, extracted_dir: Path) -> pd.DataFrame:
        """
        Consolidate food data from multiple CSV files.
        
        Args:
            extracted_dir: Directory containing extracted CSV files
            
        Returns:
            Consolidated DataFrame
        """
        logger.info("Starting food data consolidation")
        
        # Core files to load
        core_files = {
            'food': 'food.csv',
            'food_nutrient': 'food_nutrient.csv', 
            'nutrient': 'nutrient.csv',
            'food_category': 'food_category.csv'
        }
        
        # Optional files
        optional_files = {
            'branded_food': 'branded_food.csv',
            'foundation_food': 'foundation_food.csv',
            'sr_legacy_food': 'sr_legacy_food.csv'
        }
        
        # Load core data
        data = {}
        for key, filename in core_files.items():
            file_path = extracted_dir / filename
            if file_path.exists():
                logger.info(f"Loading {filename}")
                data[key] = self.load_csv_with_fallback(file_path)
                logger.info(f"Loaded {len(data[key])} rows from {filename}")
            else:
                logger.error(f"Required file not found: {filename}")
                raise FileNotFoundError(f"Required file not found: {file_path}")
        
        # Load optional data
        for key, filename in optional_files.items():
            file_path = extracted_dir / filename
            if file_path.exists():
                logger.info(f"Loading optional file: {filename}")
                data[key] = self.load_csv_with_fallback(file_path)
                logger.info(f"Loaded {len(data[key])} rows from {filename}")
            else:
                logger.warning(f"Optional file not found: {filename}")
        
        # Create nutrient lookup
        nutrient_lookup = data['nutrient'].set_index('id')['name'].to_dict()
        logger.info(f"Created nutrient lookup with {len(nutrient_lookup)} nutrients")
        
        # Create category lookup
        category_lookup = data['food_category'].set_index('id')['description'].to_dict()
        logger.info(f"Created category lookup with {len(category_lookup)} categories")
        
        # Process foods with nutrients
        logger.info("Processing food nutrient data...")
        
        # Group nutrients by food
        nutrient_groups = data['food_nutrient'].groupby('fdc_id')
        
        consolidated_foods = []
        foods_processed = 0
        
        for fdc_id, food_row in data['food'].iterrows():
            foods_processed += 1
            if foods_processed % 10000 == 0:
                logger.info(f"Processed {foods_processed:,} foods")
            
            food_id = food_row['fdc_id']
            
            # Get basic food info
            food_info = {
                'fdc_id': food_id,
                'description': food_row.get('description', ''),
                'data_type': food_row.get('data_type', ''),
                'food_category_id': food_row.get('food_category_id'),
                'food_category': category_lookup.get(food_row.get('food_category_id'), ''),
                'publication_date': food_row.get('publication_date', '')
            }
            
            # Add branded food info if available
            if 'branded_food' in data:
                branded_info = data['branded_food'][data['branded_food']['fdc_id'] == food_id]
                if not branded_info.empty:
                    branded_row = branded_info.iloc[0]
                    food_info.update({
                        'brand_owner': branded_row.get('brand_owner', ''),
                        'brand_name': branded_row.get('brand_name', ''),
                        'ingredients': branded_row.get('ingredients', ''),
                        'serving_size': branded_row.get('serving_size'),
                        'serving_size_unit': branded_row.get('serving_size_unit', ''),
                        'household_serving_fulltext': branded_row.get('household_serving_fulltext', '')
                    })
            
            # Get nutrients for this food
            if food_id in nutrient_groups.groups:
                food_nutrients = nutrient_groups.get_group(food_id)
                
                # Create nutrient dictionary
                nutrients = {}
                for _, nutrient_row in food_nutrients.iterrows():
                    nutrient_id = nutrient_row['nutrient_id']
                    nutrient_name = nutrient_lookup.get(nutrient_id, f'Unknown_{nutrient_id}')
                    nutrients[nutrient_name] = nutrient_row.get('amount', 0)
                
                food_info['nutrients'] = nutrients
            else:
                food_info['nutrients'] = {}
            
            consolidated_foods.append(food_info)
        
        logger.info(f"Completed processing {foods_processed:,} foods")
        
        # Convert to DataFrame
        logger.info("Converting to DataFrame...")
        consolidated_df = pd.DataFrame(consolidated_foods)
        
        logger.info(f"Consolidation complete: {len(consolidated_df)} foods consolidated")
        return consolidated_df

    def save_consolidated_data(self, df: pd.DataFrame, format_type: str = "both") -> List[Path]:
        """
        Save consolidated data in various formats.
        
        Args:
            df: Consolidated DataFrame
            format_type: Format to save ('csv', 'json', 'both')
            
        Returns:
            List of saved file paths
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []
        
        if format_type in ["csv", "both"]:
            # Save as CSV (flattened nutrients)
            csv_path = self.data_dir / f"usda_food_consolidated_{timestamp}.csv"
            logger.info(f"Saving CSV to {csv_path}")
            
            # Flatten nutrients into separate columns
            csv_df = df.copy()
            
            # Extract common nutrients into separate columns
            common_nutrients = [
                'Energy', 'Protein', 'Total lipid (fat)', 'Carbohydrate, by difference',
                'Fiber, total dietary', 'Sugars, total including NLEA', 'Sodium, Na',
                'Calcium, Ca', 'Iron, Fe', 'Vitamin C, total ascorbic acid'
            ]
            
            for nutrient in common_nutrients:
                csv_df[f'nutrient_{nutrient.lower().replace(",", "").replace(" ", "_")}'] = csv_df['nutrients'].apply(
                    lambda x: x.get(nutrient, 0) if isinstance(x, dict) else 0
                )
            
            # Remove the nested nutrients column for CSV
            csv_df = csv_df.drop('nutrients', axis=1)
            
            csv_df.to_csv(csv_path, index=False, encoding='utf-8')
            saved_files.append(csv_path)
            logger.info(f"CSV saved: {csv_path}")
        
        if format_type in ["json", "both"]:
            # Save as JSON (with nested nutrients)
            json_path = self.data_dir / f"usda_food_consolidated_{timestamp}.json"
            logger.info(f"Saving JSON to {json_path}")
            
            # Convert DataFrame to JSON-friendly format
            json_data = df.to_dict('records')
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
            saved_files.append(json_path)
            logger.info(f"JSON saved: {json_path}")
        
        # Also save a summary
        summary_path = self.data_dir / f"usda_food_summary_{timestamp}.txt"
        with open(summary_path, 'w') as f:
            f.write(f"USDA Food Database Consolidation Summary\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Total foods: {len(df):,}\n")
            f.write(f"Data types: {df['data_type'].value_counts().to_string()}\n\n")
            f.write(f"Top categories: {df['food_category'].value_counts().head(10).to_string()}\n\n")
            
            if 'brand_owner' in df.columns:
                f.write(f"Top brands: {df['brand_owner'].value_counts().head(10).to_string()}\n\n")
        
        saved_files.append(summary_path)
        logger.info(f"Summary saved: {summary_path}")
        
        return saved_files

    def download_and_consolidate(self, dataset_type: str = "full", save_format: str = "both") -> List[Path]:
        """
        Main method to download and consolidate USDA food data.
        
        Args:
            dataset_type: Type of dataset to download ('full', 'foundation', 'branded')
            save_format: Format to save data ('csv', 'json', 'both')
            
        Returns:
            List of saved file paths
        """
        logger.info(f"Starting USDA food data download and consolidation")
        logger.info(f"Dataset type: {dataset_type}")
        logger.info(f"Save format: {save_format}")
        
        try:
            # Get latest download URL
            download_url = self.get_latest_download_url(dataset_type)
            
            # Download the ZIP file
            zip_filename = f"usda_food_data_{dataset_type}_{datetime.now().strftime('%Y%m%d')}.zip"
            zip_path = self.download_file(download_url, zip_filename)
            
            # Extract the ZIP file
            extracted_dir = self.extract_zip(zip_path)
            
            # Find the actual data directory (may be nested)
            data_dirs = [d for d in extracted_dir.iterdir() if d.is_dir() and 'csv' in d.name.lower()]
            if data_dirs:
                actual_data_dir = data_dirs[0]
            else:
                actual_data_dir = extracted_dir
            
            logger.info(f"Using data directory: {actual_data_dir}")
            
            # Consolidate the data
            consolidated_df = self.consolidate_food_data(actual_data_dir)
            
            # Save consolidated data
            saved_files = self.save_consolidated_data(consolidated_df, save_format)
            
            logger.info("=" * 60)
            logger.info("🎉 USDA Food Database Download and Consolidation Complete!")
            logger.info(f"📊 Total foods processed: {len(consolidated_df):,}")
            logger.info("📁 Files saved:")
            for file_path in saved_files:
                logger.info(f"   • {file_path}")
            logger.info("=" * 60)
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Error during download and consolidation: {e}")
            raise

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download and consolidate USDA Food Database")
    parser.add_argument("--dataset", choices=["full", "foundation", "branded"], 
                       default="full", help="Dataset type to download")
    parser.add_argument("--format", choices=["csv", "json", "both"], 
                       default="both", help="Output format")
    parser.add_argument("--data-dir", default="../data", 
                       help="Directory to save processed data")
    parser.add_argument("--download-dir", default="../downloads", 
                       help="Directory for temporary downloads")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🍎 USDA Food Database Downloader")
    print("=" * 50)
    print(f"Dataset: {args.dataset}")
    print(f"Format: {args.format}")
    print(f"Data directory: {args.data_dir}")
    print("=" * 50)
    
    try:
        downloader = USDAFoodDownloader(
            data_dir=args.data_dir,
            download_dir=args.download_dir
        )
        
        saved_files = downloader.download_and_consolidate(
            dataset_type=args.dataset,
            save_format=args.format
        )
        
        print("\n✅ Success! Files saved:")
        for file_path in saved_files:
            print(f"  📄 {file_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Full error details:")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
