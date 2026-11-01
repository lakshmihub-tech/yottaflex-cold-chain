\# YottaFlex Cold Chain Monitoring System



A Python and SQLite-based cold-chain monitoring system designed to track shipments, monitor sensor readings, detect temperature and humidity excursions, validate data quality, and maintain corrective-action records.



\## 1. Features



\- Shipment, product, container, and sensor management.

\- Product-specific temperature and humidity threshold policies.

\- Five-minute interval sensor monitoring.

\- Shipment-to-container assignment tracking.

\- Temperature and humidity excursion detection.

\- Excursion duration and severity classification.

\- Route stops and operational event records.

\- Data-quality validation and ground-truth scenarios.

\- Corrective-action tracking.

\- SQLite database integrity and foreign-key validation.

\- Streamlit dashboard with Plotly visualizations.

\- CSV ground-truth export.

\- Automated validation report generation.



\## 2. Technology Stack



| Technology | Purpose |

|---|---|

| Python | Application logic and data processing |

| SQLite | Relational database |

| Pandas | Data analysis |

| NumPy | Synthetic data generation |

| Streamlit | Interactive dashboard |

| Plotly | Data visualization |

| Pytest | Automated testing |



\## 3. Project Structure



```text

yottaflex-cold-chain/

│

├── data/

│   └── cold\_chain.db

│

├── src/

│   ├── align\_readings.py

│   ├── dashboard.py

│   ├── detect\_excursions.py

│   ├── generate\_data.py

│   ├── generate\_operations.py

│   ├── init\_db.py

│   ├── main.py

│   ├── quality\_scenarios.py

│   ├── schema.sql

│   └── verify\_db.py

│

├── tests/

│   └── test\_database.py

│

├── reports/

│   ├── ground\_truth.csv

│   └── validation\_report.txt

│

├── DATA\_DICTIONARY.md

├── export\_ground\_truth.py

├── generate\_validation\_report.py

├── requirements.txt

├── .gitignore

└── README.md

```



\## 4. Installation and Setup



Clone the repository:



```bash

git clone https://github.com/lakshmihub-tech/yottaflex-cold-chain.git

cd yottaflex-cold-chain

```



Install dependencies:



```bash

pip install -r requirements.txt

```



\## 5. Run the Application



Start the Streamlit dashboard:



```bash

streamlit run src/dashboard.py

```



\## 6. Database Verification



Run database verification:



```bash

python src/verify\_db.py

```



This checks expected entity counts, foreign-key relationships, database integrity, and reading timestamp order.



\## 7. Excursion Detection



Run the rule-based excursion detector:



```bash

python src/detect\_excursions.py

```



The detector evaluates temperature and humidity readings against applicable product thresholds and records detected excursion episodes.



\*\*Important:\*\* Run experiments against a test database. Preserve the original database.



\## 8. Ground-Truth Export



Generate the ground-truth CSV:



```bash

python export\_ground\_truth.py

```



Output:



```text

reports/ground\_truth.csv

```



\## 9. Validation Report



Generate the validation report:



```bash

python generate\_validation\_report.py

```



Output:



```text

reports/validation\_report.txt

```



\## 10. Run Automated Tests



Execute the test suite:



```bash

python -m pytest tests/ -v

```



The current test suite contains five database tests covering database existence, product count, container count, shipment count, and valid shipment-product relationships.



\*\*Latest recorded test result: 5 passed.\*\*



\## 11. Data Quality Scenarios



The project includes five documented negative scenarios:



1\. Physically impossible sensor reading.

2\. Missing sensor reading interval.

3\. Delivery before departure.

4\. Incorrect product threshold application.

5\. Excursion duration undercounting.



These scenarios are represented in the data-quality and ground-truth records.



\## 12. Data Dictionary



Refer to `DATA\_DICTIONARY.md` for entity descriptions, field definitions, data types, relationships, and validation details.



\## 13. Validation Summary



Previously recorded validation results:



\- Five automated database tests passed.

\- SQLite integrity check passed.

\- Foreign-key validation reported zero violations.

\- Product-specific threshold verification passed.

\- Synthetic excursion tests detected brief and prolonged temperature excursions.



\## 14. Data Disclaimer



All database records are synthetic demonstration data. This application is intended for software development and demonstration purposes and must not be used as the sole basis for real-world pharmaceutical, medical, or food-safety decisions.



\## 15. Limitations



\- Excursion detection is rule-based, not machine-learning prediction.

\- Real-world notification delivery is not claimed as implemented.

\- Synthetic test scenarios do not replace validation against real operational data.

