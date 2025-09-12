import glob
import json
import os
import pandas as pd

def load_csv():
    # Load each CSV file into a DataFrame and store in a dictionary
    dataframes = {}
    for file_path in glob.glob("import/*.csv"):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        df = pd.read_csv(file_path)
        dataframes[file_name] = df
    return dataframes

def load_json():
    # Load each JSON file into a dictionary and store in a dictionary
    data = {}
    for file_path in glob.glob("import/*.json"):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        with open(file_path, 'r') as f:
            data[file_name] = json.load(f)
    return data

