# StatBox Q&A Database for AI Assistant

## General System Questions

### Q: How do I get started with StatBox?
**A:** First, upload a dataset (CSV, XLSX, or XLS format). Then create a new analysis session by selecting a model type (Regression, ANOVA, or BMA), choosing your dataset, entering a statistical formula, and clicking "Run". The system will analyze your data and display results with tables and interactive plots.

### Q: What file formats does StatBox support?
**A:** StatBox supports CSV (comma-separated values), XLSX (Excel 2007 and later), and XLS (Excel 97-2003) file formats. Files are uploaded through the dataset section on the main page.

### Q: How do I write a formula in StatBox?
**A:** Formulas use R-style syntax: `dependent_variable ~ independent_variable1 + independent_variable2`. For example: `sales ~ advertising + price`. You can add interactions using `*` (creates main effects and interaction) or `:` (interaction only). Multiple dependent variables: `y1 + y2 ~ x + z`.

### Q: What's the difference between a session and a dataset?
**A:** A **dataset** is your uploaded data file. A **session** is a specific analysis you run on that dataset. You can create multiple sessions using the same dataset with different formulas or model types. Sessions preserve your analysis history and results.

### Q: Can I merge datasets?
**A:** Yes! Check the boxes next to the datasets you want to merge and click the "Merge" button. You'll need to select matching columns from each dataset that contain common values (like IDs or keys) for the merge to work.

### Q: How do I clean or prepare my data?
**A:** Click the "Clean / Types" button (pencil icon) next to your dataset. This opens a data preparation interface where you can adjust column types (numeric, categorical, etc.), handle missing values, and preview your data.

---

## Regression Analysis Questions

### Q: What is Frequentist Regression?
**A:** Frequentist regression uses classical statistical methods (p-values, confidence intervals) to estimate relationships between variables. It's the standard approach for testing hypotheses about whether variables significantly predict outcomes. Results include t-tests, p-values, and R-squared measures of model fit.

### Q: What is Bayesian Regression?
**A:** Bayesian regression uses probability distributions to express uncertainty about model parameters. Instead of p-values, you get posterior distributions showing the probability of different parameter values. It provides credible intervals and works well with prior knowledge, but currently only supports numeric (continuous) dependent variables.

### Q: Why can't I use Bayesian regression with my categorical outcome?
**A:** Currently, Bayesian regression in StatBox only supports continuous (numeric) dependent variables. For binary, ordinal, or multinomial outcomes, use Frequentist Regression instead, which fully supports all outcome types.

### Q: How do I interpret regression coefficients?
**A:** A coefficient tells you how much the dependent variable changes for each 1-unit increase in the predictor, holding all other variables constant. For example, if `sales ~ advertising` has coefficient 2.5, each additional dollar spent on advertising increases sales by $2.50 (on average, assuming other factors stay the same).

### Q: What does R-squared mean?
**A:** R-squared (R²) is the proportion of variance in your dependent variable explained by your model. It ranges from 0 to 1. An R² of 0.75 means your predictors explain 75% of the variation in outcomes. Higher is generally better, but beware of overfitting with too many predictors.

### Q: What is Adjusted R-squared?
**A:** Adjusted R² accounts for the number of predictors in your model. Unlike regular R², it decreases when you add non-helpful predictors, making it better for comparing models with different numbers of variables. Use it when deciding which predictors to include.

### Q: What does AIC mean?
**A:** AIC (Akaike Information Criterion) measures model quality, balancing fit and complexity. Lower AIC values indicate better models. Use AIC to compare different model specifications—the model with the lowest AIC is generally preferred.

### Q: How do I interpret p-values in regression?
**A:** A p-value tells you the probability of observing your result if there's actually no relationship (null hypothesis). Conventionally:
- p < 0.05 (*): Statistically significant at 5% level
- p < 0.01 (**): Statistically significant at 1% level  
- p < 0.001 (***): Statistically significant at 0.1% level

Low p-values suggest the relationship is unlikely due to chance.

### Q: What's the difference between confidence intervals and credible intervals?
**A:** **Confidence intervals** (Frequentist): In 95% of repeated studies, this interval would contain the true value. **Credible intervals** (Bayesian): There's a 95% probability the true value is in this interval. Both typically range from 2.5th to 97.5th percentile.

