import os
import uuid

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, jsonify, send_file, redirect, url_for
)
from werkzeug.utils import secure_filename

from converter import pipeline

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB upload cap


@app.route("/")
def root():
    return redirect(url_for("home"))


@app.route("/home")
def home():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    file = request.files.get("pptx")
    if not file or file.filename == "":
        return jsonify({"error": "No .pptx file was uploaded."}), 400
    if not file.filename.lower().endswith(".pptx"):
        return jsonify({"error": "Please upload a .pptx file."}), 400

    gender = request.form.get("gender", "female")
    if gender not in ("male", "female"):
        return jsonify({"error": "gender must be 'male' or 'female'."}), 400

    try:
        speed = float(request.form.get("speed", "1"))
    except ValueError:
        return jsonify({"error": "speed must be a number."}), 400
    if speed not in (1.0, 1.5, 2.0):
        return jsonify({"error": "speed must be 1, 1.5, or 2."}), 400

    filename = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    job_id = pipeline.start_job(save_path, gender, speed)
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    job = pipeline.get_job(job_id)
    if not job:
        return jsonify({"error": "Unknown job id"}), 404
    return jsonify({
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "error": job["error"],
        "ready": job["status"] == "done",
    })


@app.route("/preview/<job_id>")
def preview(job_id):
    job = pipeline.get_job(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Video not ready"}), 404
    return send_file(job["output_path"], mimetype="video/mp4")


@app.route("/download/<job_id>")
def download(job_id):
    job = pipeline.get_job(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Video not ready"}), 404
    return send_file(
        job["output_path"], mimetype="video/mp4",
        as_attachment=True, download_name=f"presentation_{job_id}.mp4",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8086))
    app.run(host="0.0.0.0", port=port, debug=False)
