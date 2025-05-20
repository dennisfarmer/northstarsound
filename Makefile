run_streamlit:
	streamlit run streamlit_app.py
	
# there's probably a better way than
# separating the ngrok and flask commands
# but flask_ngrok.run_with_ngrok wasn't 
# working

# requires paid plan:
#ngrok http 5000 --url https://northstarsound.ngrok.app
run_audio_api:
	.venv/bin/python audio_api.py &
	#ngrok http 5000

stop_audio_api:
	kill -3 $(pgrep -f "python audio_api.py")
	ngrok http 5000

#curl -X POST -H "video_id: _r-nPqWGG6c" https://6671-35-1-109-213.ngrok-free.app -o output.mp3
test_api:
	curl -X POST $(endpoint)?video_id=_r-nPqWGG6c -o output.mp3

setup_ngrok:
	brew install ngrok
	source .env
	ngrok config add-authtoken $NGROK_AUTHTOKEN



generate_streamlit_env:
	sed 's/=/ = /g' .env > .streamlit_env