"""
Query Processor with Claude AI Integration
Handles natural language queries and generates intelligent responses
"""

import anthropic
import time
from typing import Dict, List, Optional
from enum import Enum

class QueryType(Enum):
    PRODUCT_SEARCH = "product_search"
    GREETING = "greeting"
    HELP = "help"
    OUT_OF_CONTEXT = "out_of_context"
    ERROR = "error"

class QueryResult:
    def __init__(self, response: str, query_type: QueryType,
                 products: List = None, recommendations: List = None,
                 processing_time: float = 0.0):
        self.response = response
        self.query_type = query_type
        self.products = products or []
        self.recommendations = recommendations or []
        self.processing_time = processing_time

class QueryProcessor:
    def __init__(self, config):
        self.config = config
        self.claude_client = None
        self._init_claude()

    def _init_claude(self):
        """Initialize Claude AI client"""
        try:
            if self.config.ANTHROPIC_API_KEY and self.config.ANTHROPIC_API_KEY != "":
                self.claude_client = anthropic.Anthropic(
                    api_key=self.config.ANTHROPIC_API_KEY
                )
                print("Claude AI client initialized")
            else:
                print("Warning: Claude API key not configured - AI responses will be limited")
        except Exception as e:
            print(f"Error initializing Claude: {e}")

    def process_query(self, query: str, search_engine, recommender,
                     products_list: List) -> QueryResult:
        """
        Process user query and return appropriate response
        """
        start_time = time.time()

        # Check query type
        query_lower = query.lower().strip()

        # Handle greetings
        if any(word in query_lower for word in ['hi', 'hello', 'hey', 'greetings']):
            return QueryResult(
                response=self._handle_greeting(),
                query_type=QueryType.GREETING,
                processing_time=time.time() - start_time
            )

        # Handle help requests
        if any(word in query_lower for word in ['help', 'how to', 'what can']):
            return QueryResult(
                response=self._handle_help(),
                query_type=QueryType.HELP,
                processing_time=time.time() - start_time
            )

        # Check if query looks like a reference number
        if self._is_reference_query(query):
            return self._handle_reference_search(
                query, search_engine, recommender, products_list, start_time
            )

        # Standard product search
        return self._handle_product_search(
            query, search_engine, recommender, products_list, start_time
        )

    def _is_reference_query(self, query: str) -> bool:
        """Check if query is a reference number lookup"""
        import re
        # Pattern for reference numbers
        ref_pattern = r'^[A-Z]{2,}\d{4,}[-]?[A-Z0-9]*$|^\d{5,}[-]?[A-Z0-9]+$'
        return bool(re.match(ref_pattern, query.strip().upper()))

    def _handle_greeting(self) -> str:
        return """**Welcome to Industrial Parts Product Finder!**

I'm here to help you find the right products from our extensive catalog of:
- Labels & Signs
- Handling Equipment & Accessories

**How to use:**
- Describe what you're looking for (e.g., "safety warning label")
- Mention your use case (e.g., "label for forklift")
- Provide a reference number for exact matches
- Ask about product recommendations

Try asking something like:
- "I need a warning label for a forklift"
- "Show me safety signs"
- "What labels are available for electrical hazards?"

What can I help you find today?"""

    def _handle_help(self) -> str:
        return """**How to Find Products**

**Search Methods:**
1. **Describe what you need:**
   - "fire safety label"
   - "danger warning sign"
   - "forklift attachment"

2. **Describe your scenario:**
   - "I need a label for electrical equipment"
   - "What signs do I need for warehouse safety?"

3. **Use reference numbers:**
   - Just type the reference number directly

4. **Browse by category:**
   - "show me labels"
   - "what handling equipment do you have?"

**Tips:**
- Be specific about colors, sizes, or purposes
- Mention the equipment or application
- Use simple, clear language

**Recommendations:**
After finding a product, I'll suggest items frequently bought together!

Ready to search? Just type what you're looking for."""

    def _handle_reference_search(self, query: str, search_engine,
                                 recommender, products_list, start_time) -> QueryResult:
        """Handle search by reference number"""
        reference = query.strip().upper()

        # Search by reference
        result = search_engine.search_by_reference(reference)

        if not result:
            # Fallback to semantic search
            return self._handle_product_search(
                query, search_engine, recommender, products_list, start_time
            )

        product = result['product']

        # Get recommendations
        recommendations = recommender.get_recommendations_with_products(
            product.reference_number,
            products_list,
            top_n=5
        )

        # Build response
        response = f"""**Found Product: {product.name}**

**Reference:** {product.reference_number}
**Category:** {product.category}
**Location:** Page {product.page_number} in {product.catalog_source}

**Description:**
{product.description[:300]}...

"""

        if recommendations:
            response += "\n**Frequently Bought Together:**\n"
            for rec in recommendations:
                rec_prod = rec['product']
                response += f"- {rec_prod.name} ({rec_prod.reference_number}) - {rec['reason']}\n"

        return QueryResult(
            response=response,
            query_type=QueryType.PRODUCT_SEARCH,
            products=[product],
            recommendations=recommendations,
            processing_time=time.time() - start_time
        )

    def _handle_product_search(self, query: str, search_engine,
                              recommender, products_list, start_time) -> QueryResult:
        """Handle semantic product search"""

        # Perform search
        search_results = search_engine.search(query, top_k=5)

        if not search_results:
            return QueryResult(
                response=self._handle_no_results(query),
                query_type=QueryType.OUT_OF_CONTEXT,
                processing_time=time.time() - start_time
            )

        # Extract products
        products = [r['product'] for r in search_results]

        # Get recommendations for top result
        recommendations = []
        if products:
            recommendations = recommender.get_recommendations_with_products(
                products[0].reference_number,
                products_list,
                top_n=3
            )

        # Generate response with Claude if available
        if self.claude_client:
            response = self._generate_ai_response(query, search_results, recommendations)
        else:
            response = self._generate_basic_response(query, search_results, recommendations)

        return QueryResult(
            response=response,
            query_type=QueryType.PRODUCT_SEARCH,
            products=products,
            recommendations=recommendations,
            processing_time=time.time() - start_time
        )

    def _generate_ai_response(self, query: str, search_results: List[Dict],
                             recommendations: List[Dict]) -> str:
        """Generate AI-powered response using Claude"""

        # Prepare context
        context = "# Search Results:\n\n"
        for i, result in enumerate(search_results, 1):
            product = result['product']
            context += f"{i}. **{product.name}**\n"
            context += f"   - Reference: {product.reference_number}\n"
            context += f"   - Category: {product.category}\n"
            context += f"   - Page: {product.page_number}\n"
            context += f"   - Description: {product.description[:200]}\n"
            context += f"   - Match Score: {result['score']:.2f}\n\n"

        if recommendations:
            context += "\n# Recommended Related Products:\n\n"
            for rec in recommendations:
                rec_prod = rec['product']
                context += f"- {rec_prod.name} (Ref: {rec_prod.reference_number})\n"
                context += f"  Reason: {rec['reason']}\n"

        # Create prompt
        prompt = f"""You are a helpful industrial parts catalog assistant. A customer is searching for products.

Customer Query: "{query}"

{context}

Please provide a helpful, concise response that:
1. Confirms what the customer is looking for
2. Presents the top 2-3 most relevant products with their key details
3. Mentions related products if available
4. Keeps the tone professional but friendly
5. Limits response to 3-4 short paragraphs

Format product details clearly with reference numbers and page locations."""

        try:
            response = self.claude_client.messages.create(
                model=self.config.CLAUDE_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            print(f"Claude API error: {e}")
            return self._generate_basic_response(query, search_results, recommendations)

    def _generate_basic_response(self, query: str, search_results: List[Dict],
                                 recommendations: List[Dict]) -> str:
        """Generate basic response without AI"""

        response = f"**Search Results for:** \"{query}\"\n\n"
        response += f"Found {len(search_results)} matching products:\n\n"

        for i, result in enumerate(search_results[:3], 1):
            product = result['product']
            response += f"**{i}. {product.name}**\n"
            response += f"   Reference: {product.reference_number}\n"
            response += f"   Category: {product.category}\n"
            response += f"   Page: {product.page_number} in {product.catalog_source}\n"
            response += f"   Match: {result['score']:.0%}\n"

            # Add brief description
            desc = product.description[:150]
            if len(product.description) > 150:
                desc += "..."
            response += f"   {desc}\n\n"

        if recommendations:
            response += "\n**Customers Also Bought:**\n"
            for rec in recommendations[:3]:
                rec_prod = rec['product']
                response += f"- {rec_prod.name} (Ref: {rec_prod.reference_number})\n"

        return response

    def _handle_no_results(self, query: str) -> str:
        return f"""**No products found matching:** "{query}"

**Suggestions:**
- Try different keywords (e.g., "warning" instead of "caution")
- Search by category: "labels", "signs", "handling equipment"
- Use broader terms (e.g., "safety label" instead of "red safety warning label")
- Check if you have the correct reference number

**Popular Categories:**
- Safety Labels & Signs
- Warning Labels
- Handling Equipment
- Forklift Accessories

Try rephrasing your search or ask for help!"""