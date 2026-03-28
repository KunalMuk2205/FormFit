import pandas as pd
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

def train_exercise_model(exercise_name, csv_path, model_out_path):
    print(f"--- Training Model for {exercise_name} ---")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    df = pd.read_csv(csv_path)
    print("Detected columns:", list(df.columns))
    
    # Clean data
    drop_cols = ["timestamp", "label_specific"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    
    # Convert labels: good_form -> 1, bad_form -> 0
    df["label_binary"] = df["label_binary"].apply(lambda x: 1 if x == "good_form" else 0)
    
    # Split
    X = df.drop(columns=["label_binary"])
    y = df["label_binary"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc:.4f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    
    print("Feature Importance:")
    importances = clf.feature_importances_
    for name, imp in sorted(zip(X.columns, importances), key=lambda x: x[1], reverse=True):
        print(f"  {name}: {imp:.4f}")
        
    # Save
    os.makedirs(os.path.dirname(model_out_path), exist_ok=True)
    with open(model_out_path, "wb") as f:
        pickle.dump(clf, f)
    print(f"-> Saved {exercise_name} model to {model_out_path}\n")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    pushup_csv = os.path.join(base_dir, "dataset", "pushups.csv")
    pushup_model = os.path.join(base_dir, "ml", "pushup_model.pkl")
    train_exercise_model("Pushups", pushup_csv, pushup_model)
    
    squat_csv = os.path.join(base_dir, "dataset", "squats.csv")
    squat_model = os.path.join(base_dir, "ml", "squat_model.pkl")
    train_exercise_model("Squats", squat_csv, squat_model)
