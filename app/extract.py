import glob
import os
import pandas as pd

def load_dataframes():
    # Load each CSV file into a DataFrame and store in a dictionary
    dataframes = {}
    for file_path in glob.glob("import/*.csv"):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        df = pd.read_csv(file_path)
        dataframes[file_name] = df
    return dataframes