"""
Configuration for Industrial Parts Product Finder
"""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    # API Configuration (loaded from environment variables)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-3-7-sonnet-20250219"
    
    # Data Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    CATALOG_PDF_1: str = "sample_catalog_1.pdf"  # Add your own PDF
    CATALOG_PDF_2: str = "sample_catalog_2.pdf"  # Add your own PDF
    RECOMMENDATIONS_DATA: str = "sample_purchases.csv"  # Add your own CSV
    
    # Processed Data
    PROCESSED_FOLDER: str = "data/processed"
    CACHE_FOLDER: str = "cache"
    
    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Search Parameters
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    MAX_SEARCH_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.25
    
    # Recommendations
    TOP_N_RECOMMENDATIONS: int = 5
    MIN_RECOMMENDATION_SCORE: float = 2.0
    
    def __post_init__(self):
        self.BASE_DIR = Path(self.BASE_DIR)
        Path(self.CACHE_FOLDER).mkdir(exist_ok=True)
        Path(self.PROCESSED_FOLDER).mkdir(parents=True, exist_ok=True)
        
        # Validate API key
        if not self.ANTHROPIC_API_KEY:
            print("Warning: ANTHROPIC_API_KEY not set in environment variables")
    
    def get_full_path(self, filename: str) -> Path:
        """Get full path for data files"""
        return self.BASE_DIR / filename