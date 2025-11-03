# ----------------------------------------------------------
# Run Bayesian Model Averaging (BMA) in R directly from Python
# Handles both numeric and non-numeric predictors and response
# Uses BAS library with MCMC method as requested
# ----------------------------------------------------------

import pandas as pd
import numpy as np
from rpy2.robjects import r, pandas2ri
import rpy2.robjects as ro
from rpy2.robjects.conversion import localconverter
import json
import re

def _quote_column_names_with_special_chars(df, formula):
    """Handle column names with spaces, dots, and other special characters for R processing"""
    # For R, we need to temporarily rename columns with special characters
    # and update the formula accordingly
    column_mapping = {}
    df_renamed = df.copy()
    
    # Create mapping for columns with special characters
    for col in df.columns:
        # Check if column name contains spaces, dots, or other problematic characters
        if any(char in col for char in [' ', '.', '-', '(', ')', '[', ']', '+', '*', ':', '~', '^', '$', '|', '\\', '/', '?']):
            # Create a safe name by replacing problematic characters with underscores
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', col)
            # Ensure the safe name doesn't start with a number
            if safe_name[0].isdigit():
                safe_name = 'var_' + safe_name
            # Ensure the safe name is unique
            original_safe_name = safe_name
            counter = 1
            while safe_name in column_mapping.values():
                safe_name = f"{original_safe_name}_{counter}"
                counter += 1
            
            column_mapping[safe_name] = col
            df_renamed = df_renamed.rename(columns={col: safe_name})
            # Update formula to use safe names - use word boundaries to avoid partial matches
            formula = re.sub(rf'\b{re.escape(col)}\b', safe_name, formula)
    
    return formula, df_renamed, column_mapping

