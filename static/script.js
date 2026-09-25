const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const dzFile = document.getElementById('dzFile');
const submitBtn = document.getElementById('submitBtn');
const form = document.getElementById('convertForm');
const progressBlock = document.getElementById('progressBlock');
const progressFill = document.getElementById('progressFill');
const progressMsg = document.getElementById('progressMsg');
const resultBlock = document.getElementById('resultBlock');
const previewVideo = document.getElementById('previewVideo');
const downloadLink = document.getElementById('downloadLink');
const errorMsg = document.getElementById('errorMsg');

let selectedGender = 'female';
let selectedSpeed = '1';

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('drag');
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    onFileChosen();
  }
});
fileInput.addEventListener('change', onFileChosen);

function onFileChosen() {
  if (fileInput.files.length) {
    dzFile.textContent = fileInput.files[0].name;
    submitBtn.disabled = false;
  }
}

document.querySelectorAll('.seg').forEach((seg) => {
  seg.addEventListener('click', (e) => {
    const btn = e.target.closest('.seg-btn');
    if (!btn) return;
    seg.querySelectorAll('.seg-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    const name = seg.dataset.name;
    if (name === 'gender') selectedGender = btn.dataset.value;
    if (name === 'speed') selectedSpeed = btn.dataset.value;
  });
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorMsg.hidden = true;
  resultBlock.hidden = true;
  submitBtn.disabled = true;

  const formData = new FormData();
  formData.append('pptx', fileInput.files[0]);
  formData.append('gender', selectedGender);
  formData.append('speed', selectedSpeed);

  progressBlock.hidden = false;
  progressFill.style.width = '2%';
  progressMsg.textContent = 'Uploading…';

  try {
    const res = await fetch('/convert', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Upload failed');
    pollStatus(data.job_id);
  } catch (err) {
    showError(err.message);
  }
});

function pollStatus(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/status/${jobId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Status check failed');

      progressFill.style.width = `${data.progress}%`;
      progressMsg.textContent = data.message;

      if (data.status === 'done') {
        clearInterval(interval);
        progressBlock.hidden = true;
        resultBlock.hidden = false;
        previewVideo.src = `/preview/${jobId}`;
        downloadLink.href = `/download/${jobId}`;
        submitBtn.disabled = false;
      } else if (data.status === 'error') {
        clearInterval(interval);
        showError(data.error || 'Conversion failed');
      }
    } catch (err) {
      clearInterval(interval);
      showError(err.message);
    }
  }, 2000);
}

function showError(msg) {
  progressBlock.hidden = true;
  errorMsg.hidden = false;
  errorMsg.textContent = msg;
  submitBtn.disabled = false;
}
