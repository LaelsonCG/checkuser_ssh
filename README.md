# API Checkuser e Limitador de Conexões

Como o nome sugere, essa é uma api de checkuser para obter informações de usuarios e para garantir que o usuario não ultrapasse o numero de dispositivos conectados permitidos em seu login.

- Obter informações do usuario como limite de conexões permitidas;
- Obter numero de dispositivos conectados;
- Obter data de Vencimento;
- Calcular dias restantes;
- Desconecta automáticamente o usuario que exceder o limite permitido;

Em breve, mais recursos estarão disponíveis!

# Instalação:

```shell
wget https://raw.githubusercontent.com/LaelsonCG/checkuser_ssh/main/instalar.sh && chmod +x instalar.sh && ./instalar.sh```

Após ativar, você poderá usar a api em aplicativos baseados no conecta4g e dtunnel, utilizando a porta 7000, como nos exemplos abaixo:

## Dtunnel
```http://seu_dominio_ou_ip:7000```

## Conecta4G/5G
```http://seu_dominio_ou_ip:7000/checkUser```

