\# Industrial Parts Product Finder



AI-powered semantic search and recommendation system for industrial parts catalogs using RAG (Retrieval Augmented Generation).



\## Features



\- \*\*Natural Language Search\*\* - Describe what you're looking for in plain English

\- \*\*Semantic Understanding\*\* - AI understands context, not just keywords

\- \*\*Product Recommendations\*\* - "Frequently bought together" suggestions

\- \*\*Voice Input\*\* - Search using voice commands

\- \*\*PDF Catalog Processing\*\* - Extracts products from PDF catalogs automatically



\## Tech Stack



\- \*\*Backend:\*\* Python, FastAPI

\- \*\*AI/ML:\*\* Claude AI (Anthropic), Sentence Transformers, FAISS

\- \*\*Frontend:\*\* HTML, CSS, JavaScript

\- \*\*Vector Search:\*\* FAISS (Facebook AI Similarity Search)



\## Architecture

```

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐

│   Frontend      │────▶│   FastAPI        │────▶│   Claude AI     │

│   (HTML/JS)     │     │   Backend        │     │   (Response)    │

└─────────────────┘     └────────┬─────────┘     └─────────────────┘

&nbsp;                                │

&nbsp;                   ┌────────────┼────────────┐

&nbsp;                   ▼            ▼            ▼

&nbsp;             ┌─────────┐  ┌─────────┐  ┌─────────┐

&nbsp;             │  FAISS  │  │ Product │  │ Recomm- │

&nbsp;             │  Index  │  │ Catalog │  │ endation│

&nbsp;             └─────────┘  └─────────┘  └─────────┘

```



\## Setup



\### 1. Clone Repository

```bash

git clone https://github.com/YOUR\_USERNAME/industrial-parts-finder.git

cd industrial-parts-finder

```



\### 2. Create Virtual Environment

```bash

python -m venv venv

source venv/bin/activate  # Linux/Mac

venv\\Scripts\\activate     # Windows

```



\### 3. Install Dependencies

```bash

pip install -r requirements.txt

```



\### 4. Configure Environment

```bash

cp .env.example .env

\# Edit .env and add your Anthropic API key

```



\### 5. Add Sample Data



Place your PDF catalogs in the project root:

\- `sample\_catalog\_1.pdf` - Labels \& Signs catalog

\- `sample\_catalog\_2.pdf` - Handling Equipment catalog

\- `sample\_purchases.csv` - Purchase history for recommendations



\### 6. Run Application

```bash

uvicorn backend.main:app --reload --port 8000

```



\### 7. Access Application



Open browser: http://localhost:8000



\## API Endpoints



| Endpoint | Method | Description |

|----------|--------|-------------|

| `/` | GET | Frontend UI |

| `/api/initialize` | POST | Initialize system |

| `/api/search` | POST | Search products |

| `/api/status` | GET | System status |

| `/api/health` | GET | Health check |



\## Usage



1\. Click "Initialize System" (first time only)

2\. Type your search query (e.g., "safety warning labels")

3\. View results with AI-generated response

4\. See product recommendations



\## Sample Queries



\- "safety warning label for forklift"

\- "fire safety signs"

\- "electrical hazard warning"

\- "handling equipment for warehouse"



\## Project Structure

```

# Industrial Parts Product Finder & Recommender/

├── backend/

│   ├── config.py              # Configuration

│   ├── main.py                # FastAPI application

│   └── core/

│       ├── catalog\_processor.py   # PDF processing

│       ├── product\_search.py      # FAISS search

│       ├── query\_processor.py     # AI responses

│       └── recommender.py         # Recommendations

├── frontend/

│   ├── index.html             # Main UI

│   ├── script.js              # Frontend logic

│   └── style.css              # Styles

├── sample\_data/               # Sample data (not included)

├── requirements.txt           # Python dependencies

├── .env.example              # Environment template

└── README.md                 # This file

```



\## License



MIT License



\## Author



Built as a demonstration of RAG-based product search systems.

