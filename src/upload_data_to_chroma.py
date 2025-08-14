#!/usr/bin/env python3
"""
Upload USDA Food Data to Chroma Vector Database
This script replaces the Pinecone implementation with ChromaDB for vector storage and similarity search.
"""

import os
import csv
import json
import logging
import argparse
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction, SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChromaFoodDataUploader:
    """
    A class to handle uploading USDA food data to ChromaDB with vector embeddings.
    """
    
    def __init__(
        self,
        collection_name: str = "usda_food_data",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: Optional[str] = None,
        use_openai_embeddings: bool = False
    ):
        """
        Initialize the ChromaFoodDataUploader.
        
        Args:
            collection_name: Name of the Chroma collection
            embedding_model: Model to use for embeddings
            persist_directory: Directory to persist the database (None for in-memory)
            use_openai_embeddings: Whether to use OpenAI embeddings instead of sentence transformers
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.use_openai_embeddings = use_openai_embeddings
        
        # Initialize Chroma client
        if persist_directory:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            self.client = chromadb.Client(
                settings=Settings(anonymized_telemetry=False)
            )
        
        # Set up embedding function
        if use_openai_embeddings:
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI embeddings")
            self.embedding_function = OpenAIEmbeddingFunction(
                api_key=openai_api_key,
                model_name="text-embedding-ada-002"
            )
        else:
            self.embedding_function = SentenceTransformerEmbeddingFunction(
                model_name=embedding_model
            )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "USDA Food Data with nutritional information"}
        )
        
        logger.info(f"Initialized ChromaDB collection: {collection_name}")
        
    def prepare_food_document(self, food_item: Dict[str, Any]) -> str:
        """
        Prepare a food item as a text document for embedding.
        
        Args:
            food_item: Dictionary containing food data
            
        Returns:
            Formatted text document
        """
        food_name = food_item.get('food_name', '')
        carbs = food_item.get('carbohydrates_g', '')
        serving_size = food_item.get('serving_size', '')
        
        # Create a rich text representation for better embeddings
        document = f"Food: {food_name}"
        
        if carbs:
            document += f" | Carbohydrates: {carbs}g"
        if serving_size:
            document += f" | Serving Size: {serving_size}"
            
        # Add any additional nutritional information if available
        for key, value in food_item.items():
            if key not in ['food_name', 'carbohydrates_g', 'serving_size'] and value:
                # Format the key to be more readable
                formatted_key = key.replace('_', ' ').title()
                document += f" | {formatted_key}: {value}"
        
        return document
    
    def load_csv_data(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Load data from CSV file.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            List of food item dictionaries
        """
        food_items = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    food_items.append(dict(row))
            
            logger.info(f"Loaded {len(food_items)} food items from {csv_path}")
            return food_items
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            raise
    
    def upload_data(
        self,
        data: List[Dict[str, Any]],
        batch_size: int = 100,
        start_id: int = 0
    ) -> None:
        """
        Upload food data to Chroma collection.
        
        Args:
            data: List of food item dictionaries
            batch_size: Number of items to process in each batch
            start_id: Starting ID for the items (useful for incremental uploads)
        """
        total_items = len(data)
        logger.info(f"Starting upload of {total_items} items to Chroma collection")
        
        for i in range(0, total_items, batch_size):
            batch = data[i:i + batch_size]
            batch_ids = []
            batch_documents = []
            batch_metadatas = []
            
            for j, food_item in enumerate(batch):
                item_id = str(start_id + i + j)
                document = self.prepare_food_document(food_item)
                
                # Prepare metadata (ChromaDB requires all values to be strings, numbers, or booleans)
                metadata = {}
                for key, value in food_item.items():
                    if value is not None and value != '':
                        # Convert to appropriate type
                        if isinstance(value, str):
                            # Try to convert numeric strings to float
                            try:
                                if '.' in value or value.replace('.', '').isdigit():
                                    metadata[key] = float(value)
                                else:
                                    metadata[key] = value
                            except (ValueError, AttributeError):
                                metadata[key] = value
                        else:
                            metadata[key] = value
                
                batch_ids.append(item_id)
                batch_documents.append(document)
                batch_metadatas.append(metadata)
            
            # Add batch to collection
            try:
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                
                logger.info(f"Uploaded batch {i//batch_size + 1}/{(total_items-1)//batch_size + 1} "
                           f"({len(batch)} items)")
                
            except Exception as e:
                logger.error(f"Error uploading batch {i//batch_size + 1}: {e}")
                raise
        
        logger.info(f"Successfully uploaded all {total_items} items to Chroma collection")
    
    def search_similar_foods(
        self,
        query: str,
        n_results: int = 10,
        include_metadata: bool = True,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar foods based on a query.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            include_metadata: Whether to include metadata in results
            where_filter: Optional metadata filter
            
        Returns:
            Search results from ChromaDB
        """
        include_list = ["documents", "distances"]
        if include_metadata:
            include_list.append("metadatas")
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=include_list,
                where=where_filter
            )
            
            logger.info(f"Found {len(results['ids'][0])} results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching for similar foods: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "embedding_model": self.embedding_model,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise
    
    def delete_collection(self) -> None:
        """Delete the collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise

def main():
    """Main function to handle command line arguments and execute upload."""
    parser = argparse.ArgumentParser(description="Upload USDA food data to ChromaDB")
    parser.add_argument(
        "--csv_path",
        type=str,
        default="../data/usda_carbs_complete.csv",
        help="Path to the CSV file containing food data"
    )
    parser.add_argument(
        "--collection_name",
        type=str,
        default="usda_food_data",
        help="Name of the Chroma collection"
    )
    parser.add_argument(
        "--persist_directory",
        type=str,
        default="../data/chroma_db",
        help="Directory to persist the ChromaDB database"
    )
    parser.add_argument(
        "--embedding_model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence transformer model for embeddings"
    )
    parser.add_argument(
        "--use_openai_embeddings",
        action="store_true",
        help="Use OpenAI embeddings instead of sentence transformers"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=100,
        help="Batch size for uploading data"
    )
    parser.add_argument(
        "--sample_size",
        type=int,
        help="Limit the number of records to upload (for testing)"
    )
    parser.add_argument(
        "--delete_existing",
        action="store_true",
        help="Delete existing collection before uploading"
    )
    
    args = parser.parse_args()
    
    # Validate CSV path
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    # Create persist directory if it doesn't exist
    persist_dir = Path(args.persist_directory)
    persist_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize uploader
        uploader = ChromaFoodDataUploader(
            collection_name=args.collection_name,
            embedding_model=args.embedding_model,
            persist_directory=str(persist_dir),
            use_openai_embeddings=args.use_openai_embeddings
        )
        
        # Delete existing collection if requested
        if args.delete_existing:
            try:
                uploader.delete_collection()
                # Recreate the uploader with a fresh collection
                uploader = ChromaFoodDataUploader(
                    collection_name=args.collection_name,
                    embedding_model=args.embedding_model,
                    persist_directory=str(persist_dir),
                    use_openai_embeddings=args.use_openai_embeddings
                )
            except Exception as e:
                logger.warning(f"Could not delete existing collection: {e}")
        
        # Load data
        food_data = uploader.load_csv_data(str(csv_path))
        
        # Limit sample size if specified
        if args.sample_size:
            food_data = food_data[:args.sample_size]
            logger.info(f"Limited to {args.sample_size} records for testing")
        
        # Upload data
        uploader.upload_data(
            data=food_data,
            batch_size=args.batch_size
        )
        
        # Print collection stats
        stats = uploader.get_collection_stats()
        logger.info(f"Collection stats: {json.dumps(stats, indent=2)}")
        
        # Example search
        logger.info("\n" + "="*50)
        logger.info("Example searches:")
        
        example_queries = [
            "high protein foods",
            "low carb vegetables",
            "fruits with vitamin C",
            "whole grain bread"
        ]
        
        for query in example_queries:
            results = uploader.search_similar_foods(query, n_results=3)
            logger.info(f"\nQuery: '{query}'")
            for i, (doc, distance) in enumerate(zip(results['documents'][0], results['distances'][0])):
                logger.info(f"  {i+1}. {doc[:100]}... (distance: {distance:.4f})")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()
