from io import StringIO
from flask import Flask, render_template, request, jsonify
import lascheck  # модуль, где логика проверки .las файлов
from werkzeug.utils import secure_filename
import Test_1
import Test_2
import Test_3

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index_3.html')

@app.route('/validate', methods=['POST'])
def validate():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Имя файла отсутствует'}), 400

    if not file.filename.lower().endswith('.las'):
        return jsonify({'error': 'Допускаются только LAS файлы'}), 400
    

    file_content = file.read().decode('CP1251', errors='replace')
    # detailed_result = Test_1.validate_las_file_detailed(file_content)
    detailed_result = Test_3.validate_las_file_enhanced(file_content)

    # detailed_result= Test_2.validate_las_file_comprehensive(file)

    # error=[]
    # try:
    #     las = lascheck.read(file_content)
    #     error = las.get_non_conformities()
    # except Exception as e:
    #     # print(e)
    #     error.append(str(e))
    # results = {
    #             "summary": "Файл проверен",
    #             "errors": error,
    #             "valid": len(error) == 0
    # }

    return jsonify(detailed_result)

if __name__=='__main__':
    app.run(debug=True)