def run_bma_analysis_bas(df, response_var, predictor_vars, categorical_vars=None, original_formula=None, label_map=None, media_path=None):
    """
    Run Bayesian Model Averaging analysis using R's BAS library with MCMC method
    
    Parameters:
    -----------
    df : pandas.DataFrame
        The dataset to analyze
    response_var : str
        Name of the response variable
    predictor_vars : list
        List of predictor variable names
    categorical_vars : list, optional
        List of categorical variable names (will be converted to factors in R)
    original_formula : str, optional
        Original formula string for complex interactions
    label_map : dict, optional
        Dictionary mapping variable names to display labels
        
    Returns:
    --------
    dict : Dictionary containing BMA results and summary statistics
    """
    
    try:
        # Handle column names with special characters for proper processing
        if original_formula:
            formula, df_renamed, column_mapping = _quote_column_names_with_special_chars(df, original_formula)
        else:
            # Create a simple formula if none provided
            simple_formula = f"{response_var} ~ " + " + ".join(predictor_vars)
            formula, df_renamed, column_mapping = _quote_column_names_with_special_chars(df, simple_formula)
        
        # Prepare the dataset for R using renamed columns
        analysis_df = df_renamed[[response_var] + predictor_vars].copy()
        
        # Send dataset to R
        with localconverter(ro.default_converter + pandas2ri.converter):
            ro.globalenv["df"] = analysis_df
        
        # Send label_map to R if provided
        if label_map is not None:
            # Convert Python dict to R list
            r_label_map = ro.ListVector(label_map)
            ro.globalenv["label_map"] = r_label_map
        
        # Convert categorical variables to factors in R
        if categorical_vars is None:
            categorical_vars = []
        
        factor_conversion = ""
        for var in categorical_vars:
            if var in analysis_df.columns:
                factor_conversion += f"df${var} <- as.factor(df${var})\n"
        
        r(f'''
        df <- as.data.frame(df)
        {factor_conversion}
        ''')
        
        # Use the processed formula (already handles special characters)
        formula_str = formula
        
        # Load BAS and run bas.lm with MCMC method
        # Set default media path if not provided
        import os
        if media_path is None:
            media_path = os.path.join(os.getcwd(), 'media')
        
        # Ensure media directory exists
        os.makedirs(media_path, exist_ok=True)
        
        r_code = f'''
        # Install and load BAS package
        if (!requireNamespace("BAS", quietly = TRUE)) {{
          install.packages("BAS", repos="https://cloud.r-project.org")
        }}
        library(BAS)
        
        # Define plotting function matching the R template
        plot_bma_results <- function(file_path, model_name, bma_model, label_map = NULL) {{
          pic_name <- paste0(file_path, "/", model_name, ".png")
          
          coef_info <- coef(bma_model, probne0 = TRUE)
          
          # Extract and process coefficients
          pip <- coef_info$probne0[-1]  # Remove intercept
          post_means <- coef_info$postmean[-1]
          post_sds <- coef_info$postsd[-1]
          predictors <- coef_info$namesx[-1]
          
          # Calculate 95% confidence intervals
          ci_lower <- post_means - 1.96 * post_sds
          ci_upper <- post_means + 1.96 * post_sds
          
          # Create a data frame and sort by PIP in descending order
          coef_df <- data.frame(predictors, pip, post_means, post_sds, ci_lower, ci_upper)
          coef_df <- coef_df[order(-coef_df$pip), ]
          
          # Update vectors with sorted values
          pip <- coef_df$pip
          post_means <- coef_df$post_means
          post_sds <- coef_df$post_sds
          predictors <- coef_df$predictors
          ci_lower <- coef_df$ci_lower
          ci_upper <- coef_df$ci_upper
          
          # Apply label mapping if provided
          if (!is.null(label_map)) {{
            predictors <- ifelse(predictors %in% names(label_map),
                                 label_map[predictors],
                                 predictors)
          }}
          
          # Open PNG device
          png(pic_name, width = 12, height = 6, units = "in", res = 300)
          
          # Set up modern plotting parameters with consistent font
          par(mfrow = c(1, 2), 
              mar = c(12, 5, 6, 2) + 0.1, 
              mgp = c(3.5, 1, 0), 
              cex.axis = 0.9,
              cex.lab = 1.1,
              cex.main = 1.2,
              family = "sans")
          
          # Modern color palette for PIP bars
          pip_colors <- ifelse(pip < 0.5, 
                               "#E5E7EB",  # Light gray for low PIP
                               "#3B82F6")  # Modern blue for high PIP
          
          # Add gradient effect for high PIP bars
          pip_colors_gradient <- ifelse(pip < 0.5, 
                                        "#E5E7EB",
                                        ifelse(pip < 0.7, "#60A5FA", "#1D4ED8"))
          
          # Plot modern PIP barplot
          bp_pip <- barplot(
            pip,
            names.arg = predictors,
            xlab = "",
            ylim = c(0, 1.05),
            col = pip_colors_gradient,
            border = "white",
            main = paste("Posterior Inclusion Probabilities\\\\n", model_name),
            ylab = "Inclusion Probability",
            cex.names = 0.8,
            las = 2,
            space = 0.3,
            col.main = "#1F2937",
            col.lab = "#374151",
            col.axis = "#6B7280"
          )
          
          # Add modern reference line
          abline(h = 0.5, col = "#EF4444", lty = 2, lwd = 2.5)
          
          # Add subtle grid lines
          grid(nx = NA, ny = NULL, col = "#F3F4F6", lty = 1, lwd = 0.5)
          
          # Add value labels on top of bars
          text(x = bp_pip, y = pip + 0.03, 
               labels = paste0(round(pip * 100, 1), "%"), 
               cex = 0.7, col = "#374151", font = 2)
          
          # Plot modern coefficient barplot with error bars
          bp_coef <- barplot(
            post_means,
            names.arg = predictors,
            xlab = "",
            col = "#10B981",  # Modern emerald green
            border = "white",
            main = paste("Model-averaged Coefficients ±1 SD\\\\n", model_name),
            ylab = "Coefficient Estimate",
            cex.names = 0.8,
            las = 2,
            space = 0.3,
            col.main = "#1F2937",
            col.lab = "#374151",
            col.axis = "#6B7280",
            ylim = range(c(post_means - post_sds, post_means + post_sds)) * 1.2
          )
          
          # Add modern error bars
          arrows(
            x0 = bp_coef,
            y0 = post_means - post_sds,
            x1 = bp_coef,
            y1 = post_means + post_sds,
            angle = 90,
            code = 3,
            length = 0.08,
            lwd = 2.5,
            col = "#374151"
          )
          
          # Add horizontal reference line at zero
          abline(h = 0, col = "#6B7280", lty = 1, lwd = 1.5)
          
          # Add subtle grid lines
          grid(nx = NA, ny = NULL, col = "#F3F4F6", lty = 1, lwd = 0.5)
          
          # Add coefficient value labels
          text(x = bp_coef, y = post_means + sign(post_means) * post_sds + 
               sign(post_means) * 0.05 * diff(range(c(post_means - post_sds, post_means + post_sds))), 
               labels = paste0(round(post_means, 3)), 
               cex = 0.7, col = "#374151", font = 2)
          
          dev.off()
          
          return(coef_df)
        }}
        
        # Initialize variables
        bma_fit <- NULL
        bma_results <- data.frame(
          predictors = character(0),
          pip = numeric(0),
          post_means = numeric(0),
          post_sds = numeric(0)
        )
        n_models <- 0
        r_squared <- 0
        weighted_R2 <- 0
        best_model_fit <- data.frame(
          model_index = 0,
          log_marginal_likelihood = 0,
          R2 = 0
        )
        top_models <- NULL
        top_model_probs <- NULL
        
        # Fit BMA model using BAS with MCMC method
        tryCatch({{
          print("Fitting BAS model...")
          bma_fit <- bas.lm(
            formula = as.formula("{formula_str}"),
            data = df,
            prior = "BIC",
            modelprior = uniform(),
            method = "MCMC"
          )
          
          print("Model fitted successfully")
          
          # Generate plots and get coefficient table
          model_name <- "BMA_Analysis"
          file_path <- "{media_path}"
          
          # Use label_map from global environment if available
          r_label_map <- NULL
          if (exists("label_map")) {{
            r_label_map <- label_map
          }}
          
          bma_results <- plot_bma_results(file_path, model_name, bma_fit, r_label_map)
          
          # Get model information
          n_models <- length(bma_fit$logmarg)
          
          # Calculate fit statistics
          fit_stats <- data.frame(
            model_index = seq_along(bma_fit$logmarg),
            log_marginal_likelihood = bma_fit$logmarg,
            R2 = bma_fit$R2
          )
          
          # Best model based on log marginal likelihood
          best_model_index <- which.max(bma_fit$logmarg)
          best_model_fit <- fit_stats[best_model_index, ]
          # Weighted R2 (model-averaged R2)
          weighted_R2 <- sum(bma_fit$postprobs * bma_fit$R2)
          # Calculate R-squared for the best model (for backward compatibility)
          # Use the R2 from the best model directly
          r_squared <- best_model_fit$R2
          # Get top models - simplified approach
          top_models <- NULL
          top_model_probs <- NULL
          
        }}, error = function(e) {{
          print(paste("Error in BMA fitting:", e$message))
          # Keep the initialized empty results
          n_models <- 0
          r_squared <- 0
          weighted_R2 <- 0
          best_model_fit <- data.frame(
            model_index = 0,
            log_marginal_likelihood = 0,
            R2 = 0
          )
          top_models <- NULL
          top_model_probs <- NULL
        }})
        '''
        r(r_code)
        
        # Bring the results back into Python
        with localconverter(ro.default_converter + pandas2ri.converter):
            bma_table = r['bma_results']
            n_models = r['n_models'][0] if len(r['n_models']) > 0 else 0
            r_squared = r['r_squared'][0] if len(r['r_squared']) > 0 else 0.0
            print("sd")
            print(r_squared)
            weighted_R2 = r['weighted_R2'][0] if len(r['weighted_R2']) > 0 else 0.0
            best_model_fit = r['best_model_fit']
            top_models = r['top_models']
            top_model_probs = r['top_model_probs']
        
        # Convert to more readable format
        top_models_list = []
        try:
            # Check if top_models is not NULL and has content
            if top_models is not None and hasattr(top_models, '__len__') and len(top_models) > 0:
                for i in range(min(5, len(top_models))):
                    model_dict = {'model_id': i+1, 'variables': 'Model ' + str(i+1)}
                    top_models_list.append(model_dict)
        except Exception as e:
            # Silently handle NULL case - this is expected when top_models is NULL
            top_models_list = []
        
        # Format the clean results table
        bma_summary = []
        for _, row in bma_table.iterrows():
            bma_summary.append({
                'Variable': row['predictors'],
                'PosteriorMean': row['post_means'],
                'PosteriorSD': row['post_sds'],
                'InclusionProb': row['pip'],
                'CILower': row['ci_lower'],
                'CIUpper': row['ci_upper']
            })
        
        try:
            top_model_probs_list = [float(p) for p in top_model_probs] if top_model_probs is not None else []
        except Exception as e:
            top_model_probs_list = []
        
        results = {
            'success': True,
            'bma_summary': bma_summary,
            'n_models_evaluated': int(n_models) if n_models is not None else 0,
            'r_squared': float(r_squared) if r_squared is not None else 0.0,
            'top_models': top_models_list,
            'top_model_probs': top_model_probs_list,
            'formula_used': formula_str,
            'response_variable': response_var,
            'predictor_variables': predictor_vars,
            'plot_generated': True,
            'plot_filename': 'BMA_Analysis.png'
        }
        
        # Add new statistics to results
        results['weighted_R2'] = float(weighted_R2) if weighted_R2 is not None else 0.0
        
        # Extract best model fit statistics
        best_model_stats = {}
        try:
            if best_model_fit is not None and len(best_model_fit) > 0:
                best_model_stats = {
                    'model_index': int(best_model_fit['model_index'].iloc[0]) if 'model_index' in best_model_fit.columns else 0,
                    'log_marginal_likelihood': float(best_model_fit['log_marginal_likelihood'].iloc[0]) if 'log_marginal_likelihood' in best_model_fit.columns else 0.0,
                    'R2': float(best_model_fit['R2'].iloc[0]) if 'R2' in best_model_fit.columns else 0.0
                }
        except Exception as e:
            print(f"Warning: Could not extract best model fit: {e}")
            best_model_stats = {
                'model_index': 0,
                'log_marginal_likelihood': 0.0,
                'R2': 0.0
            }
        
        results['best_model_fit'] = best_model_stats
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'bma_summary': [],
            'n_models_evaluated': 0,
            'r_squared': 0.0,
            'top_models': [],
            'top_model_probs': [],
            'formula_used': formula_str if 'formula_str' in locals() else '',
            'response_variable': response_var,
            'predictor_variables': predictor_vars
        }

