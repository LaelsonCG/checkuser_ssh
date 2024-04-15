apt update && apt upgrade -y && mkdir /etc/speednet && mkdir /etc/speednet/checkuser
apt install -y python3 python3-pip &&
pip3 install Flask &&
cd /etc/speednet/checkuser &&
wget -y && wget https://raw.githubusercontent.com/LaelsonCG/checkuser_ssh/main/app.py &&
