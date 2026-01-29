# L-SOMA Project: Strategic Expansion Analysis for Senior Living

## Abstract
This project presents a data-driven strategic analysis for expanding a network of senior living residences in Spain. By leveraging **demographic data** (census, aging projections), **socioeconomic indicators** (household income), and **competitive intelligence** (Google Places API auditing), we identify "Blue Ocean" opportunities—areas with high demand, high purchasing power, and low market saturation.

## Methodology
The study follows a rigorous phased approach:

1.  **Data Ingestion**: Integration of national census data, cadastral information, and income statistics.
2.  **Feature Engineering**: Calculation of the "Target Vector Q" based on population >65 and economic capability.
3.  **Clustering (DBSCAN)**: Identification of continuous urban clusters ripe for expansion.
4.  **Viability Selection**: Filtering clusters based on critical mass (minimum 40,000 equivalent inhabitants).
5.  **Competitive Audit**: Real-time validation of competitors using **Google Places API**, correcting for false positives (pharmacies, gyms).
6.  **Strategic Classification**: Categorization of clusters into *Blue Oceans* (High Potential/Low Competition), *Battlefields*, and *Saturated Markets*.

## Key Findings
- **Identified Clusters**: Analysis of over 300 urban clusters.
- **Top Candidates**: 21 "Prime" locations identified as immediate expansion targets.
- **Validation**: Competitor data validated with >95% accuracy via automated auditing scripts.

## Project Structure
```
├── datos/                  # Raw and processed datasets (Excluded from repo)
├── informe/                # LaTeX source for reports and presentations
├── scripts/                # Python processing pipeline
│   ├── 00_...              # Data ingestion & cleaning
│   ├── 14_...              # DBSCAN Clustering
│   ├── VALIDACION_...      # Competitor auditing via Google API
│   └── ...
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```

## Requirements
- Python 3.9+
- Libraries: `pandas`, `folium`, `scikit-learn`, `requests`, `python-dotenv`
- Google Places API Key (configured in `.env`)

## Usage
1.  Install dependencies: `pip install -r requirements.txt`
2.  Configure `.env` with `GOOGLE_API_KEY`.
3.  Run the pipeline scripts in numerical order.

---
**Author**: L-SOMA Data Team
**Date**: January 2026