def run_bma_analysis(df, response_var, predictor_vars, categorical_vars=None, original_formula=None):
    """
    Run Bayesian Model Averaging analysis using R's BMA package
    
    Parameters:
    -----------
    df : pandas.DataFrame
        The dataset to analyze
    response_var : str
        Name of the response variable
    predictor_vars : list
        List of predictor variable names
    categorical_vars : list, optional
        List of categorical variable names (will be converted to factors in R)
    
    Returns:
    --------
    dict : Dictionary containing BMA results and summary statistics
    """
    
    try:
        # Prepare the dataset for R
        analysis_df = df[[response_var] + predictor_vars].copy()
        
        # Send dataset to R
        with localconverter(ro.default_converter + pandas2ri.converter):
            ro.globalenv["df"] = analysis_df
        
        # Convert categorical variables to factors in R
        if categorical_vars is None:
            categorical_vars = []
        
        factor_conversion = ""
        for var in categorical_vars:
            if var in analysis_df.columns:
                factor_conversion += f"df${var} <- as.factor(df${var})\n"
        
        r(f'''
        df <- as.data.frame(df)
        {factor_conversion}
        ''')
        
        # Use the processed formula (already handles special characters)
        formula_str = formula
        
        # Load BMA and run bic.glm with plotting
        r_code = f'''
        if (!requireNamespace("BMA", quietly = TRUE)) install.packages("BMA", repos="https://cloud.r-project.org")
        library(BMA)
        
        # Define plotting function
        plot_bma_results <- function(file_path, model_name, bma_model, label_map = NULL) {{
          pic_name <- paste0(file_path, "/", model_name, ".png")
          
          # Extract coefficients directly from the BMA model
          # Get all variable names (excluding intercept) - use the actual names from probne0
          all_vars <- names(bma_model$probne0)
          # Remove intercept if it exists
          if ("(Intercept)" %in% all_vars) {{
            all_vars <- all_vars[all_vars != "(Intercept)"]
          }}
          
          # Check if we have any variables
          if (length(all_vars) == 0) {{
            # Return empty data frame if no variables
            return(data.frame(
              predictors = character(0),
              pip = numeric(0),
              post_means = numeric(0),
              post_sds = numeric(0)
            ))
          }}
          
          # Initialize vectors for all variables
          pip <- rep(0, length(all_vars))
          post_means <- rep(0, length(all_vars))
          post_sds <- rep(0, length(all_vars))
          predictors <- all_vars
          
          # Fill in values for variables that are in the model
          for (i in 1:length(all_vars)) {{
            var_name <- all_vars[i]
            pip[i] <- as.numeric(bma_model$probne0[var_name])
            post_means[i] <- as.numeric(bma_model$postmean[var_name])
            # postsd is a vector without names, so we need to access by position
            # Find the position of this variable in the original order
            var_pos <- which(names(bma_model$postmean) == var_name)
            if (length(var_pos) > 0) {{
              post_sds[i] <- as.numeric(bma_model$postsd[var_pos])
            }} else {{
              post_sds[i] <- 0  # Default value if position not found
            }}
          }}
          
          # Debug output removed for production
          
          coef_df <- data.frame(
            predictors = predictors,
            pip = pip,
            post_means = post_means,
            post_sds = post_sds,
            stringsAsFactors = FALSE
          )
          coef_df <- coef_df[order(coef_df$pip, decreasing = TRUE), ]
          
          pip <- coef_df$pip
          post_means <- coef_df$post_means
          post_sds <- coef_df$post_sds
          predictors <- coef_df$predictors
          
          if (!is.null(label_map)) {{
            predictors <- ifelse(predictors %in% names(label_map),
                                 label_map[predictors],
                                 predictors)
          }}
          
          # Check if we have valid data for plotting
          if (length(pip) == 0 || all(is.na(pip)) || all(is.na(post_means))) {{
            # Create a simple text plot if no valid data
            png(pic_name, width = 12, height = 6, units = "in", res = 300)
            par(mfrow = c(1, 1), mar = c(5, 5, 5, 5))
            plot(1, 1, type = "n", axes = FALSE, xlab = "", ylab = "")
            text(1, 1, "No valid data for plotting", cex = 1.5)
            dev.off()
          }} else {{
            png(pic_name, width = 12, height = 6, units = "in", res = 300)
            par(mfrow = c(1, 2), mar = c(10, 4, 4, 2) + 0.1, mgp = c(3, 0.7, 0),
                cex.axis = 0.8, cex.lab = 0.8, cex.main = 0.9)
            
            pip_colors <- ifelse(pip < 0.5, "grey", "skyblue")
            
            bp_pip <- barplot(
              pip, names.arg = predictors, ylim = c(0, 1), col = pip_colors,
              main = paste("Posterior Inclusion Probabilities\\\\n", model_name),
              ylab = "PIP", cex.names = 0.7, las = 2)
            abline(h = 0.5, col = "red", lty = 2, lwd = 1.5)
            
            # Calculate ylim safely
            y_range <- range(c(post_means - post_sds, post_means + post_sds), na.rm = TRUE)
            if (any(is.finite(y_range)) && diff(y_range) > 0) {{
              y_lim <- y_range * 1.3
            }} else {{
              y_lim <- c(-1, 1)
            }}
            
            bp_coef <- barplot(
              post_means, names.arg = predictors, col = "salmon",
              main = paste("Model-averaged Coefficients ±1 SD\\\\n", model_name),
              ylab = "Coefficient Estimate", cex.names = 0.7, las = 2,
              ylim = y_lim)
            
            arrows(x0 = bp_coef, y0 = post_means - post_sds,
                   x1 = bp_coef, y1 = post_means + post_sds,
                   angle = 90, code = 3, length = 0.05, lwd = 1.5)
            
            dev.off()
          }}
          
          return(coef_df)
        }}
        
        # Fit BMA model with error handling
        tryCatch({{
          bma_fit <- bic.glm({formula_str},
                             data = df, glm.family = gaussian())
          
          # Generate plots and get coefficient table
          model_name <- "BMA_Analysis"
          file_path <- getwd()
          bma_results <- plot_bma_results(file_path, model_name, bma_fit)
        }}, error = function(e) {{
          print(paste("Error in BMA fitting:", e$message))
          # Return empty results if BMA fails
          bma_results <- data.frame(
            predictors = character(0),
            pip = numeric(0),
            post_means = numeric(0),
            post_sds = numeric(0)
          )
          bma_fit <- NULL
        }})
        
        # Get model information
        if (!is.null(bma_fit)) {{
          n_models <- length(bma_fit$which)
          best_model_idx <- which.max(bma_fit$probne0)
          best_model_vars <- names(bma_fit$which)[bma_fit$which[best_model_idx,]]
          
          # Calculate R-squared for the best model
          if (length(best_model_vars) > 0) {{
            best_formula <- as.formula(paste("{response_var} ~", paste(best_model_vars, collapse = " + ")))
            best_model <- lm(best_formula, data = df)
            r_squared <- summary(best_model)$r.squared
          }} else {{
            r_squared <- 0
          }}
          
          # Get top models - simplified approach
          top_models <- head(bma_fit$which, 5)
          top_model_probs <- head(bma_fit$probne0, 5)
        }} else {{
          n_models <- 0
          r_squared <- 0
          top_models <- NULL
          top_model_probs <- NULL
        }}
        '''
        r(r_code)
        
        # Bring the results back into Python
        with localconverter(ro.default_converter + pandas2ri.converter):
            bma_table = r['bma_results']
            n_models = r['n_models'][0] if len(r['n_models']) > 0 else 0
            r_squared = r['r_squared'][0] if len(r['r_squared']) > 0 else 0.0
            top_models = r['top_models']
            top_model_probs = r['top_model_probs']
        
        # Debug output removed for production
        
        # Convert to more readable format
        # Handle top_models conversion - simplified approach
        top_models_list = []
        try:
            # Convert top_models to a simple list format
            if top_models is not None and len(top_models) > 0:
                # Create a simple representation of the top models
                for i in range(min(5, len(top_models))):
                    model_dict = {'model_id': i+1, 'variables': 'Model ' + str(i+1)}
                    top_models_list.append(model_dict)
        except Exception as e:
            print(f"Warning: Could not convert top_models: {e}")
            top_models_list = []
        
        # Format the clean results table
        bma_summary = []
        for _, row in bma_table.iterrows():
            bma_summary.append({
                'Variable': row['predictors'],
                'PosteriorMean': row['post_means'],
                'PosteriorSD': row['post_sds'],
                'InclusionProb': row['pip'],
                'CILower': row['ci_lower'],
                'CIUpper': row['ci_upper']
            })
        
        try:
            top_model_probs_list = [float(p) for p in top_model_probs] if top_model_probs is not None else []
        except Exception as e:
            top_model_probs_list = []
        
        results = {
            'success': True,
            'bma_summary': bma_summary,
            'n_models_evaluated': int(n_models) if n_models is not None else 0,
            'r_squared': float(r_squared) if r_squared is not None else 0.0,
            'top_models': top_models_list,
            'top_model_probs': top_model_probs_list,
            'formula_used': formula_str,
            'response_variable': response_var,
            'predictor_variables': predictor_vars,
            'plot_generated': True,
            'plot_filename': 'BMA_Analysis.png'
        }
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'bma_summary': [],
            'n_models_evaluated': 0,
            'r_squared': 0.0,
            'top_models': [],
            'top_model_probs': [],
            'formula_used': formula_str if 'formula_str' in locals() else '',
            'response_variable': response_var,
            'predictor_variables': predictor_vars
        }

