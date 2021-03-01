FROM ubuntu:focal

LABEL maintainer="Mingyi Zhang <mingyi.z@outlook.com>"


COPY files/sources.list-ubuntu.20.04 /etc/apt/sources.list

RUN apt-get update \
    && apt install -y python3 python3-pip python-is-python3 \
       sshpass sudo \
    && python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && python -m pip config set install.trusted-host mirrors.aliyun.com \
    && python -m pip install ansible docker networkx python-gitlab winrm \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd 1001 -g 1001 \
    && groupadd 1000 -g 1000 \
    && groupadd 2000 -g 2000 \
    && groupadd 999 -g 999 \
    && useradd -ms /bin/bash ansible -g 1001 -G 1000,2000,999 \
    && printf "ansible:ansible" | chpasswd \
    && adduser ansible sudo \
    && printf "ansible ALL= NOPASSWD: ALL\\n" >> /etc/sudoers 

USER ansible
WORKDIR /home/ansible

COPY files/ansible.cfg /home/ansible/.ansible.cfg

    

