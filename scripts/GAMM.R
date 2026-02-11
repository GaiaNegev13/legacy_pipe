library(gamm4)
library(readr)

# 1. Load data
df <- read_csv("Projects/legacy_data/data_for_r_all_rois.csv")

# Ensure categorical variables are factors
df$sex <- as.factor(df$sex)
df$subject_id <- as.factor(df$subject_id)

# 2. Identify all unique ROIs
roi_list <- unique(df$region_label)

# Prepare a list to store every single result row
all_results_list <- list()
all_viz_list <- list() 

# 3. Loop through each ROI
for (roi_name in roi_list) {
  cat("Processing ROI:", roi_name, "...\n")
  
  df_sub <- subset(df, region_label == roi_name)
  
  model_list <- tryCatch({
    gamm4(volume_mm3 ~ s(age_in_years) + s(birth_year) + tiv + sex, 
          random = ~ (1 | subject_id), 
          data = df_sub, 
          family = gaussian())
  }, error = function(e) {
    cat("  ! Model failed for", roi_name, "\n")
    return(NULL)
  })
  
  if (!is.null(model_list)) {
    summ <- summary(model_list$gam)
    
    # --- Process Fixed Effects ---
    fixed <- as.data.frame(summ$p.table)
    colnames(fixed) <- c("Estimate", "StdError", "Statistic", "PValue")
    fixed$term <- rownames(fixed)
    fixed$effect_type <- "fixed"
    
    # --- Process Smooth Effects ---
    smooth <- as.data.frame(summ$s.table)
    # Smooths don't have StdError, so we fill with NA to keep the table uniform
    colnames(smooth) <- c("Estimate", "Ref_df", "Statistic", "PValue")
    smooth$StdError <- NA 
    smooth$term <- rownames(smooth)
    smooth$effect_type <- "smooth"
    
    # Reorder columns to match for merging
    cols_to_keep <- c("term", "effect_type", "Estimate", "StdError", "Statistic", "PValue")
    
    # Combine fixed and smooth for this ROI
    roi_combined <- rbind(fixed[, cols_to_keep], smooth[, cols_to_keep])
    roi_combined$roi <- roi_name
    
    all_results_list[[roi_name]] <- roi_combined
    
    # Create a grid for smooth visualization (e.g., Age from 20 to 90)
    # We hold TIV and Birth Year at their means, and Sex at its reference level
    grid <- data.frame(
      birth_year = seq(min(df_sub$birth_year), max(df_sub$birth_year), length.out = 100),
      age_in_years = mean(df_sub$age_in_years),
      tiv = mean(df_sub$tiv),
      sex = levels(df$sex)[1],
      subject_id = df_sub$subject_id[1] # This is ignored by using re.form=NA
    )
    
    # Predict volume and standard errors
    # re.form = NA ensures we see the population curve, not a specific person
    preds <- predict(model_list$gam, newdata = grid, se.fit = TRUE)
    
    # Store coordinates for Python
    viz_df <- data.frame(
      roi = roi_name,
      birth_year = grid$birth_year,
      fit = preds$fit,
      se  = preds$se.fit
    )
    
    # Append to a master visualization list
    all_viz_list[[roi_name]] <- viz_df
  }
}

# 4. Merge all ROIs into one big table
all_effects <- do.call(rbind, all_results_list)

# 5. Export to one CSV for Python
write.csv(all_effects, 'all_effects.csv', row.names = FALSE)
write.csv(do.call(rbind, all_viz_list), 'all_roi_curves.csv', row.names = FALSE)
cat("Done! Results saved to all_effects.csv\n")