### Q: Can I analyze binary outcomes (yes/no) in regression?
**A:** Yes! Frequentist regression supports binary outcomes. The model estimates the probability of one outcome category. Coefficients are interpreted in terms of log-odds or odds ratios, depending on the model specification.

### Q: What's an interaction effect?
**A:** An interaction means the effect of one variable depends on the value of another. For example, if `sales ~ advertising * region`, advertising might increase sales more in some regions than others. Use `*` for main effects plus interaction, or `:` for interaction only.

### Q: How do I interpret an interaction coefficient?
**A:** The interaction coefficient shows how much the effect of the first variable changes per unit of the second variable. If `y ~ x * z` has interaction coefficient 0.5, then the effect of x on y increases by 0.5 for each unit increase in z.

---

## ANOVA Analysis Questions

### Q: What is ANOVA?
**A:** ANOVA (Analysis of Variance) tests whether group means differ significantly. It compares variability between groups to variability within groups. If between-group variability is much larger than within-group, groups likely have different means.

### Q: When should I use ANOVA instead of regression?
**A:** Use ANOVA when your main interest is comparing group means (e.g., treatment vs. control, different conditions). Use regression when you want to understand relationships with continuous predictors or make predictions. ANOVA can be seen as a special case of regression with categorical predictors.

### Q: How do I interpret ANOVA F-statistics?
**A:** The F-statistic is the ratio of between-group to within-group variance. Larger F-values suggest stronger evidence that group means differ. Compare the F-statistic's p-value to your significance level (usually 0.05) to decide if differences are statistically significant.

### Q: What does the ANOVA table show?
**A:** The ANOVA table shows:
- **Source**: What causes variation (your predictors or error)
- **Sum of Squares (SS)**: Total variability from each source
- **Degrees of Freedom (DF)**: Number of independent pieces of information
- **Mean Square**: SS divided by DF (average variability)
- **F**: Ratio of Mean Squares (test statistic)
- **Prob > F**: p-value (probability of this F if null is true)

### Q: How do I create an ANOVA plot?
**A:** On the ANOVA results page, use the "Generate Plot" sidebar. Select X-axis variable, Y-axis variable, and optionally a group variable. Set standard deviation thresholds for splitting high/low groups. The plot shows bar charts with t-tests comparing groups.

### Q: What are the asterisks (*) in ANOVA plots?
**A:** Asterisks indicate statistical significance from t-tests comparing groups:
- ***: p < 0.001 (highly significant)
- **: p < 0.01 (very significant)
- *: p < 0.05 (significant)

The lines connecting bars show which groups are being compared.

### Q: Can I have multiple dependent variables in ANOVA?
**A:** Yes! Use the syntax `y1 + y2 ~ x1 + x2`. StatBox will run separate ANOVA analyses for each dependent variable and display separate results tables for each one.

### Q: What's the difference between main effects and interactions in ANOVA?
**A:** **Main effects**: The effect of each predictor by itself, averaged across all other predictors. **Interactions**: How the effect of one predictor changes depending on the value of another. Your ANOVA table shows both separately.

---

## Bayesian Model Averaging (BMA) Questions

### Q: What is BMA?
**A:** Bayesian Model Averaging combines multiple regression models that include different combinations of predictors. Instead of choosing one "best" model, BMA averages across all possible models, weighted by how well each fits the data.

### Q: Why would I use BMA instead of regular regression?
**A:** BMA helps when you're uncertain which predictors to include. Instead of choosing variables arbitrarily, BMA tells you which predictors are consistently important across many models. It's especially useful when you have many potential predictors and want to assess variable importance.

### Q: What is an inclusion probability?
**A:** Inclusion probability (ranging from 0 to 1) is the probability that a variable should be in your model, averaged across all possible models. A probability of 0.85 means the variable appears in 85% of the best-fitting models. Higher probabilities suggest more important predictors.

### Q: How do I interpret BMA inclusion probabilities?
**A:** 
- **> 0.5**: Variable is more likely to be included than excluded
- **> 0.75**: Strong evidence variable should be included
- **< 0.5**: Variable is more likely to be excluded
- **< 0.25**: Strong evidence variable can be excluded

Traditional threshold is 0.5, but some use 0.75 for a more conservative selection.

### Q: What is a model-averaged coefficient?
**A:** A model-averaged coefficient is the average of a variable's coefficient across all models, weighted by each model's posterior probability. It accounts for uncertainty about which predictors to include, giving a more robust estimate than any single model.

