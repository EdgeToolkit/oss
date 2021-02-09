FROM edgetoolkit/gcc5

LABEL maintainer="Mingyi Zhang <mingyi.z@outlook.com>"

COPY files/sources.list-ubuntu.18.04 /etc/apt/sources.list
COPY files/pip.conf /home/conan/.pip/pip.conf

RUN sudo apt-get update \
    && sudo apt install -y sshpass \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && pip config set install.trusted-host mirrors.aliyun.com \
    && pip install ansible docker networkx python-gitlab winrm

    

