# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

#ARG PYTHON_VERSION=3.12.3
#FROM python:${PYTHON_VERSION}-slim as base
#FROM public.ecr.aws/ubuntu/ubuntu:24.04_stable
#FROM ubuntu:25.04
#FROM public.ecr.aws/lambda/python:3.12

FROM public.ecr.aws/lambda/python:3.7.2024.03.24.02

USER root

# ------------------------------------------------------
RUN yum install -y wget which nscd
# ------------------------------------------------------

ENV LAMBDA_TASK_ROOT="/var/task"
WORKDIR ${LAMBDA_TASK_ROOT}


#RUN mkdir -p ${LAMBDA_TASK_ROOT}
COPY handler.py ${LAMBDA_TASK_ROOT}}
COPY requirements.txt ${LAMBDA_TASK_ROOT}
COPY yt-dlp_linux ${LAMBDA_TASK_ROOT}
COPY ffmpeg ${LAMBDA_TASK_ROOT}
COPY test.mp3 ${LAMBDA_TASK_ROOT}

#COPY libz.so.1 /lib/libz.so.1
COPY libz.so.1 /opt/lib/libz.so.1
ENV LD_LIBRARY_PATH="/opt/lib:${LD_LIBRARY_PATH}"
#ENV LD_PRELOAD="/lib/libz.so.1"

COPY msd-musicnn-1.json ${LAMBDA_TASK_ROOT}}
COPY msd-musicnn-1.pb ${LAMBDA_TASK_ROOT}

RUN chmod -R 777 ${LAMBDA_TASK_ROOT}/yt-dlp_linux
RUN chmod -R 777 ${LAMBDA_TASK_ROOT}/ffmpeg
RUN chmod -R 777 /tmp

RUN pip install --upgrade pip
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install awslambdaric

ADD . .

EXPOSE 8080

CMD [ "handler.lambda_handler" ]