"""
Product Search Engine using Vector Embeddings and FAISS
"""

import faiss
import numpy as np
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import hashlib

class ProductSearchEngine:
    def __init__(self, config):
        self.config = config
        self.embedder = None
        self.index = None
        self.documents = []
        self.cache_file = Path(config.CACHE_FOLDER) / "product_search_index.pkl"
        self._init_embedder()
        
    def _init_embedder(self):
        """Initialize sentence transformer model"""
        try:
            print(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
            self.embedder = SentenceTransformer(self.config.EMBEDDING_MODEL)
            print("Embedding model loaded successfully")
        except Exception as e:
            print(f"Error loading embedder: {e}")
            self.embedder = None
    
    def build_index(self, documents: List[Dict]) -> bool:
        """Build FAISS search index from product documents"""
        if not documents:
            print("No documents provided to build index")
            return False
        
        if not self.embedder:
            print("Embedder not initialized")
            return False
        
        try:
            # Check if we can load from cache
            if self._load_from_cache(documents):
                print("Loaded search index from cache")
                return True
            
            print(f"\nBuilding search index for {len(documents)} products...")
            
            # Extract text content for embedding
            texts = [doc['content'] for doc in documents]
            
            # Generate embeddings with progress
            print("Generating embeddings (this may take a few minutes)...")
            embeddings = self.embedder.encode(
                texts, 
                show_progress_bar=True,
                batch_size=32
            )
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings.astype('float32'))
            
            # Build FAISS index
            dimension = embeddings.shape[1]
            print(f"Building FAISS index with dimension {dimension}...")
            
            # Use IndexFlatIP for inner product (cosine similarity after normalization)
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(embeddings.astype('float32'))
            
            # Store documents
            self.documents = documents
            
            # Save to cache
            self._save_to_cache(documents)
            
            print(f"✓ Search index built successfully with {self.index.ntotal} products")
            return True
            
        except Exception as e:
            print(f"Error building search index: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search(self, query: str, top_k: int = None, 
               filter_category: str = None) -> List[Dict]:
        """
        Search for products matching the query
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            filter_category: Optional category filter
        
        Returns:
            List of search results with products and scores
        """
        if not self.index or not self.embedder:
            print("Search index not ready")
            return []
        
        top_k = top_k or self.config.MAX_SEARCH_RESULTS
        
        try:
            # Encode query
            query_embedding = self.embedder.encode([query])
            faiss.normalize_L2(query_embedding.astype('float32'))
            
            # Search - get more results than needed for filtering
            search_k = top_k * 3 if filter_category else top_k * 2
            scores, indices = self.index.search(
                query_embedding.astype('float32'), 
                min(search_k, len(self.documents))
            )
            
            # Format results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if score > self.config.SIMILARITY_THRESHOLD:
                    doc = self.documents[idx]
                    
                    # Apply category filter if specified
                    if filter_category:
                        if doc['metadata'].get('category', '').lower() != filter_category.lower():
                            continue
                    
                    results.append({
                        'product': doc['product'],
                        'score': float(score),
                        'metadata': doc['metadata'],
                        'snippet': self._create_snippet(doc['content'], query)
                    })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            print(f"Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _create_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Create a relevant snippet from content based on query"""
        # Simple snippet: first N characters
        snippet = content[:max_length]
        if len(content) > max_length:
            snippet += "..."
        return snippet
    
    def search_by_reference(self, reference: str) -> Optional[Dict]:
        """Search for a product by exact reference number"""
        for doc in self.documents:
            if doc['metadata'].get('reference', '').lower() == reference.lower():
                return {
                    'product': doc['product'],
                    'score': 1.0,
                    'metadata': doc['metadata'],
                    'snippet': doc['content'][:200]
                }
        return None
    
    def get_products_by_category(self, category: str, limit: int = 20) -> List[Dict]:
        """Get all products from a specific category"""
        results = []
        for doc in self.documents:
            if doc['metadata'].get('category', '').lower() == category.lower():
                results.append({
                    'product': doc['product'],
                    'score': 1.0,
                    'metadata': doc['metadata']
                })
                if len(results) >= limit:
                    break
        return results
    
    def _load_from_cache(self, documents: List[Dict]) -> bool:
        """Load index from cache if available and valid"""
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Verify cache validity using document hash
            doc_hash = self._compute_document_hash(documents)
            if cache_data.get('doc_hash') != doc_hash:
                print("Cache invalid (documents changed)")
                return False
            
            self.index = cache_data['index']
            self.documents = cache_data['documents']
            
            return True
            
        except Exception as e:
            print(f"Error loading cache: {e}")
            return False
    
    def _save_to_cache(self, documents: List[Dict]):
        """Save index to cache"""
        try:
            cache_data = {
                'index': self.index,
                'documents': self.documents,
                'doc_hash': self._compute_document_hash(documents)
            }
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            print(f"Saved search index to cache: {self.cache_file}")
            
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _compute_document_hash(self, documents: List[Dict]) -> str:
        """Compute hash of documents for cache validation"""
        # Hash based on number of documents and first/last document content
        if not documents:
            return ""
        
        hash_input = f"{len(documents)}{documents[0]['content'][:100]}{documents[-1]['content'][:100]}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def get_stats(self) -> Dict:
        """Get search engine statistics"""
        if not self.index:
            return {'status': 'Not initialized'}
        
        categories = {}
        for doc in self.documents:
            cat = doc['metadata'].get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            'total_documents': len(self.documents),
            'index_size': self.index.ntotal if self.index else 0,
            'categories': categories,
            'embedding_dimension': self.embedder.get_sentence_embedding_dimension() if self.embedder else 0,
            'cache_exists': self.cache_file.exists()
        }