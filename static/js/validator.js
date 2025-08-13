const fileInput = document.getElementById('las-file');
const fileInfo = document.getElementById('file-info');
const fileNameElem = document.getElementById('file-name');
const fileSizeElem = document.getElementById('file-size');
const validateBtn = document.getElementById('validate-btn');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');
const resultsContainer = document.getElementById('results-container');
const validationSummary = document.getElementById('validation-summary');
const validationDetails = document.getElementById('validation-details');
const filePreview = document.getElementById('file-preview');

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file) {
    fileNameElem.textContent = file.name;
    fileSizeElem.textContent = `${(file.size / 1024).toFixed(1)} KB`;
    fileInfo.style.display = 'block';
    resultsContainer.style.display = 'none';

    const reader = new FileReader();
    reader.onload = function (e) {
      const text = e.target.result;
      filePreview.textContent = text
      // .split('\n').slice(0, 30).join('\n');
    };
    reader.readAsText(file, 'utf-8');
  }
});

validateBtn.addEventListener('click', () => {
  const file = fileInput.files[0];


  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  progressContainer.style.display = 'block';
  progressBar.style.width = '30%';

  fetch('/validate', {
    method: 'POST',
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      progressBar.style.width = '100%';
      setTimeout(() => {
        progressContainer.style.display = 'none';
        resultsContainer.style.display = 'block';
      }, 500);

      if (data.valid) {
        validationSummary.innerHTML = `
          <div class="alert alert-success">
            <i class="bi bi-check-circle me-2"></i>Файл прошёл проверку без ошибок.
          </div>`;
        validationDetails.innerHTML = '';
      } else {
        validationSummary.innerHTML = `
          <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>Обнаружены ошибки: ${data.errors.length}
          </div>`;
        const list = data.errors.map(err => `<li>${err}</li>`).join('');
        validationDetails.innerHTML = `<ul>${list}</ul>`;
      }
    })
    .catch(err => {
      progressContainer.style.display = 'none';
      alert("Ошибка при проверке файла. Проверьте подключение или формат.");
      console.error(err);
    });
});
