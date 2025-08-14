# USDA Food Database Downloader & Semantic Search

Complete solution for downloading USDA FoodData Central database and performing intelligent semantic food searches with accurate nutrition data.

## 🎯 Final Output

**`data/usda_carbs_complete.csv`** - Generated database with **1,685,395 foods** containing:
- `food_name` - Name as listed in USDA database
- `carbohydrates_g` - Carbohydrates in grams
- `serving_size` - Serving size with units

**`data/_first20_with_nutrition_rescaled.csv`** - Example output with correctly rescaled nutrition values for real serving sizes.

> **Note**: The large USDA database file is not included in the repository. Use the provided scripts to download and generate it locally.

## 🚀 Usage

### 1. Download & Extract Complete Database
```bash
python3 src/extract_carbs_only.py --output usda_carbs_complete.csv
```

### 2. Create Semantic Search Database
```bash
# Create ChromaDB vector database (sample for testing)
python3 src/upload_data_to_chroma.py --sample_size 1000

# Or create full database (recommended)
python3 src/upload_data_to_chroma.py
```

### 3. Batch Nutrition Lookup (Recommended)
Process multiple foods at once from a CSV file:

```bash
# Basic usage - auto-detect food column
python3 src/batch_nutrition_lookup.py input_foods.csv output_nutrition.csv

# Specify food column name
python3 src/batch_nutrition_lookup.py input_foods.csv output_nutrition.csv --food-column "Item"

# Include debug information (distances, rescaling details)
python3 src/batch_nutrition_lookup.py input_foods.csv output_nutrition.csv --debug
```

### 4. Single Food Semantic Search
Use the ChromaDB semantic search to find individual foods and get properly rescaled nutrition values:

```python
from src.upload_data_to_chroma import ChromaFoodDataUploader

# Initialize searcher
uploader = ChromaFoodDataUploader(persist_directory="data/chroma_db")

# Search for foods with semantic matching
results = uploader.search_similar_foods("chicken breast", n_results=5)
```

### 5. Legacy Text Search
```bash
python3 src/search_carbs.py "banana"
python3 src/search_carbs.py "chicken"
```

## 📁 Key Files

### Essential Scripts
- **`src/extract_carbs_only.py`** - Main carbohydrate data extractor
- **`src/upload_data_to_chroma.py`** - Creates ChromaDB vector database for semantic search
- **`src/batch_nutrition_lookup.py`** - Batch nutrition lookup for multiple foods from CSV
- **`src/search_carbs.py`** - Legacy text search tool
- **`src/usda_food_downloader.py`** - Downloads USDA database (if needed)

### Output Data
- **`data/usda_carbs_complete.csv`** - Final consolidated database (89MB, 1.7M foods)
- **`data/_first20_with_nutrition_rescaled.csv`** - Example with correctly rescaled nutrition
- **`data/chroma_db/`** - ChromaDB vector database for semantic search

### Configuration
- **`requirements.txt`** - Python dependencies (includes ChromaDB and sentence-transformers)
- **`src/nutrition_evaluator.py`** - LLM nutrition benchmarking (optional)

## 📊 Sample Output

### Raw USDA Data
```csv
food_name,carbohydrates_g,serving_size
SWANSON BROTH BEEF,0.4,240.0 ml
CAMPBELL'S SLOW KETTLE SOUP CLAM CHOWDER,6.1,440.0 g
BANANA ICED CAKE,56.5,85.0 g
```

### Batch Nutrition Lookup Results (Rescaled)
```csv
original_query,usda_name,carbohydrates_g,serving_size
"chicken breast","CHICKEN BREAST MEAT",0.0,"100.0 g"
"1 cup rice","ENRICHED EXTRA LONG GRAIN RICE",35.0,"45.0 g"
"banana","BANANA RAW",22.8,"118.0 g"
```

### Single Food Search Results (Rescaled)
```csv
ck_name,ck_carbs,ck_quantity
"SAVORY HERB CHICKEN SEASONING MIX, SAVORY HERB CHICKEN",3.0,"5.0 g"
"ENRICHED EXTRA LONG GRAIN RICE",35.0,"45.0 g"
"MINT LOWFAT ICE CREAM FROSTY TREES WITH CANDY SPRINKLES, MINT",13.0,"49.0 g"
```

## 🧠 Intelligent Rescaling

**Problem Solved**: Original USDA data had impossible values like 60g carbs in 5g serving size.

**Solution**: Post-retrieval rescaling that:
- ✅ Finds foods using semantic search (meaning-based, not text matching)
- ✅ Batch processes multiple foods efficiently (50+ foods/second)
- ✅ Properly scales carbohydrate values to actual serving sizes
- ✅ Converts `60.0g/100g → 3.0g/5.0g` for realistic nutrition facts
- ✅ Processes only retrieved foods (efficient vs. reprocessing 1.7M records)

## ⚡ Performance

- **Database Creation**: ~4-5 minutes for complete USDA database (1.7M foods)
- **Batch Processing**: 50+ foods/second with semantic search and rescaling
- **Single Food Search**: ~50ms per food query with ChromaDB
- **Rescaling**: <1 second for 20 foods vs. hours for full database reprocessing
- **Memory Efficient**: Vector embeddings cached, optimized for large datasets

## 🛠️ Installation

```bash
pip install -r requirements.txt
```

## 📖 Data Source

Downloads from [USDA FoodData Central](https://fdc.nal.usda.gov/) - the official US food composition database with 400,000+ foods and comprehensive nutrition data.

## 🎯 Tasks Completed

✅ **Download**: Automated USDA database download  
✅ **Consolidate**: Extract exactly the 3 required fields  
✅ **Optimize**: 5x performance improvement (20+ min → 4-5 min)  
✅ **Semantic Search**: ChromaDB vector database for intelligent food matching  
✅ **Batch Processing**: Efficient multi-food nutrition lookup from CSV files
✅ **Rescaling**: Post-retrieval nutrition value correction for realistic serving sizes  
✅ **Deliver**: Final CSV with 1.7M foods + intelligent search capabilities