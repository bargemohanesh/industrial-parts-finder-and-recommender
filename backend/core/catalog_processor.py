"""
Catalog Processing Module for Industrial Parts Product Finder
Extracts products from PDF catalogs
"""

import PyPDF2
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class Product:
    product_id: str
    name: str
    description: str
    category: str
    reference_number: str
    page_number: int
    catalog_source: str
    additional_info: str = ""

    def to_dict(self):
        return asdict(self)

    def to_searchable_text(self) -> str:
        """Create rich searchable text representation"""
        return f"""
Product Name: {self.name}
Reference Number: {self.reference_number}
Category: {self.category}
Description: {self.description}
Additional Information: {self.additional_info}
Found on page {self.page_number} of {self.catalog_source}
Product ID: {self.product_id}
        """.strip()


class CatalogProcessor:
    def __init__(self, config):
        self.config = config
        self.products = []

    def process_labels_catalog(self) -> List[Product]:
        """Process Labels & Decals catalog"""
        print("Processing Labels & Decals catalog...")
        catalog_path = self.config.get_full_path(self.config.CATALOG_PDF_1)

        products = self._extract_from_pdf(
            catalog_path,
            catalog_name="Labels & Signs",
            category="Labels & Decals"
        )

        self.products.extend(products)
        print(f"Extracted {len(products)} products from Labels catalog")
        return products

    def process_handling_catalog(self) -> List[Product]:
        """Process Handling Equipment catalog"""
        print("Processing Handling Equipment catalog...")
        catalog_path = self.config.get_full_path(self.config.CATALOG_PDF_2)

        products = self._extract_from_pdf(
            catalog_path,
            catalog_name="Handling Equipment & Accessories",
            category="Handling Equipment"
        )

        self.products.extend(products)
        print(f"Extracted {len(products)} products from Handling catalog")
        return products

    def _extract_from_pdf(self, pdf_path: Path, catalog_name: str, category: str) -> List[Product]:
        """Extract product information from PDF"""
        products = []

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                print(f"Processing {total_pages} pages from {pdf_path.name}...")

                for page_num in range(total_pages):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()

                        if text.strip():
                            # Extract products from page text
                            page_products = self._parse_page_content(
                                text,
                                page_num + 1,
                                pdf_path.name,
                                category
                            )
                            products.extend(page_products)

                    except Exception as e:
                        print(f"Error processing page {page_num + 1}: {e}")
                        continue

                    # Progress indicator
                    if (page_num + 1) % 50 == 0:
                        print(f"  Processed {page_num + 1}/{total_pages} pages...")

        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")

        return products

    def _parse_page_content(self, text: str, page_num: int,
                           source: str, category: str) -> List[Product]:
        """Parse text content and extract product information"""
        products = []

        # Split text into lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Strategy 1: Look for reference numbers (common pattern in catalogs)
        ref_pattern = r'\b([A-Z]{2,}\d{4,}[-]?[A-Z0-9]*|\d{5,}[-]?[A-Z0-9]+)\b'
        refs_found = re.findall(ref_pattern, text)

        if refs_found:
            # Create products based on reference numbers found
            for i, ref in enumerate(set(refs_found)):  # Use set to avoid duplicates
                # Find context around reference
                ref_context = self._extract_context_around_reference(text, ref)

                product = Product(
                    product_id=f"{category[:3].upper()}-{ref}-P{page_num}",
                    name=self._extract_product_name(ref_context, ref),
                    description=self._extract_description(ref_context),
                    category=category,
                    reference_number=ref,
                    page_number=page_num,
                    catalog_source=source,
                    additional_info=ref_context[:200]  # First 200 chars as context
                )
                products.append(product)

        # Strategy 2: If no refs found, create general page-level product
        if not products and len(text) > 100:
            # Extract potential product names (capitalized phrases)
            potential_names = re.findall(r'\b[A-Z][A-Z\s]{3,20}\b', text)

            if potential_names:
                product = Product(
                    product_id=f"{category[:3].upper()}-PAGE-{page_num}",
                    name=potential_names[0].strip() if potential_names else f"Product from page {page_num}",
                    description=text[:500],  # First 500 chars
                    category=category,
                    reference_number=f"REF-PAGE-{page_num}",
                    page_number=page_num,
                    catalog_source=source,
                    additional_info=f"Full page {page_num} content"
                )
                products.append(product)

        return products

    def _extract_context_around_reference(self, text: str, ref: str) -> str:
        """Extract text context around a reference number"""
        # Find position of reference
        pos = text.find(ref)
        if pos == -1:
            return ""

        # Get 300 characters before and after
        start = max(0, pos - 300)
        end = min(len(text), pos + 300)

        return text[start:end].strip()

    def _extract_product_name(self, context: str, ref: str) -> str:
        """Extract product name from context"""
        # Look for text before the reference (likely the product name)
        lines = context.split('\n')

        for i, line in enumerate(lines):
            if ref in line and i > 0:
                # Previous line might be the name
                prev_line = lines[i-1].strip()
                if len(prev_line) > 5 and len(prev_line) < 100:
                    return prev_line

        # Fallback: look for capitalized words
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', context)
        if words:
            return ' '.join(words[:5])  # First few words

        return f"Product {ref}"

    def _extract_description(self, context: str) -> str:
        """Extract product description from context"""
        # Clean and return context as description
        description = ' '.join(context.split())  # Remove extra whitespace
        return description[:400]  # Limit length

    def create_searchable_documents(self) -> List[Dict]:
        """Convert products to searchable document format"""
        documents = []

        for product in self.products:
            documents.append({
                'content': product.to_searchable_text(),
                'product': product,
                'metadata': {
                    'product_id': product.product_id,
                    'reference': product.reference_number,
                    'category': product.category,
                    'page': product.page_number,
                    'source': product.catalog_source
                }
            })

        return documents

    def export_products(self):
        """Export products to CSV and JSON"""
        output_dir = Path(self.config.PROCESSED_FOLDER)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export to CSV
        df = pd.DataFrame([p.to_dict() for p in self.products])
        csv_path = output_dir / "products.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"Exported {len(df)} products to {csv_path}")

        # Export to JSON
        json_path = output_dir / "products.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([p.to_dict() for p in self.products], f, indent=2, ensure_ascii=False)
        print(f"Exported products to {json_path}")

        return csv_path, json_path

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        stats = {
            'total_products': len(self.products),
            'by_category': {},
            'by_catalog': {}
        }

        for product in self.products:
            # Count by category
            stats['by_category'][product.category] = \
                stats['by_category'].get(product.category, 0) + 1

            # Count by catalog
            stats['by_catalog'][product.catalog_source] = \
                stats['by_catalog'].get(product.catalog_source, 0) + 1

        return stats