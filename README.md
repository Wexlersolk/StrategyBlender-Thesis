# StrategyBlender Platform

> **Disclaimer:** This repository contains the public, non-proprietary core of the StrategyBlender platform developed for my Bachelor's Thesis. Sensitive indicators, proprietary datasets, the execution engine, and API keys have been removed from this release.

## Overview

StrategyBlender is a service-oriented quantitative research platform designed to automate the lifecycle of trading strategy development, validation, and execution. 

### Included Modules
- **`services/`**: Orchestration components, Python Strategy service, and strategy generator templates.
- **`research/`**: Statistical validation tools, including Combinatorial Purged Cross-Validation (CPCV), Walk-Forward Analysis, and Monte Carlo simulations.
- **`ui/`**: Streamlit-based graphical user interface for interacting with the Quant Lab.
- **`tests/`**: Unit testing and system validation modules.

### Removed Components
- `engine/` (Core execution logic and Microstructure modeling)
- MetaTrader 5 Indicators & Expert Advisors (`.mq5`, `.ex5`)
- Proprietary market datasets and historical quotes
- Specific generated candidate strategies

## Requirements
See `requirements.txt` for Python dependencies. This public release is provided for academic review and demonstration purposes.
