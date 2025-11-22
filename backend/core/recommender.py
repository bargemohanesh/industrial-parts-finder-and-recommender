"""
Product Recommendation System
Based on frequently-bought-together data from dummy_purchases.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict, Counter

class ProductRecommender:
    def __init__(self, config):
        self.config = config
        self.recommendations_df = None
        self.associations = defaultdict(Counter)  # product_id -> {related_product: frequency}
        self.product_names = {}  # product_id -> name mapping
        
    def load_purchase_data(self) -> bool:
        """Load dummy_purchases.csv data"""
        try:
            data_path = self.config.get_full_path(self.config.RECOMMENDATIONS_DATA)
            print(f"Loading purchase data from {data_path}...")
            
            # Read CSV with various encoding attempts
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(data_path, encoding=encoding)
                    print(f"Successfully read with {encoding} encoding")
                    break
                except:
                    continue
            
            if df is None:
                print("Failed to read CSV with any encoding")
                return False
            
            self.recommendations_df = df
            print(f"Loaded {len(df)} purchase records")
            print(f"Columns: {list(df.columns)}")
            
            # Display sample
            print("\nSample data:")
            print(df.head())
            
            # Build associations
            self._build_associations()
            
            return True
            
        except Exception as e:
            print(f"Error loading purchase data: {e}")
            return False
    
    def _build_associations(self):
        """Build product association matrix from purchase data"""
        
        # Inspect column names to determine structure
        cols = list(self.recommendations_df.columns)
        print(f"\nAnalyzing columns: {cols}")
        
        # Common column name patterns
        possible_patterns = [
            ('product_id_1', 'product_id_2', 'frequency'),
            ('source_product', 'target_product', 'count'),
            ('item_a', 'item_b', 'frequency'),
            ('labels_product', 'handling_product', 'purchase_count'),
        ]
        
        # Try to identify column structure
        col_mapping = None
        for pattern in possible_patterns:
            if all(col in cols for col in pattern):
                col_mapping = pattern
                break
        
        if not col_mapping:
            # Fallback: use first 3 columns
            print("Using first 3 columns as: source, target, frequency")
            col_mapping = (cols[0], cols[1], cols[2] if len(cols) > 2 else None)
        
        src_col, tgt_col, freq_col = col_mapping
        print(f"Using columns: {src_col} -> {tgt_col} (frequency: {freq_col})")
        
        # Build associations
        for _, row in self.recommendations_df.iterrows():
            source = str(row[src_col]).strip()
            target = str(row[tgt_col]).strip()
            
            if freq_col:
                frequency = float(row[freq_col]) if pd.notna(row[freq_col]) else 1.0
            else:
                frequency = 1.0
            
            # Bidirectional associations
            self.associations[source][target] += frequency
            self.associations[target][source] += frequency
        
        print(f"\nBuilt associations for {len(self.associations)} products")
        
        # Show sample associations
        if self.associations:
            sample_key = list(self.associations.keys())[0]
            print(f"Sample: {sample_key} -> {dict(self.associations[sample_key])}")
    
    def get_recommendations(self, product_ref: str, top_n: int = None) -> List[Tuple[str, float]]:
        """
        Get recommended products for a given product reference
        Returns list of (product_ref, score) tuples
        """
        top_n = top_n or self.config.TOP_N_RECOMMENDATIONS
        
        # Try exact match first
        if product_ref in self.associations:
            recs = self.associations[product_ref]
        else:
            # Try fuzzy matching (partial reference)
            matched_key = None
            for key in self.associations.keys():
                if product_ref in key or key in product_ref:
                    matched_key = key
                    break
            
            if matched_key:
                recs = self.associations[matched_key]
            else:
                return []
        
        # Filter by minimum score and sort
        filtered_recs = [
            (prod, score) 
            for prod, score in recs.items() 
            if score >= self.config.MIN_RECOMMENDATION_SCORE
        ]
        
        # Sort by frequency (score)
        sorted_recs = sorted(filtered_recs, key=lambda x: x[1], reverse=True)
        
        return sorted_recs[:top_n]
    
    def get_recommendations_with_products(self, product_ref: str, 
                                         all_products: List, 
                                         top_n: int = None) -> List[Dict]:
        """
        Get recommendations with full product details
        """
        recommended_refs = self.get_recommendations(product_ref, top_n)
        
        if not recommended_refs:
            return []
        
        # Create product lookup by reference
        product_lookup = {}
        for p in all_products:
            # Try multiple reference formats
            product_lookup[p.reference_number] = p
            product_lookup[p.product_id] = p
        
        # Match recommendations to actual products
        results = []
        for rec_ref, score in recommended_refs:
            # Try to find matching product
            matched_product = None
            
            # Direct match
            if rec_ref in product_lookup:
                matched_product = product_lookup[rec_ref]
            else:
                # Fuzzy match
                for ref, prod in product_lookup.items():
                    if rec_ref in ref or ref in rec_ref:
                        matched_product = prod
                        break
            
            if matched_product:
                results.append({
                    'product': matched_product,
                    'score': score,
                    'reason': f'Frequently bought together ({int(score)} times)'
                })
        
        return results
    
    def get_stats(self) -> Dict:
        """Get recommendation statistics"""
        if not self.associations:
            return {'status': 'No data loaded'}
        
        total_associations = sum(len(v) for v in self.associations.values())
        
        return {
            'total_products': len(self.associations),
            'total_associations': total_associations,
            'avg_associations_per_product': total_associations / len(self.associations) if self.associations else 0,
            'sample_products': list(self.associations.keys())[:5]
        }