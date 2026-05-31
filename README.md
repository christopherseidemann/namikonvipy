# NaMi-ETL Pipeline: Automated Data Parsing \& XML Generation

[!\[Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[!\[License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Project Context:**  
This project was developed to automate the financial data processing for a non-profit organization. While the domain is financial/membership management, the core architecture demonstrates a robust **ETL (Extract, Transform, Load) pipeline**.



## Technical Features

* **Data Wrangling \& Cleaning (`pandas`):** Ingests raw, unstructured Excel exports, filters out inactive records, and sanitizes strings (e.g., stripping whitespaces, normalizing formats).
* **Relational Inference \& Grouping:** Automatically infers household relationships based on a combination of last names and banking identifiers to dynamically calculate tiered membership fees.
* **Algorithmic Validation (ISO 7064):** Implements a custom Modulus-97 algorithm to mathematically validate IBAN (International Bank Account Number) checksums before processing.
* **Schema-Compliant XML Export:** Uses Python's native `xml.etree.ElementTree` to construct deeply nested, standard-compliant SEPA XML files (`pain.008.003.02` schema).
* **Fault-Tolerant Logging:** Invalid or missing data does not crash the pipeline. Instead, problematic records are isolated and exported into dedicated Excel reports (`openpyxl`) for manual review\[cite: 1].

\---

## Tech Stack \& Architecture

* **Core:** Python 3.8+
* **Data Processing:** `pandas` (for DataFrame manipulation, filtering, and aggregation)\[cite: 1]
* **I/O Operations:** `openpyxl` (for structured Excel report generation)\[cite: 1]
* **XML Engine:** `xml.etree.ElementTree` (Standard library)

### Pipeline Architecture

```text
\[Raw Excel Data] ──> \[Pandas Data Cleaning] ──> \[Relational Grouping (Households)]
                                                        │
       ┌────────────────────────────────────────────────┴───────────────────┐
       ▼                                                                    ▼
\[Validation (Modulus 97 Checksum)]                                  \[Missing/Corrupt Data]
       │                                                                    │
       ▼                                                                    ▼
\[SEPA XML Generation (Schema strict)]                             \[Excel Error Reports]

