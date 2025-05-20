from flask import Flask, request, send_file
from flask_ngrok import run_with_ngrok
from src.youtube import download_audio

app = Flask(__name__)
#run_with_ngrok(app)  # Start ngrok when app is run

@app.route("/", methods=["POST"])
def send_yt_audio():
    if request.method == "POST":
        video_id = request.args.get("video_id")
        if not video_id:
            return "No video ID provided", 400
        output_path = download_audio(video_id)
        return send_file(output_path)  #io.BytesIO


if __name__ == "__main__":
    app.run(port=5000)