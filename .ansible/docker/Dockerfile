FROM ubuntu:focal

LABEL maintainer="Mingyi Zhang <mingyi.z@outlook.com>"

COPY files/sources.list-ubuntu.20.04 /etc/apt/sources.list

RUN apt-get update \
    && apt install -y sshpass python3 python3-pip python-is-python3 \
    && python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && python -m pip config set install.trusted-host mirrors.aliyun.com \
    && python -m pip install ansible docker networkx python-gitlab winrm


    

