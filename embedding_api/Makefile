
build:
	docker build --platform linux/amd64 -t aws-embeddings:latest .

run: build
	docker run --platform linux/amd64 -p 8080:8080 aws-embeddings:latest

push_to_ecr:
	# unfortunately this doesn't work because Makefiles can't export environment variables
	# to the child process that called make push_to_ecr
	# hopefully no one will notice that I hardcoded the credentials here
	# please don't steal my ARN from my public github repo oh no ahhhh
	# export CREDIT_CARD_NUMBER="8224-5278-9017-3254"
	# export CREDIT_CARD_EXPIRATION_DATE="12/98"
	# export CREDIT_CARD_CVV="392"
	#export AWS_ACCESS_KEY_ID=""
	#export AWS_SECRET_ACCESS_KEY=""
	#export AWS_SESSION_TOKEN=""
	#json_string=$$(aws sts assume-role --role-arn arn:aws:iam::998955259098:role/ECRPushRole --role-session-name my-session)
	#@echo $$json_string
	##aws sts assume-role --role-arn arn:aws:iam::998955259098:role/ECRPushRole --role-session-name my-session
	##export AWS_ACCESS_KEY_ID=$$(echo "$$json_string" | jq -r '.Credentials.AccessKeyId')
	##export AWS_SECRET_ACCESS_KEY=$$(echo "$$json_string" | jq -r '.Credentials.SecretAccessKey')
	##export AWS_SESSION_TOKEN=$$(echo "$$json_string" | jq -r '.Credentials.SessionToken')
	##docker login -u AWS -p $(aws ecr get-login-password --region us-east-2) 998955259098.dkr.ecr.us-east-2.amazonaws.com
	##docker tag aws-embeddings:latest 998955259098.dkr.ecr.us-east-2.amazonaws.com/music-recommendation:embeddings
	##docker push 998955259098.dkr.ecr.us-east-2.amazonaws.com/music-recommendation:embeddings



default_test:
	curl -X POST "http://localhost:8080/2015-03-31/functions/function/invocations" -d '{"video_id": "test"}'

single_video_test:
	curl -X POST "http://localhost:8080/2015-03-31/functions/function/invocations" -d '{"video_id": "UZyTZVH-OO0"}'

multiple_videos_test:
	curl -X POST "http://localhost:8080/2015-03-31/functions/function/invocations" -d '{"video_ids": ["vEwu9Pm4zpE", "_r-nPqWGG6c"]}'

#wget https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
#tar -xf ffmpeg-master-latest-linux64-gpl.tar.xz
#rm ffmpeg-master-latest-linux64-gpl.tar.xz
#mv ffmpeg-*-linux64-gpl/bin/ffmpeg .
download_ffmpeg_binary:
	wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz
	mv ffmpeg-git-20240629-amd64-static/ffmpeg .
	rm -rf ffmpeg-git-20240629-amd64-static
	rm -rf ffmpeg-git-20240629-amd64-static.tar.xz
	chmod +x ffmpeg

download_ytdlp_binary:
	wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux
	chmod +x yt-dlp_linux

download_musicnn_model:
	wget -q https://essentia.upf.edu/models/autotagging/msd/msd-musicnn-1.pb
	wget -q https://essentia.upf.edu/models/autotagging/msd/msd-musicnn-1.json

download_RIE_amd64:
	# necessary for running the lambda function locally with a non-aws lambda image
	mkdir -p ~/.aws-lambda-rie && curl -Lo ~/.aws-lambda-rie/aws-lambda-rie \
		https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie \
		&& chmod +x ~/.aws-lambda-rie/aws-lambda-rie

download_RIE_arm64:
	# necessary for running the lambda function locally with a non-aws lambda image
	mkdir -p ~/.aws-lambda-rie && curl -Lo ~/.aws-lambda-rie/aws-lambda-rie \
		https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie-arm64 \
		&& chmod +x ~/.aws-lambda-rie/aws-lambda-rie

build_arm64:
	docker buildx build --platform linux/arm64 --provenance=false -t aws-embeddings .

run_arm64:
	# this works on a macbook with M3 chip (arm64 architecture)
	docker run --platform linux/arm64 -d -v ~/.aws-lambda-rie:/aws-lambda -p 9000:8080 aws-embeddings:latest \
		--entrypoint /aws-lambda/aws-lambda-rie /usr/local/bin/python -m #awslambdaric lambda_function.handler




# these one works for Dockerfiles that are based on the Docker Python3.7 image
# Amazon Linux doesn't work because we would need to install audio dependencies
# to compile tensorflow-essentia from source (when using python3.12/3.13/etc.) 
# and the al2023 package manager doesn't have them

# UPDATE: turns out there is a python3.7 aws lambda image so I'm just using that
# FROM public.ecr.aws/lambda/python:3.7.2024.03.24.02 <-- this is the base image

# https://docs.aws.amazon.com/linux/al2023/release-notes/all-packages-AL2023.7.html
# https://docs.aws.amazon.com/lambda/latest/dg/python-image.html#python-image-instructions

build_from_python_image:
	docker buildx build --platform linux/amd64 --provenance=false -t aws-embeddings .

run_from_python_image:
	docker run --platform linux/amd64 -d -v ~/.aws-lambda-rie:/aws-lambda -p 8080:8080 \
		--entrypoint /aws-lambda/aws-lambda-rie \
		aws-embeddings /usr/local/bin/python -m awslambdaric handler.lambda_handler
