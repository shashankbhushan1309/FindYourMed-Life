import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Load the dataset
file_path = "refined_okq.csv"
try:
    df = pd.read_csv(file_path)
    print("CSV file loaded successfully.")
except Exception as e:
    print(f"Error loading CSV file: {e}")
    df = pd.DataFrame()

# Clean the dataset by dropping rows with missing values in key columns
df.dropna(subset=['name', 'price(₹)', 'short_composition1'], inplace=True)

# Feature Engineering: Create a dictionary for medicine composition lookup
composition_dict = df.groupby('name', group_keys=False).apply(
    lambda x: x[['short_composition1', 'short_composition2', 'price(₹)']].to_dict('records')
).to_dict()

# Convert all keys in composition_dict to lowercase and strip spaces
composition_dict = {k.strip().lower(): v for k, v in composition_dict.items()}

def find_cheaper_medicines(medicine_name):
    medicine_name = medicine_name.strip().lower()
    if medicine_name in composition_dict:
        compositions = []
        for comp_record in composition_dict[medicine_name]:
            compositions.append(comp_record['short_composition1'])
            if pd.notna(comp_record['short_composition2']):
                compositions.append(comp_record['short_composition2'])
        
        compositions = list(set([comp for comp in compositions if pd.notna(comp)]))
        
        same_composition_meds = df[df.apply(
            lambda row: any(comp in row['short_composition1'] for comp in compositions) or
                        (pd.notna(row['short_composition2']) and any(comp in row['short_composition2'] for comp in compositions)),
            axis=1
        )]
        
        input_medicine_price = df[df['name'].str.strip().str.lower() == medicine_name]['price(₹)'].min()
        
        cheaper_meds = same_composition_meds[same_composition_meds['price(₹)'] < input_medicine_price]
        
        cheaper_meds = cheaper_meds.sort_values(by='price(₹)')
        
        result = cheaper_meds[['name', 'price(₹)']].rename(columns={'price(₹)': 'price'}).to_dict('records')
        
        return result
    else:
        return None

@app.route('/recommend', methods=['GET'])
def recommend():
    try:
        medicine_name = request.args.get('medicine_name')
        if not medicine_name:
            return jsonify({"error": "No medicine name provided"}), 400
        
        recommendations = find_cheaper_medicines(medicine_name)
        if recommendations is not None:
            if len(recommendations) > 0:
                return jsonify({"recommendations": recommendations})
            else:
                return jsonify({"message": "No cheaper medicines found with the same composition"}), 200
        else:
            return jsonify({"error": "Medicine not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(debug=True, port=5001)  # Running on port 5001
