# StatBox System Guide

## Overview

StatBox is a web-based statistical analysis platform that allows users to perform advanced statistical analyses on their datasets. The system supports multiple analysis types including Regression (Frequentist and Bayesian), ANOVA, and Bayesian Model Averaging (BMA).

## System Architecture

### Core Components

1. **Dataset Management**
   - Users upload CSV, XLSX, or XLS files
   - Datasets are stored on the server and associated with user accounts
   - Support for dataset cleaning and type detection
   - Ability to merge multiple datasets

2. **Analysis Sessions**
   - Each analysis is stored as a "session" with a unique name
   - Sessions track: model type, formula, dataset, analysis type, and options
   - Sessions preserve analysis history and allow for iterative refinement

3. **Module System**
   - Modular architecture supporting multiple analysis types
   - Each module handles a specific type of statistical analysis
   - Modules: Regression, ANOVA, Bayesian Regression, BMA

## Workflow

### Step 1: Dataset Upload
- User uploads a dataset file (CSV, XLSX, or XLS)
- Optionally provides a custom display name
- System stores the file and parses column types

### Step 2: Dataset Preparation (Optional)
- Users can clean and prepare their data
- Features include:
  - Column type detection and correction (numeric, categorical, binary, etc.)
  - Missing value handling
  - Data type conversion
  - Data preview and validation

### Step 3: Create Analysis Session
Users specify:
- **Session Name**: Descriptive name for the analysis
- **Model Type**: Choose from Regression, ANOVA, or BMA
- **Dataset**: Select from uploaded datasets
- **Analysis Type**: For Regression, choose Frequentist or Bayesian
- **Equation/Formula**: Statistical formula using R-style syntax

### Step 4: Formula Entry
Formulas follow R-style syntax:
- Basic: `y ~ x1 + x2`
- Multiple DVs: `y1 + y2 ~ x + z`
- Interactions: `y ~ x * m` (shorthand for `x + m + x:m`)
- Explicit interactions: `y ~ x1 + x2 + x1:x2`

### Step 5: Run Analysis
- System validates the formula
- Checks that all variables exist in the dataset
- Runs the appropriate statistical module
- Generates results tables, plots, and summary statistics

### Step 6: View Results
Results pages show:
- Summary statistics tables
- Model fit statistics (R², AIC, etc.)
- Coefficient tables with significance tests
- Interactive visualizations
- Customizable plots

## Analysis Types

### 1. Frequentist Regression
- Standard linear and generalized linear models
- Supports continuous, binary, ordinal, and multinomial outcomes
- Provides p-values, confidence intervals, R², AIC
- Hypothesis testing for coefficients
- Model diagnostics

### 2. Bayesian Regression
- Bayesian estimation using MCMC sampling
- Works with continuous outcomes only (numeric dependent variables)
- Provides posterior distributions
- Credible intervals instead of confidence intervals
- Uses Bambi library for model specification
- Configurable: draws, tune, chains, cores, priors

### 3. ANOVA (Analysis of Variance)
- Tests differences between group means
- Supports multiple dependent variables
- Handles main effects and interactions
- Generates ANOVA tables with F-statistics
- Provides interactive bar charts with t-tests
- Customizable x-axis labels and group variables

### 4. BMA (Bayesian Model Averaging)
- Combines multiple models with different variable combinations
- Evaluates variable inclusion probabilities
- Provides model-averaged coefficients
- Useful for variable selection uncertainty
- Shows which predictors are most important across models

## Formula Syntax

### Basic Structure
```
dependent_variable ~ independent_variables
```

### Multiple Dependent Variables
```
y1 + y2 ~ x + z
```
Runs separate analyses for each dependent variable.

### Variable Types
- **Continuous/Numeric**: Standard numeric variables
- **Categorical**: Automatically detected or manually set
- **Binary**: Variables with only 2 values (0/1)
- **Ordinal**: Ordered categorical variables
- **Multinomial**: Unordered categorical with >2 levels

### Interactions
- `x * m` creates: `x + m + x:m`
- `x:m` creates only the interaction term
- `x + m + x:m` explicitly includes all terms

## Results Interpretation

