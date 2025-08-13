from io import StringIO
from flask import Flask, render_template, request, jsonify
import lascheck  # модуль, где логика проверки .las файлов
from werkzeug.utils import secure_filename

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index_2.html')

@app.route('/validate', methods=['POST'])
def validate():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Имя файла отсутствует'}), 400

    if not file.filename.lower().endswith('.las'):
        return jsonify({'error': 'Допускаются только LAS файлы'}), 400
    

    file_content = file.read().decode('utf-8', errors='replace')
    error=[]
    try:
        las = lascheck.read(file_content)
        error = las.get_non_conformities()
    except Exception as e:
        # print(e)
        error.append(str(e))
    results = {
                "summary": "Файл проверен",
                "errors": error,
                "valid": len(error) == 0
    }

    return jsonify(results)

if __name__=='__main__':
    app.run(debug=True)