### Q: How does BMA handle uncertainty?
**A:** BMA acknowledges two types of uncertainty:
1. **Parameter uncertainty**: Given a model, uncertainty about coefficient values
2. **Model uncertainty**: Uncertainty about which predictors to include

BMA combines both, providing more realistic uncertainty estimates than single models.

---

## Visualization Questions

### Q: How do I customize plot colors?
**A:** Click the "Customize" button on any plot. You can change background color, bar colors for different groups, border colors, axis labels, group variable labels, and plot titles. Changes apply immediately and affect only the displayed plot.

### Q: Can I download plots?
**A:** Yes! Click the "Download" button and choose your preferred quality (Standard 800×600, High 1200×900, Ultra 1600×1200, or Custom dimensions). Downloads are at 300 DPI for high-quality printing.

### Q: What is a spotlight plot?
**A:** A spotlight plot shows how a relationship between two variables changes at different levels of a third variable (moderator). For example, it might show how advertising affects sales at low, medium, and high price levels. The plot includes confidence bands showing uncertainty.

### Q: How do I interpret significance lines in ANOVA plots?
**A:** Horizontal lines connect groups being compared. Vertical "caps" at the ends mark the comparison points. Asterisks above lines indicate significance level. Lines spanning multiple groups compare overall patterns; lines within groups compare subgroups.

---

## Data Preparation Questions

### Q: How does StatBox detect column types?
**A:** StatBox automatically detects numeric (continuous), categorical (nominal), binary (0/1 or yes/no), ordinal (ordered), and text types. You can override these in the data preparation interface if detection is incorrect.

### Q: What should I do if my column types are wrong?
**A:** Go to "Clean / Types" for your dataset. The interface shows detected types. Click on a column type to change it. Correct types ensure appropriate analyses—numeric variables allow full statistical tests, while categorical variables use group comparisons.

### Q: Can I merge datasets?
**A:** Yes! Check multiple datasets and click "Merge". You'll select matching columns (keys) from each dataset. The system combines rows where key values match. This is useful for joining data from different sources.

---

## Technical Questions

### Q: What happens if a variable in my formula doesn't exist?
**A:** StatBox will show an error message listing the unknown variables. You can either fix the variable names in your formula or use the "Drop Unknown Variables" option to automatically remove them and proceed with available variables.

### Q: What if my analysis takes too long?
**A:** Complex models or large datasets may take time. Bayesian analyses can take 1-5 minutes for MCMC sampling. You can safely navigate away and return later—your session is saved. If analysis fails, check error messages and try simplifying your model.

### Q: Can I compare different models?
**A:** Yes! Create separate sessions with different formulas or settings. Compare their AIC values (for frequentist) or use BMA to see how model selection affects results. You can also download session history to compare analyses.

### Q: How do I save my work?
**A:** Everything is automatically saved! Sessions, datasets, and results are stored on your account. You can return to any session later to view results, modify analyses, or download data.

### Q: What is session history?
**A:** Session history tracks all changes you make to an analysis: initial runs, modifications, added plots, and notes. Download it as text or JSON to keep a record of your analytical decisions and process.

---

## Interpretation Help

### Q: My p-value is 0.06, but I was told I need p < 0.05. Is my result significant?
**A:** By strict convention, p = 0.06 is not "statistically significant" at the 0.05 level, meaning we can't confidently reject the null hypothesis. However, this is a threshold set by convention, not a hard boundary. Consider:
- Effect size (how large is the effect?)
- Practical significance (does it matter in real terms?)
- Sample size (larger samples make small effects significant)
- Prior evidence (does this fit with existing knowledge?)

Some researchers use p < 0.10 as a threshold for "marginally significant" results warranting further investigation.

### Q: My R-squared is low (0.15). Does this mean my model is bad?
**A:** Not necessarily. Low R² can mean:
1. Many unmeasured factors affect your outcome (common in social/behavioral sciences)
2. High natural variability in your dependent variable
3. Your predictors are less important than other factors

Focus on whether predictors are statistically significant and practically meaningful. In some fields (e.g., psychology), R² = 0.15 might be considered substantial.

