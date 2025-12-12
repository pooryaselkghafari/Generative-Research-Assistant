# Generative Research Assistant (GRA)

An open-source, locally-run web application for statistical analysis and data visualization. GRA provides a no-code interface for regression analysis, Bayesian modeling, ANOVA, time series analysis, and more.

## Features

- **Data Management**: Upload, clean, and manage datasets (CSV, Excel, JSON)
- **Statistical Analysis**:
  - OLS Regression
  - Bayesian Regression
  - Bayesian Model Averaging (BMA)
  - ANOVA
  - VARX (Vector Autoregression with Exogenous Variables)
  - Structural Models (2SLS, 3SLS, SUR)
- **Data Preparation**: 
  - Column management (rename, type conversion, ordering)
  - Data cleaning and normalization
  - Stationarity fixes for time series
  - Date format detection and conversion
- **Visualization**: Interactive plots and charts
- **Session Management**: Save and manage analysis sessions
- **Paper Organization**: Organize research papers and associated analyses

## Prerequisites

- **Python**: 3.9 or higher
- **pip**: Python package manager
- **R** (optional): Required for Bayesian Model Averaging (BMA) analysis. If not installed, BMA features will be unavailable.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/pooryaselkghafari/Generative-Research-Assistant.git
cd Generative-Research-Assistant
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
```

### 3. Activate the Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you encounter any dependency conflicts, you may need to upgrade pip first:

```bash
pip install --upgrade pip
```

### 5. Run Database Migrations

```bash
python manage.py migrate
```

This will create the SQLite database file (`db.sqlite3`) and set up all necessary tables.

### 6. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

## Running the Application

### Start the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

### Using a Different Port

If port 8000 is already in use, specify a different port:

```bash
python manage.py runserver 8080
```

## How to Use

### 1. Upload a Dataset

1. Navigate to the main page at `http://127.0.0.1:8000/`
2. Click on "Upload Dataset" or use the dataset upload interface
3. Select a file (CSV, Excel, or JSON format)
4. The dataset will be processed and added to your dataset list

### 2. Clean and Prepare Data

1. Click on a dataset to open the data cleaner
2. In the cleaner interface, you can:
   - **Manage Columns**: Rename columns, change data types (numeric, categorical, ordinal, date, etc.)
   - **Code Columns**: Apply coding transformations
   - **Normalize Columns**: Apply normalization (min-max, mean centering, standardization)
   - **Drop Columns**: Remove unwanted columns
   - **Fix Date Formats**: Detect and convert date formats
3. Click "Save" to overwrite the original dataset, or "Save as..." to create a new dataset

### 3. Run Statistical Analysis

1. From the main page, click "New Analysis" or select an existing session
2. Choose your analysis type:
   - **OLS Regression**: Standard linear regression
   - **Bayesian Regression**: Bayesian linear regression
   - **BMA**: Bayesian Model Averaging (requires R)
   - **ANOVA**: Analysis of Variance
   - **VARX**: Vector Autoregression with Exogenous Variables
   - **Structural Models**: 2SLS, 3SLS, SUR
3. Select your dependent and independent variables
4. Configure analysis options
5. Click "Run Analysis"

### 4. View Results

- Results are displayed with:
  - Statistical tables and coefficients
  - Model diagnostics
  - Interactive visualizations
  - Export options (CSV, Excel, JSON)

### 5. Manage Sessions

- **Save Sessions**: Analysis sessions are automatically saved
- **Organize with Papers**: Group related analyses into research papers
- **Export Results**: Download results in various formats
- **Session History**: View and manage previous analysis sessions

### 6. VARX-Specific Features

For VARX analysis:
- **Stationarity Check**: View ADF test results for each variable
- **Fix Stationarity**: Apply differencing or log transformations to make variables stationary
- **IRF Plots**: Generate Impulse Response Function plots
- **Correlation Heatmaps**: Visualize variable correlations

## Project Structure

```
GRA/
├── engine/              # Main application code
│   ├── dataprep/       # Data preparation and cleaning
│   ├── models/         # Django database models
│   ├── services/       # Business logic services
│   ├── static/         # Static files (CSS, JS)
│   ├── templates/      # HTML templates
│   └── views/          # View controllers
├── models/             # Statistical analysis models
│   ├── regression.py
│   ├── bayesian_regression.py
│   ├── BMA.py
│   ├── ANOVA.py
│   ├── VARX.py
│   └── structural_model.py
├── data_prep/          # Data preparation utilities
├── statbox/            # Django project settings
├── manage.py           # Django management script
└── requirements.txt    # Python dependencies
```

## Configuration

### Local Development

The application runs locally by default with:
- **Database**: SQLite (no configuration needed)
- **Authentication**: Not required (local use only)
- **Static Files**: Served by Django development server

### Environment Variables (Optional)

You can customize settings using environment variables:

```bash
export DEBUG=True
export SECRET_KEY=your-secret-key
export ALLOWED_HOSTS=localhost,127.0.0.1
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure your virtual environment is activated and all dependencies are installed:

```bash
pip install -r requirements.txt
```

### Database Errors

If you encounter database errors, try resetting the database:

```bash
rm db.sqlite3
python manage.py migrate
```

### R Integration Issues

If BMA analysis fails, ensure R is installed and accessible from your PATH:

```bash
# Check if R is installed
R --version

# Install required R packages (if needed)
Rscript -e "install.packages('BAS', repos='https://cloud.r-project.org')"
```

### Port Already in Use

If port 8000 is already in use, specify a different port:

```bash
python manage.py runserver 8080
```

### Static Files Not Loading

If static files (CSS, JS) are not loading:

```bash
python manage.py collectstatic --noinput
```

### Python Version Issues

Ensure you're using Python 3.9 or higher:

```bash
python3 --version
```

If you have multiple Python versions, use:

```bash
python3.9 -m venv venv
```

## Development

### Running Tests

```bash
python manage.py test
```

### Creating Migrations

If you modify models:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Accessing Django Admin (Optional)

The admin interface is available at `/admin/` (no authentication required for local use).

## Privacy and Data

This application runs **entirely locally** on your machine:
- All data is stored locally in your SQLite database
- No data is transmitted to external servers
- No tracking or analytics
- No cloud services
- You have full control over your data

## License

This project is open source and available under the MIT License. See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on the [GitHub repository](https://github.com/pooryaselkghafari/Generative-Research-Assistant).

## Acknowledgments

This tool is built using:
- Django (Python web framework)
- Pandas (Data manipulation)
- NumPy (Numerical computing)
- Statsmodels (Statistical modeling)
- R (for Bayesian Model Averaging)
- Various visualization libraries

---

**Note**: This is a local application designed to run on your machine. No authentication or external services are required for basic usage.
