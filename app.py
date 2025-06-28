from flask import Flask, render_template, request, redirect, url_for, session
import os
import pandas as pd
from werkzeug.utils import secure_filename
from main import AccountManagementAnalyzer
from flask import Flask, request, jsonify
import pickle
import tempfile
import numpy as np

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'  # Folder for graphs
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER

# Allowed file types
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    password = request.form.get('password', '')  # Get password input

    if not file or not file.filename:
        return redirect(request.url)

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Process the file using AccountManagementAnalyzer
        analyzer = AccountManagementAnalyzer()
        
        unprotected_pdf = analyzer.remove_pdf_password(filepath, password)  # Decrypt PDF
        if unprotected_pdf:
            csv_file = analyzer.analyze(unprotected_pdf)  # Convert PDF to CSV
            if csv_file:
                df = analyzer.show_data()
                analyzer.preprocessing_and_analysis()
                analyzer.classification()

                # Store csv_file in session for later use in prediction
                session['csv_file'] = csv_file

                table_html = df.to_html(classes='table table-striped')

                return render_template("result.html", filename=filename, table_html=table_html)

    return redirect(url_for('index'))

@app.route('/predict', methods=['POST'])
def predict():
    prediction_days = request.form.get('days', '30')
    try:
        future_days = int(prediction_days)
    except ValueError:
        future_days = 30
    
    if 'csv_file' in session:
        analyzer = AccountManagementAnalyzer()
        analyzer.csv_file = session['csv_file']
        analyzer.show_data()
        analyzer.preprocessing_and_analysis()
        analyzer.classification()
        
        current_balance, prediction_df = analyzer.trans_pred(future_days)
        predicted_balance = prediction_df["ARIMA_Prediction"].iloc[-1]
        
        budget_data = analyzer.budget_system()
        
        session['future_days'] = future_days
        
        # Convert prediction_df to dict and ensure all values are JSON serializable
        prediction_data = prediction_df.to_dict(orient='records')
        
        # Convert NumPy types to native Python types in prediction_data
        for record in prediction_data:
            for key, value in record.items():
                if hasattr(value, 'item'):  # Check if it's a NumPy type
                    record[key] = value.item()
                elif isinstance(value, (np.integer, np.floating)):
                    record[key] = value.item()
        
        # Convert NumPy types in budget_data
        if budget_data:
            for key, value in budget_data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if hasattr(sub_value, 'item'):
                            budget_data[key][sub_key] = sub_value.item()
                        elif isinstance(sub_value, (np.integer, np.floating)):
                            budget_data[key][sub_key] = sub_value.item()
                elif hasattr(value, 'item'):
                    budget_data[key] = value.item()
                elif isinstance(value, (np.integer, np.floating)):
                    budget_data[key] = value.item()
        
        return jsonify({
            'success': True, 
            'days': future_days,
            'current_balance': f"₹{float(current_balance):.2f}",
            'predicted_balance': f"₹{float(predicted_balance):.2f}",
            'prediction_data': prediction_data,
            'budget_data': budget_data
        })
    
    return jsonify({'success': False, 'error': 'No data available for prediction'})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)