### Q: How do I know if my model assumptions are met?
**A:** StatBox provides basic diagnostics, but consider checking:
- **Linearity**: Relationships should be roughly linear (check scatterplots)
- **Normality**: Residuals should be normally distributed (less critical with large samples)
- **Homoscedasticity**: Variance should be constant across predictor values
- **Independence**: Observations should be independent (no repeated measures or clustering)

For violations, consider transformations or alternative models.

### Q: I have an interaction that's significant but the main effects aren't. What does this mean?
**A:** This suggests the effect of one variable depends strongly on the value of the other. Even though neither variable has a consistent effect on average, their combination does. You should interpret the interaction effect rather than the main effects alone. Plot the interaction to visualize how effects change.

### Q: My coefficient is very small (0.001). Is this meaningful?
**A:** Statistical significance doesn't equal practical significance. A tiny but significant coefficient might be:
- Meaningless if measuring large-scale outcomes (e.g., $0.001 change in company revenue)
- Important if measuring small-scale outcomes (e.g., 0.001 change in test scores on 0-1 scale)

Always consider the scale of your variables and what change is practically important in your context.

---

## Common Problems and Solutions

### Q: I get an error saying "Variable not found"
**A:** Check that:
1. Variable names in your formula exactly match column names in your dataset
2. Variable names are spelled correctly (case-sensitive)
3. You've selected the correct dataset
4. Variables aren't hidden or filtered in data preparation

### Q: My analysis says "Insufficient data"
**A:** This usually means:
1. Too many missing values for the variables you're using
2. Not enough observations after filtering for your analysis
3. A group in ANOVA has fewer than 2 observations

Try reducing the number of predictors, handling missing data, or adjusting group thresholds.

### Q: Bayesian analysis says my dependent variable must be numeric
**A:** Bayesian regression currently only supports continuous (numeric) outcomes. For binary, ordinal, or multinomial outcomes, use Frequentist Regression, which fully supports all outcome types with appropriate link functions.

### Q: My plot won't download
**A:** Make sure:
1. The plot has been generated (not just the results table)
2. You've selected a quality option
3. Your browser allows downloads
4. Try a different browser if issues persist

### Q: I can't see my customized labels after downloading
**A:** Customizations apply to the display but may not export if done incorrectly. Make sure to click "Apply" in the customization modal before downloading. The downloaded image reflects the current plot state.

---

## Advanced Topics

### Q: What's the difference between Type I, II, and III Sum of Squares in ANOVA?
**A:** These differ in how they handle unbalanced designs and interactions:
- **Type I (Sequential)**: Tests each effect controlling only for effects entered before it
- **Type II**: Tests each effect controlling for all other effects except those containing it
- **Type III (Marginal)**: Tests each effect controlling for all other effects

StatBox typically uses Type II or III, which are more robust for unbalanced designs.

### Q: How do I handle multicollinearity?
**A:** Multicollinearity occurs when predictors are highly correlated, making coefficient estimates unstable. Signs include:
- High standard errors
- Unexpected coefficient signs
- Large changes when adding/removing variables

Solutions: Remove one correlated variable, use regularization, or combine variables into a single predictor.

### Q: What's the difference between marginal and conditional effects?
**A:** **Marginal effects**: Average effect of a variable across all values of other variables. **Conditional effects**: Effect of a variable at specific values of other variables (especially relevant for interactions). StatBox typically shows marginal effects, but spotlight plots show conditional effects.

### Q: How should I handle missing data?
**A:** Options include:
- **Listwise deletion**: Remove any observation with missing values (default in most models)
- **Pairwise deletion**: Use available data for each analysis (not always appropriate)
- **Imputation**: Fill in missing values (advanced, not currently built-in)

StatBox uses listwise deletion by default. Check how many observations are used in your results—large drops suggest missing data issues.

---

## Getting Help

### Q: Where can I learn more about statistical concepts?
**A:** For regression, ANOVA, and BMA concepts, consider introductory statistics textbooks or online resources. StatBox handles the computations, but understanding the statistical concepts helps you interpret results correctly.

### Q: Can I export my results?
**A:** Yes! You can:
- Download plots as high-resolution PNG images
- Download session history as text or JSON
- Copy tables from results pages
- Take screenshots of visualizations

### Q: How do I share my analysis?
**A:** Currently, you can share by:
- Exporting plots and tables
- Sharing session history files
- Describing your formula and results

Sessions are tied to your account, but you can recreate analyses in other accounts if needed.

