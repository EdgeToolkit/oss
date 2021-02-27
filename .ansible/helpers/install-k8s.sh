#
#
# Kubernetes installation, check https://developer.aliyun.com/mirror/kubernetes?spm=a2c6h.13651102.0.0.3e221b11TePNmi
#


install_kube_tool() {
  sudo apt-get update && apt-get install -y apt-transport-https
  curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | sudo apt-key add -
  sudo cp ./config/kubernetes.list /etc/apt/sources.list.d/kubernetes.list
  sudo apt-get update
  sudo apt-get install -y kubelet kubeadm kubectl

}

kube_init(){
  # ref https://blog.csdn.net/Finux1688/article/details/106164912/
  sudo kubeadm init --apiserver-advertise-address ${APISERVER_IP} --pod-network-cidr=172.20.0.0/16 
  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  # check for nodes status
  sudo kubectl get nodes
  
  #export KUBECONFIG=/etc/kubernetes/admin.conf
  #kubeadm join 192.168.56.110:6443 --token 87qu7r.fyi4rhio9tbhqxae \
  #  --discovery-token-ca-cert-hash sha256:606fe60e4665113b3fc5ccb773a2d158d7a7b67fa2e300ba1d588ed641858964
}
load_images(){
  images=$(kubeadm config images list | awk -F"/" '{print $2}')
  for i in ${images[@]} ; do
    sudo docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/$i
    sudo docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/$i k8s.gcr.io/$i
    sudo docker rmi registry.cn-hangzhou.aliyuncs.com/google_containers/$i
  done
}

install_cni_calico(){
wget https://docs.projectcalico.org/manifests/calico.yaml

}