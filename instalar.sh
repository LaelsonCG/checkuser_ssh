#!/bin/bash

# Atualiza e instala as atualizações do sistema
apt update && apt upgrade -y

# Cria os diretórios necessários
mkdir -p /etc/speednet/checkuser

# Instala o Python 3 e o pip
apt install -y python3 python3-pip

# Instala o Flask via pip
pip3 install Flask

# Baixa o arquivo app.py da sua API
wget -O /etc/speednet/checkuser/app.py https://raw.githubusercontent.com/LaelsonCG/checkuser_ssh/main/app.py

# Baixa o arquivo de serviço .service para o systemd
wget -O /etc/systemd/system/checkuser-api.service https://raw.githubusercontent.com/LaelsonCG/checkuser_ssh/main/checkuser-api.service

# Recarrega o systemd para reconhecer o novo serviço
systemctl daemon-reload

# Habilita e inicia o serviço
systemctl enable checkuser-api.service
systemctl start checkuser-api.service

clear

# Exibe a mensagem de conclusão da instalação
echo "***********************************************"
echo "Parabéns! CheckUser Instalado com Sucesso."
echo "***********************************************"
echo ""
echo "Para instruções de uso e outras informações,"
echo "visite a documentação no link abaixo:"
echo "https://github.com/LaelsonCG/checkuser_ssh"
echo "***********************************************"
rm /root/instalar.sh