### Regression Coefficients
- **Coefficient Value**: Change in DV per unit change in IV, holding other variables constant
- **Standard Error**: Uncertainty in the coefficient estimate
- **t-statistic**: Coefficient divided by standard error
- **p-value**: Probability of observing this coefficient if null is true
- **Significance Levels**: * = p < 0.05, ** = p < 0.01, *** = p < 0.001

### Confidence/Credible Intervals
- **Frequentist**: 95% confidence interval - 95% of intervals would contain true value
- **Bayesian**: 95% credible interval - 95% probability true value is in this range

### Model Fit Statistics
- **R² (R-squared)**: Proportion of variance explained (0-1, higher is better)
- **Adjusted R²**: R² adjusted for number of predictors
- **AIC (Akaike Information Criterion)**: Lower is better; used for model comparison

### ANOVA Results
- **F-statistic**: Ratio of between-group to within-group variance
- **p-value**: Probability that group means are equal (null hypothesis)
- **Sum of Squares**: Variability attributed to each source
- **Mean Square**: Sum of squares divided by degrees of freedom

### BMA Results
- **Inclusion Probability**: Probability that variable should be in the model (0-1)
- **Posterior Mean**: Average coefficient across all models
- **Posterior SD**: Standard deviation of coefficient across models

## Visualization Features

### Interactive Plots
- **Spotlight Plots**: Show relationships with confidence bands
- **Bar Charts**: For ANOVA and categorical outcomes
- **Model Comparison**: Visual comparison of different models
- **Customizable**: Colors, labels, titles, borders
- **Download**: High-resolution exports (300 DPI) in PNG format

### Plot Customization
- Background color
- Bar colors (separate for low/high groups)
- Border colors
- Axis labels
- Group variable labels
- Plot titles

## Technical Details

### Supported File Formats
- CSV (Comma-separated values)
- XLSX (Excel 2007+)
- XLS (Excel 97-2003)

### Column Type Detection
System automatically detects:
- Numeric (continuous)
- Categorical (nominal)
- Binary (0/1 or yes/no)
- Ordinal (ordered categories)
- Text/string

### Missing Data Handling
- Options vary by analysis type
- Most models use listwise deletion
- Some support explicit missing data handling

### Session History
- Each session tracks analysis history
- Users can download history as text or JSON
- History includes: iterations, modifications, notes, plots

## User Interface Elements

### Main Dashboard
- List of sessions
- Dataset management
- Session search and filtering
- Bulk operations (delete)

### Analysis Form
- Session name input
- Model selection dropdown
- Dataset selection dropdown
- Analysis type toggle (Frequentist/Bayesian)
- Equation textarea with autocomplete
- Run and Visualize buttons

### Results Pages
- Summary statistics section
- Coefficient/ANOVA tables
- Interactive plots
- Customization modals
- Download options
- Edit dataset links

## Error Handling

### Common Errors
1. **Variable not found**: Variable name in formula doesn't exist in dataset
2. **Invalid formula syntax**: Formula doesn't follow required syntax
3. **Insufficient data**: Not enough observations for analysis
4. **Type mismatch**: Variable type incompatible with analysis
5. **Missing dataset**: Selected dataset was deleted

### Error Messages
- User-friendly error explanations
- Suggestions for fixing issues
- Formula correction assistance
- Variable name suggestions

## Best Practices

1. **Data Preparation**
   - Check column types before analysis
   - Handle missing values appropriately
   - Ensure sufficient sample size

2. **Formula Construction**
   - Start simple, add complexity gradually
   - Check variable names match dataset exactly
   - Use clear, descriptive session names

3. **Interpretation**
   - Consider effect sizes, not just significance
   - Check model assumptions
   - Use multiple model specifications when uncertain
   - Consider practical significance, not just statistical

4. **Session Management**
   - Use descriptive session names
   - Document important insights in notes
   - Keep datasets organized

## Limitations

1. **Bayesian Regression**: Only supports numeric dependent variables
2. **File Size**: Limited by subscription tier
3. **Computational Limits**: Large datasets or complex models may take time
4. **Supported Models**: Primarily linear and generalized linear models

## Future Features

- Support for more Bayesian model types
- Additional outcome variable types for Bayesian
- More advanced visualization options
- Model comparison tools
- Automated report generation

