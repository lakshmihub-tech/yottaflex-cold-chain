# YottaFlex Cold Chain Monitoring System



A Python and SQLite-based cold-chain monitoring application that tracks shipments, validates sensor readings, detects temperature and humidity excursions, and supports corrective actions.



## Features



- Shipment, product, container, and sensor records.

- Temperature and humidity monitoring.

- Product-specific threshold policies.

- Route stops and operational events.

- Data-quality checks and excursion records.

- Streamlit dashboard with Plotly charts.

- Corrective-action tracking.

- CSV exports.



## Technology Stack



- Python

- SQLite

- Pandas

- NumPy

- Streamlit

- Plotly

- Pytest



## Project Structure



yottaflex-cold-chain/

&#x20;   data/

&#x20;       cold_chain.db

&#x20;   src/

&#x20;       align_readings.py

&#x20;       dashboard.py

&#x20;       generate_data.py

&#x20;       generate_operations.py

&#x20;       init_db.py

&#x20;       main.py

&#x20;       quality_scenarios.py

&#x20;       schema.sql

&#x20;       verify_db.py

&#x20;   tests/

&#x20;       test_database.py

&#x20;   reports/

&#x20;   .gitignore

&#x20;   README.md

&#x20;   requirements.txt



## Setup



Install dependencies:



&#x20;   pip install -r requirements.txt



## Run Dashboard



&#x20;   streamlit run src/dashboard.py



## Verify Database



&#x20;   python src/verify_db.py



## Run Tests



&#x20;   python -m pytest tests/ -v



## Validation



The project has previously passed five automated database tests, product verification, database integrity checks, and foreign-key checks.



## Data Disclaimer



The database contains synthetic demonstration data. It is not intended for real-world medical or food-safety decisions.



## Note



Excursion detection and operational validation use software rules and data-quality checks. This project does not claim machine-learning prediction.


