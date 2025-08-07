from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
import os
from werkzeug.utils import secure_filename
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this to a secure secret key

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'las'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class LASFileChecker:
    """
    Professional LAS file validation class based on LAS 2.0 standards.
    Implements comprehensive checking as described in your requirements.
    """
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.info = {}
        self.content = ""
        self.lines = []
        
    def check_file(self):
        """Main method to check the LAS file according to LAS 2.0 standards."""
        try:
            # Read file with proper encoding handling
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as file:
                self.content = file.read()
                
            self.lines = [line.rstrip() for line in self.content.split('\n')]
            
            # Perform comprehensive validation
            self._check_file_structure()
            self._check_version_section()
            self._check_well_section()
            self._check_curve_section()
            self._check_data_section()
            self._check_section_order()
            self._check_empty_lines()
            
            # Generate summary
            self._generate_summary()
            
            return {
                'valid': len(self.errors) == 0,
                'errors': self.errors,
                'warnings': self.warnings,
                'info': self.info
            }
            
        except Exception as e:
            self.errors.append(f"Ошибка при чтении файла: {str(e)}")
            return {
                'valid': False,
                'errors': self.errors,
                'warnings': self.warnings,
                'info': self.info
            }
    
    def _check_file_structure(self):
        """Check basic LAS file structure and required sections."""
        sections_found = []
        section_counts = {}
        
        for i, line in enumerate(self.lines):
            line_stripped = line.strip().upper()
            if line_stripped.startswith('~'):
                section_type = line_stripped.split()[0] if line_stripped.split() else line_stripped
                sections_found.append((section_type, i + 1))
                section_counts[section_type] = section_counts.get(section_type, 0) + 1
        
        # Check for required sections
        required_sections = ['~V', '~W', '~C', '~A']
        for section in required_sections:
            if not any(s[0] == section for s in sections_found):
                self.errors.append(f"Отсутствует обязательный раздел: {section}")
        
        # Check for duplicate sections (LAS 2.0 rule)
        for section, count in section_counts.items():
            if section in ['~V', '~W', '~C', '~A', '~P', '~O'] and count > 1:
                self.errors.append(f"В файле LAS 2.0 раздел {section} может встречаться только один раз (найдено: {count})")
        
        self.info['sections_found'] = [s[0] for s in sections_found]
        self.info['section_positions'] = sections_found
        self.info['total_lines'] = len(self.lines)
    
    def _check_section_order(self):
        """Check if sections are in correct order."""
        sections = []
        for line in self.lines:
            line_stripped = line.strip().upper()
            if line_stripped.startswith('~'):
                section_type = line_stripped.split()[0] if line_stripped.split() else line_stripped
                sections.append(section_type)
        
        # ~V should be first
        if sections and sections[0] != '~V':
            self.errors.append("Раздел ~V должен быть первым в файле")
        
        # ~A should be last
        if sections and sections[-1] != '~A':
            self.errors.append("Раздел данных ~A должен быть последним разделом в файле")
    
    def _check_empty_lines(self):
        """Check for internal empty lines in sections."""
        current_section = None
        in_section = False
        
        for i, line in enumerate(self.lines):
            line_stripped = line.strip()
            
            # Check for section headers
            if line_stripped.upper().startswith('~'):
                current_section = line_stripped.upper().split()[0] if line_stripped.split() else line_stripped.upper()
                in_section = True
                continue
            
            # Check for empty lines within sections
            if in_section and not line_stripped and current_section:
                # Look ahead to see if we're still in the same section
                next_section_found = False
                for j in range(i + 1, len(self.lines)):
                    next_line = self.lines[j].strip()
                    if next_line.upper().startswith('~'):
                        next_section_found = True
                        break
                    elif next_line:  # Non-empty line found
                        break
                
                if not next_section_found and i < len(self.lines) - 1:
                    self.warnings.append(f"Пустая строка внутри раздела {current_section} на строке {i + 1}")
    
    def _check_version_section(self):
        """Check ~V (VERSION) section."""
        version_section = self._extract_section('~V')
        version_info = {}
        
        if not version_section:
            self.errors.append("Раздел ~V (VERSION INFORMATION) отсутствует")
            return
        
        # Parse version parameters
        for line_num, line in version_section:
            if line.strip() and not line.strip().startswith('#'):
                parsed = self._parse_parameter_line(line)
                if parsed:
                    mnemonic, unit, value, description = parsed
                    version_info[mnemonic] = {
                        'unit': unit,
                        'value': value,
                        'description': description,
                        'line': line_num
                    }
        
        # Check required parameters
        if 'VERS' not in version_info:
            self.errors.append("Раздел ~V должен содержать параметр VERS")
        
        if 'WRAP' not in version_info:
            self.errors.append("Раздел ~V должен содержать параметр WRAP")
        else:
            wrap_value = version_info['WRAP'].get('value', '').upper()
            if wrap_value not in ['YES', 'NO']:
                self.warnings.append(f"Значение WRAP должно быть YES или NO, найдено: {wrap_value}")
        
        self.info['version_info'] = version_info
    
    def _check_well_section(self):
        """Check ~W (WELL INFORMATION) section."""
        well_section = self._extract_section('~W')
        well_info = {}
        
        if not well_section:
            self.errors.append("Раздел ~W (WELL INFORMATION SECTION) является обязательным")
            return
        
        # Parse well parameters
        for line_num, line in well_section:
            if line.strip() and not line.strip().startswith('#'):
                parsed = self._parse_parameter_line(line)
                if parsed:
                    mnemonic, unit, value, description = parsed
                    well_info[mnemonic] = {
                        'unit': unit,
                        'value': value,
                        'description': description,
                        'line': line_num
                    }
        
        # Check required parameters
        required_well_params = ['STRT', 'STOP', 'STEP', 'NULL', 'COMP', 'WELL', 'FLD', 'LOC', 'SRVC', 'DATE']
        for param in required_well_params:
            if param not in well_info:
                self.errors.append(f"Раздел ~W должен содержать параметр: {param}")
        
        # Validate depth units if present
        if 'STRT' in well_info:
            unit = well_info['STRT'].get('unit', '').upper()
            if unit and unit not in ['M', 'F', 'FT', 'FEET']:
                self.warnings.append(f"Единицы измерения глубины должны быть M (метры) или F/FT (футы), найдено: {unit}")
        
        self.info['well_info'] = well_info
    
    def _check_curve_section(self):
        """Check ~C (CURVE INFORMATION) section."""
        curve_section = self._extract_section('~C')
        curve_info = {}
        
        if not curve_section:
            self.errors.append("Раздел ~C (CURVE INFORMATION SECTION) является обязательным")
            return
        
        curves_order = []
        
        # Parse curve parameters
        for line_num, line in curve_section:
            if line.strip() and not line.strip().startswith('#'):
                parsed = self._parse_parameter_line(line)
                if parsed:
                    mnemonic, unit, value, description = parsed
                    curve_info[mnemonic] = {
                        'unit': unit,
                        'value': value,
                        'description': description,
                        'line': line_num
                    }
                    curves_order.append(mnemonic)
        
        if not curves_order:
            self.errors.append("Раздел ~C не содержит определений кривых")
            return
        
        # Check index curve (first curve)
        index_curve = curves_order[0]
        valid_index_mnemonics = ['DEPT', 'DEPTH', 'TIME', 'INDEX']
        
        if index_curve.upper() not in valid_index_mnemonics:
            self.errors.append(f"Индексная кривая должна иметь мнемонику DEPT, DEPTH, TIME или INDEX. Найдено: {index_curve}")
        
        # Check index curve units
        if index_curve in curve_info:
            unit = curve_info[index_curve].get('unit', '').upper()
            if index_curve.upper() in ['DEPT', 'DEPTH'] and unit not in ['M', 'F', 'FT', 'FEET']:
                self.warnings.append(f"Для индекса глубины единицы измерения должны быть M или F/FT, найдено: {unit}")
        
        self.info['curve_info'] = curve_info
        self.info['curves_order'] = curves_order
        self.info['num_curves'] = len(curves_order)
    
    def _check_data_section(self):
        """Check ~A (ASCII LOG DATA) section."""
        data_section = self._extract_section('~A')
        
        if not data_section:
            self.errors.append("Раздел ~A (ASCII LOG DATA) является обязательным")
            return
        
        data_lines = []
        for line_num, line in data_section:
            if line.strip() and not line.strip().startswith('#'):
                data_lines.append((line_num, line.strip()))
        
        if not data_lines:
            self.errors.append("Раздел ~A не содержит данных")
            return
        
        # Check data consistency
        expected_columns = self.info.get('num_curves', 0)
        inconsistent_lines = []
        
        for line_num, line_data in data_lines[:20]:  # Check first 20 lines
            values = line_data.split()
            if len(values) != expected_columns:
                inconsistent_lines.append((line_num, len(values), expected_columns))
        
        if inconsistent_lines:
            for line_num, found, expected in inconsistent_lines[:5]:  # Show first 5
                self.warnings.append(f"Строка {line_num}: ожидается {expected} колонок, найдено {found}")
        
        # Check for numeric data
        if data_lines:
            first_line_values = data_lines[0][1].split()
            numeric_columns = 0
            for value in first_line_values:
                try:
                    float(value.replace(',', '.'))  # Handle comma as decimal separator
                    numeric_columns += 1
                except ValueError:
                    pass
            
            self.info['numeric_columns'] = numeric_columns
        
        self.info['data_lines_count'] = len(data_lines)
    
    def _extract_section(self, section_name):
        """Extract lines from a specific section."""
        section_lines = []
        in_section = False
        
        for i, line in enumerate(self.lines):
            line_stripped = line.strip().upper()
            
            if line_stripped.startswith(section_name.upper()):
                in_section = True
                continue
            elif line_stripped.startswith('~') and in_section:
                break
            elif in_section:
                section_lines.append((i + 1, line))
        
        return section_lines
    
    def _parse_parameter_line(self, line):
        """Parse a parameter line: MNEM.UNIT VALUE : DESCRIPTION"""
        # Try different patterns
        patterns = [
            r'^([^.]+)\.([^:]*?)\s+([^:]+?)\s*:\s*(.*?)$',  # MNEM.UNIT VALUE : DESC
            r'^([^.]+)\.([^:]*?)\s*:\s*(.*?)$',             # MNEM.UNIT : DESC
            r'^([^:]+?)\s+([^:]+?)\s*:\s*(.*?)$',           # MNEM VALUE : DESC
            r'^([^:]+?)\s*:\s*(.*?)$'                       # MNEM : DESC
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line.strip())
            if match:
                groups = match.groups()
                if len(groups) == 4:
                    mnemonic, unit, value, description = groups
                    return mnemonic.strip(), unit.strip(), value.strip(), description.strip()
                elif len(groups) == 3:
                    if ':' in line and line.count(':') == 1:  # MNEM.UNIT : DESC
                        mnemonic_unit, description = line.split(':', 1)
                        if '.' in mnemonic_unit:
                            mnemonic, unit = mnemonic_unit.split('.', 1)
                            return mnemonic.strip(), unit.strip(), '', description.strip()
                        else:  # MNEM VALUE : DESC
                            mnemonic, value, description = groups
                            return mnemonic.strip(), '', value.strip(), description.strip()
                elif len(groups) == 2:
                    mnemonic, description = groups
                    return mnemonic.strip(), '', '', description.strip()
        
        return None
    
    def _generate_summary(self):
        """Generate validation summary."""
        self.info['validation_summary'] = {
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'is_valid': len(self.errors) == 0,
            'validation_time': datetime.now().isoformat()
        }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/lascheck', methods=['GET', 'POST'])
def lascheck():
    """Route for LAS file checking with web interface."""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if file was actually selected
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        # Check if file is allowed
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(filepath)
                
                # Check the LAS file
                checker = LASFileChecker(filepath)
                result = checker.check_file()
                
                # Add original filename to result
                result['original_filename'] = file.filename
                
                # Clean up uploaded file
                os.remove(filepath)
                
                return render_template('lascheck_result.html', 
                                     filename=file.filename, 
                                     result=result)
                
            except Exception as e:
                flash(f'Ошибка при обработке файла: {str(e)}', 'error')
                # Clean up file if it exists
                if os.path.exists(filepath):
                    os.remove(filepath)
                return redirect(request.url)
        else:
            flash('Неверный тип файла. Загрузите файл с расширением .las', 'error')
            return redirect(request.url)
    
    return render_template('lascheck.html')

@app.route('/api/lascheck', methods=['POST'])
def api_lascheck():
    """API endpoint for LAS file checking."""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не предоставлен'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Неверный тип файла. Разрешены только файлы .las'}), 400
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        # Check the LAS file
        checker = LASFileChecker(filepath)
        result = checker.check_file()
        
        # Add original filename to result
        result['original_filename'] = file.filename
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        # Clean up file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(debug=True)