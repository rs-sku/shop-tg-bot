# Shop TG bot
## Usage:
1. Create venv: `python -m venv .venv`
2. Activate venv: `source .venv/bin/activate` (on Windows: `.venv\Scripts\activate`)
3. Install dependencies `pip install -r requirements txt`
4. Create `.env` using `.env.example`
5. Up db `docker-compose up -d`
6. Run bot `python src/main.py`
7. Load initial data if needed `python src/scripts.py`