import time
from flask import Flask, request, jsonify
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

@app.route('/test-upload', methods=['POST'])
def test_upload():
    """Test pure upload speed without processing"""
    start_time = time.time()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    
    # Just read the file without processing
    file_content = file.read()
    file_size = len(file_content)
    
    upload_time = time.time() - start_time
    
    return jsonify({
        'file_size_bytes': file_size,
        'file_size_mb': round(file_size / (1024*1024), 2),
        'upload_time_seconds': round(upload_time, 2),
        'speed_mbps': round((file_size / (1024*1024)) / upload_time, 2) if upload_time > 0 else 0
    })

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'gunicorn':
        # Run: python test_performance.py gunicorn
        import subprocess
        subprocess.run(['gunicorn', '-w', '4', '-b', '0.0.0.0:5001', 'test_performance:app'])
    else:
        app.run(host='0.0.0.0', port=5001, debug=False)