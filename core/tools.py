import pandas as pd
import json
import ast
from unidecode import unidecode

def csv_to_json(csv_file, json_file):
    # Read CSV file
    df = pd.read_csv(csv_file, header=None)

    # Convert to dictionary format
    result = {}
    for key, value in df.itertuples(index=False):
        result.setdefault(key, []).append(value)
    
    # Save to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

def normalize_json(input_file, output_file='resource/QN2Nom_without_accent.json'):
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    normalized_data = {}

    for key, values in data.items():
        normalized_key = unidecode(key)  # Convert key to ASCII
        if normalized_key in normalized_data:
            normalized_data[normalized_key].extend(values)  # Merge values
        else:
            normalized_data[normalized_key] = values

    # Remove duplicates from the values
    for key in normalized_data:
        normalized_data[key] = list(set(normalized_data[key]))

    # Write to the output JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f, ensure_ascii=False, indent=4)



# Function to convert sim column to list format
def process_sim_column(sim_value):
    return sim_value.split(',')

def convert_sim_dict(file_name):
    df = pd.read_csv(file_name)  
    # Apply the function to the sim column
    df["sim"] = df["sim"].apply(process_sim_column)
    df.to_csv(file_name, index=False)