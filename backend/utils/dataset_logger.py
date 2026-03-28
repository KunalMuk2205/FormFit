import os
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Base directory for datasets
DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset")

def log_rep_features(exercise_name, schema, features):
    """
    Appends a row of features to the dataset CSV for the given exercise.
    Creates the directory and CSV file with headers if they don't exist.
    """
    try:
        if not os.path.exists(DATASET_DIR):
            os.makedirs(DATASET_DIR)
            
        csv_path = os.path.join(DATASET_DIR, f"{exercise_name}.csv")
        file_exists = os.path.exists(csv_path)
        
        # Ensure all schema keys exist in features, defaulting to empty string
        row_data = [features.get(key, "") for key in schema]
        
        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write header if file operates for the first time
            if not file_exists:
                writer.writerow(schema)
                
            print(f"DEBUG: Writing row to {exercise_name}.csv -> {row_data}")
            writer.writerow(row_data)
            
    except Exception as e:
        logger.error(f"Failed to log rep features to {exercise_name}.csv: {e}")
