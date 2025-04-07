from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd
from werkzeug.utils import secure_filename
from acc_anal_2 import AccountManagementAnalyzer
from flask import Flask, request, jsonify

app = Flask(__name__)

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
    print(file,password)
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
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
                analyzer.trans_pred()
                analyzer.budget_system()

                table_html = df.to_html(classes='table table-striped')

                return render_template("result.html", filename=filename, table_html=table_html)

    return redirect(url_for('index'))





if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