def get_bma_plot_data(bma_results):
    """
    Generate plot data for BMA visualization
    
    Parameters:
    -----------
    bma_results : dict
        Results from run_bma_analysis
        
    Returns:
    --------
    dict : Plot data for visualization
    """
    
    if not bma_results['success'] or not bma_results['bma_summary']:
        return None
    
    # Create inclusion probability plot data
    summary_df = pd.DataFrame(bma_results['bma_summary'])
    
    # Sort by inclusion probability in descending order (highest to lowest)
    summary_df = summary_df.sort_values('InclusionProb', ascending=False)
    
    # Convert inclusion probabilities to percentages (0-100) for display
    inclusion_probs_pct = [prob * 100 for prob in summary_df['InclusionProb'].tolist()]
    
    # Create modern vertical bar chart data
    plot_data = {
        'type': 'bar',
        'x': summary_df['Variable'].tolist(),
        'y': inclusion_probs_pct,
        'text': [f"{prob:.1f}%" for prob in inclusion_probs_pct],
        'textposition': 'outside',
        'textfont': {
            'size': 14,
            'color': '#374151',
            'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'
        },
        'marker': {
            'color': inclusion_probs_pct,
            'colorscale': [
                [0.0, '#E5E7EB'],  # Light gray for low values
                [0.5, '#60A5FA'],  # Medium blue for medium values  
                [1.0, '#1D4ED8']   # Dark blue for high values
            ],
            'showscale': True,
            'colorbar': {
                'title': {
                    'text': 'Inclusion Probability (%)',
                    'font': {'size': 14, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
                },
                'titleside': 'right',
                'tickmode': 'array',
                'tickvals': [0, 20, 40, 60, 80, 100],
                'ticktext': ['0%', '20%', '40%', '60%', '80%', '100%'],
                'tickfont': {'size': 12, 'color': '#6B7280', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'},
                'len': 0.8,
                'thickness': 25,
                'x': 1.02,
                'xpad': 20
            },
            'line': {
                'color': 'rgba(255,255,255,0.8)',
                'width': 2
            },
            'opacity': 0.9
        },
        'hovertemplate': '<b>%{x}</b><br>' +
                        'Inclusion Probability: %{y:.1f}%<br>' +
                        '<extra></extra>',
        'hoverlabel': {
            'bgcolor': 'rgba(255,255,255,0.95)',
            'bordercolor': '#E5E7EB',
            'font': {'size': 13, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
        }
    }
    
    layout = {
        'title': {
            'text': 'Bayesian Model Averaging - Variable Inclusion Probabilities',
            'font': {'size': 18, 'color': '#1f2937', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'},
            'x': 0.5,
            'xanchor': 'center',
            'pad': {'t': 20, 'b': 20}
        },
        'xaxis': {
            'title': {
                'text': 'Variables',
                'font': {'size': 15, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
            },
            'showgrid': False,
            'categoryorder': 'array',
            'categoryarray': summary_df['Variable'].tolist(),
            'tickangle': -45,
            'tickfont': {'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif', 'size': 13, 'color': '#6B7280'},
            'linecolor': '#E5E7EB',
            'linewidth': 1
        },
        'yaxis': {
            'title': {
                'text': 'Inclusion Probability (%)',
                'font': {'size': 15, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
            },
            'showgrid': True,
            'gridcolor': '#F3F4F6',
            'gridwidth': 1,
            'zeroline': True,
            'zerolinecolor': '#D1D5DB',
            'zerolinewidth': 2,
            'tickfont': {'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif', 'size': 13, 'color': '#6B7280'},
            'linecolor': '#E5E7EB',
            'linewidth': 1
        },
        'height': 600,
        'margin': {
            'l': 100,   # Space for y-axis
            'r': 150,   # Space for colorbar
            't': 200,   # Space for title and outside bar tags
            'b': 200    # Space for x-axis variable names and label
        },
        'bargap': 0.4,
        'barmode': 'group',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'showlegend': False,
        'hovermode': 'closest',
        'dragmode': 'zoom',
        'modebar': {
            'bgcolor': 'rgba(255,255,255,0.8)',
            'color': '#374151',
            'activecolor': '#1D4ED8'
        }
    }
    
    return {
        'data': [plot_data],
        'layout': layout
    }

def get_bma_coefficients_plot_data(bma_results):
    """
    Generate plot data for BMA coefficients visualization
    
    Parameters:
    -----------
    bma_results : dict
        Results from run_bma_analysis
        
    Returns:
    --------
    dict : Plot data for coefficients visualization
    """
    
    if not bma_results['success'] or not bma_results['bma_summary']:
        return None
    
    # Create coefficient plot data
    summary_df = pd.DataFrame(bma_results['bma_summary'])
    
    # Sort by absolute posterior mean in descending order (highest absolute effect to lowest)
    summary_df['abs_posterior_mean'] = summary_df['PosteriorMean'].abs()
    summary_df = summary_df.sort_values('abs_posterior_mean', ascending=False)
    
    # Create vertical bar chart data for coefficients
    plot_data = {
        'type': 'bar',
        'x': summary_df['Variable'].tolist(),
        'y': summary_df['PosteriorMean'].tolist(),
        'text': [f"{coef:.3f}" for coef in summary_df['PosteriorMean'].tolist()],
        'textposition': 'outside',
        'textfont': {
            'size': 14,
            'color': '#374151',
            'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'
        },
        'marker': {
            'color': summary_df['PosteriorMean'].tolist(),
            'colorscale': [
                [0.0, '#DC2626'],  # Red for negative values
                [0.5, '#E5E7EB'],  # Light gray for zero
                [1.0, '#059669']   # Green for positive values
            ],
            'showscale': True,
            'colorbar': {
                'title': {
                    'text': 'Coefficient Value',
                    'font': {'size': 14, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
                },
                'titleside': 'right',
                'tickfont': {'size': 12, 'color': '#6B7280', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'},
                'len': 0.8,
                'thickness': 25,
                'x': 1.02,
                'xpad': 20
            },
            'line': {
                'color': 'rgba(255,255,255,0.8)',
                'width': 2
            },
            'opacity': 0.9
        },
        'hovertemplate': '<b>%{x}</b><br>' +
                        'Coefficient: %{y:.3f}<br>' +
                        'Posterior SD: %{customdata:.3f}<br>' +
                        '<extra></extra>',
        'customdata': summary_df['PosteriorSD'].tolist(),
        'hoverlabel': {
            'bgcolor': 'rgba(255,255,255,0.95)',
            'bordercolor': '#E5E7EB',
            'font': {'size': 13, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
        },
        'error_y': {
            'type': 'data',
            'array': summary_df['PosteriorSD'].tolist(),
            'visible': True,
            'color': '#374151',
            'thickness': 2,
            'width': 4
        }
    }
    
    layout = {
        'title': {
            'text': 'Model-Averaged Coefficients ±1 SD',
            'font': {'size': 18, 'color': '#1f2937', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'},
            'x': 0.5,
            'xanchor': 'center',
            'pad': {'t': 20, 'b': 20}
        },
        'xaxis': {
            'title': {
                'text': 'Variables',
                'font': {'size': 15, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
            },
            'showgrid': False,
            'categoryorder': 'array',
            'categoryarray': summary_df['Variable'].tolist(),
            'tickfont': {'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif', 'size': 13, 'color': '#6B7280'},
            'linecolor': '#E5E7EB',
            'linewidth': 1
        },
        'yaxis': {
            'title': {
                'text': 'Coefficient Estimate',
                'font': {'size': 15, 'color': '#374151', 'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif'}
            },
            'showgrid': True,
            'gridcolor': '#F3F4F6',
            'gridwidth': 1,
            'zeroline': True,
            'zerolinecolor': '#D1D5DB',
            'zerolinewidth': 2,
            'tickfont': {'family': 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, sans-serif', 'size': 13, 'color': '#6B7280'},
            'linecolor': '#E5E7EB',
            'linewidth': 1
        },
        'height': 600,
        'margin': {
            'l': 100,   # Space for y-axis label
            'r': 150,   # Space for colorbar
            't': 200,   # Space for title and outside bar tags
            'b': 120    # Space for x-axis variable names
        },
        'bargap': 0.3,
        'barmode': 'group',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'showlegend': False,
        'hovermode': 'closest',
        'dragmode': 'zoom',
        'modebar': {
            'bgcolor': 'rgba(255,255,255,0.8)',
            'color': '#374151',
            'activecolor': '#1D4ED8'
        }
    }
    
    return {
        'data': [plot_data],
        'layout': layout
    }

def format_bma_results(bma_results):
    """
    Format BMA results for display in HTML template
    
    Parameters:
    -----------
    bma_results : dict
        Results from run_bma_analysis
        
    Returns:
    --------
    dict : Formatted results for template
    """
    
    if not bma_results['success']:
        return {
            'error': bma_results.get('error', 'Unknown error occurred'),
            'has_results': False
        }
    
    # Format the summary table
    summary_data = []
    for row in bma_results['bma_summary']:
        summary_data.append({
            'variable': row['Variable'],
            'posterior_mean': f"{row['PosteriorMean']:.4f}",
            'posterior_sd': f"{row['PosteriorSD']:.4f}",
            'inclusion_prob': f"{row['InclusionProb']:.4f}",
            'inclusion_prob_pct': f"{row['InclusionProb']*100:.1f}%",
            'ci_lower': f"{row['CILower']:.4f}",
            'ci_upper': f"{row['CIUpper']:.4f}"
        })
    
    # Format top models
    top_models_data = []
    for i, (model, prob) in enumerate(zip(bma_results['top_models'], bma_results['top_model_probs'])):
        # Convert boolean array to variable names
        included_vars = [var for var, included in model.items() if included]
        top_models_data.append({
            'rank': i + 1,
            'variables': ', '.join(included_vars) if included_vars else 'Intercept only',
            'probability': f"{prob:.4f}",
            'probability_pct': f"{prob*100:.1f}%"
        })
    
    return {
        'has_results': True,
        'summary_data': summary_data,
        'top_models_data': top_models_data,
        'n_models_evaluated': bma_results['n_models_evaluated'],
        'r_squared': f"{bma_results['r_squared']:.4f}",
        'formula_used': bma_results['formula_used'],
        'response_variable': bma_results['response_variable'],
        'predictor_variables': bma_results['predictor_variables'],
        'plot_data': get_bma_plot_data(bma_results),
        'coefficients_plot_data': get_bma_coefficients_plot_data(bma_results),
        'plot_generated': bma_results.get('plot_generated', False),
        'plot_filename': bma_results.get('plot_filename', 'BMA_Analysis.png'),
        'weighted_R2': bma_results.get('weighted_R2', 0.0),
        'best_model_fit': bma_results.get('best_model_fit', {})
    }

class BMAModule:
    """
    Bayesian Model Averaging module for StatBox
    """
    
    def ui_schema(self):
        """Return the UI schema for BMA analysis"""
        return {
            'formula': {
                'type': 'text',
                'label': 'Formula',
                'placeholder': 'e.g., y ~ x1 + x2 + x3',
                'help': 'Enter the regression formula. Use variable names from your dataset.',
                'required': True
            },
            'categorical_vars': {
                'type': 'text',
                'label': 'Categorical Variables (Optional)',
                'placeholder': 'e.g., region, category, group',
                'help': 'Comma-separated list of categorical variable names (will be converted to factors)',
                'required': False
            }
        }
    
    def run(self, df, formula, options=None, **kwargs):
        """
        Run Bayesian Model Averaging analysis
        
        Parameters:
        -----------
        df : pandas.DataFrame
            The dataset to analyze
        formula : str
            The regression formula (e.g., 'y ~ x1 + x2 + x3')
        options : dict, optional
            Additional options for the analysis
        **kwargs : dict
            Additional keyword arguments
            
        Returns:
        --------
        dict : Analysis results including BMA summary and plots
        """
        
        if options is None:
            options = {}
        
        try:
            # Handle column names with special characters for proper processing
            formula, df_renamed, column_mapping = _quote_column_names_with_special_chars(df, formula)
            
            # Parse the formula to extract response and predictor variables
            formula_parts = formula.split('~')
            if len(formula_parts) != 2:
                raise ValueError("Formula must be in the format 'response ~ predictor1 + predictor2'")
            
            response_var = formula_parts[0].strip()
            predictor_str = formula_parts[1].strip()
            
            # Parse predictor variables - handle interaction terms and other R syntax
            predictor_terms = [term.strip() for term in predictor_str.split('+')]
            
            # Extract individual variables from terms (handle interactions, etc.)
            individual_vars = set()
            for term in predictor_terms:
                # Handle interaction terms (e.g., "var1 * var2" or "var1:var2")
                if '*' in term or ':' in term:
                    # Split by * or : and add individual variables
                    if '*' in term:
                        vars_in_term = [v.strip() for v in term.split('*')]
                    else:  # ':'
                        vars_in_term = [v.strip() for v in term.split(':')]
                    individual_vars.update(vars_in_term)
                else:
                    # Regular variable
                    individual_vars.add(term)
            
            # Convert to list for consistency
            predictor_vars = list(individual_vars)
            
            # Get categorical variables from options
            categorical_vars = []
            if 'categorical_vars' in options and options['categorical_vars']:
                categorical_vars = [var.strip() for var in options['categorical_vars'].split(',')]
            
            # Check if response variable exists in dataset
            if response_var not in df_renamed.columns:
                raise ValueError(f"Response variable '{response_var}' not found in dataset")
            
            # Check if individual predictor variables exist in dataset
            missing_vars = [var for var in predictor_vars if var not in df_renamed.columns]
            if missing_vars:
                raise ValueError(f"Predictor variables not found in dataset: {missing_vars}")
            
            # Run BMA analysis using BAS library with MCMC method
            import os
            from django.conf import settings
            media_path = getattr(settings, 'MEDIA_ROOT', os.path.join(os.getcwd(), 'media'))
            bma_results = run_bma_analysis_bas(df_renamed, response_var, predictor_vars, categorical_vars, original_formula=formula, media_path=media_path)
            
            if not bma_results['success']:
                return {
                    'success': False,
                    'error': bma_results['error'],
                    'results': None
                }
            
            # Format results for display
            formatted_results = format_bma_results(bma_results)
            
            return {
                'success': True,
                'results': formatted_results,
                'bma_data': bma_results,
                'formula': formula,
                'response_variable': response_var,
                'predictor_variables': predictor_vars
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'results': None
            }
