library(gamm4)
library(readr)
library(car) # For VIF checking

# 1. Load data
df <- read_csv("Projects/legacy_data/data_for_r_all_rois.csv")

# Ensure categorical variables are factors
df$sex <- as.factor(df$sex)
df$subject_id <- as.factor(df$subject_id)

# 2. Identify all unique ROIs
roi_list <- unique(df$region_label)

all_results_list <- list()
all_viz_list <- list() 

# 3. Loop through each ROI
for (roi_name in roi_list) {
  cat("Processing ROI:", roi_name, "...\n")
  
  df_sub <- subset(df, region_label == roi_name)
  
  # --- STEP 1: ISOLATE AGE EFFECT (The Nuisance Model) ---
  # We fit a model using only biological/demographic factors.
  age_model <- tryCatch({
    gamm4(volume_mm3 ~ s(age_in_years) + tiv + sex, 
          random = ~ (1 | subject_id), 
          data = df_sub)
  }, error = function(e) {
    cat("  ! Age Model failed for", roi_name, "\n")
    return(NULL)
  })
  
  if (!is.null(age_model)) {
    # Extract residuals: This is volume variance that AGE cannot explain
    df_sub$age_corrected_vol <- residuals(age_model$gam)
    
    # --- STEP 2: ANALYZE BIRTH YEAR (The Cohort Model) ---
    # Now we see if Birth Year explains the leftover "residual" variance.
    cohort_model <- tryCatch({
      # Using a smooth for birth_year to capture non-linear cohort trends
      gam(age_corrected_vol ~ s(birth_year), data = df_sub)
    }, error = function(e) {
      cat("  ! Cohort Model failed for", roi_name, "\n")
      return(NULL)
    })
    
    if (!is.null(cohort_model)) {
      summ <- summary(cohort_model)
      
      # --- Process Smooth Effects (Cohort Effect) ---
      smooth <- as.data.frame(summ$s.table)
      colnames(smooth) <- c("edf", "Ref_df", "Statistic", "PValue")
      smooth$term <- rownames(smooth)
      smooth$roi <- roi_name
      
      all_results_list[[roi_name]] <- smooth
      
      # --- Visualization Data ---
      # Create a grid across the birth year range
      grid <- data.frame(
        birth_year = seq(min(df_sub$birth_year), max(df_sub$birth_year), length.out = 100)
      )
      
      preds <- predict(cohort_model, newdata = grid, se.fit = TRUE)
      
      viz_df <- data.frame(
        roi = roi_name,
        birth_year = grid$birth_year,
        fit = preds$fit,
        se  = preds$se.fit
      )
      
      all_viz_list[[roi_name]] <- viz_df
    }
  }
}

# 4. Merge and Export
if (length(all_results_list) > 0) {
  all_effects <- do.call(rbind, all_results_list)
  all_curves <- do.call(rbind, all_viz_list)
  
  write.csv(all_effects, 'cohort_residual_effects.csv', row.names = FALSE)
  write.csv(all_curves, 'cohort_residual_curves.csv', row.names = FALSE)
  cat("Done! Cohort effects isolated and saved.\n")
} else {
  cat("No models were successfully computed.\n")
}