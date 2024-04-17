#!/bin/bash
clear

# Informando sobre o que será removido
echo "Pronto para desinstalar o CheckUser da SpeedNET?"
read -p "Tecle enter para continuar ou CTRL + C para cancelar:"

echo "OK, iniciando processo de desinstalação..."
sleep 2  # Correção do comando sleep

clear
rm -rf /etc/speednet && rm -f /etc/systemd/system/checkuser-api.service &&
systemctl stop checkuser-api.service &&
systemctl disable checkuser-api.service &&
systemctl daemon-reload &&

clear

echo "#*************************************************#"
echo "# Checkuser by SpeedNET Desinstalado com Sucesso! #"
echo "#*************************************************#"
rm desinstalar.sh
