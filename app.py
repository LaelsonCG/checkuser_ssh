# Projeto checkuser e Limitador SSH criado por @Laael
# Seja ético, se utilizar este projeto, cite a fonte.
# OpenSource, liberado para uso não comercial ok?

from flask import Flask, jsonify, Response
import subprocess
import datetime
import json
import time
import threading

app = Flask(__name__)

# Função para obter todos os usuários do sistema
def obter_usuarios():
    usuarios = []
    with open('/etc/passwd', 'r') as arquivo_passwd:
        linhas = arquivo_passwd.readlines()
        for linha in linhas:
            dados = linha.strip().split(':')
            usuario = {
                'username': dados[0],
                #'uuid': '',  # Depois tentarei fazer
            }
            usuarios.append(usuario)
    return usuarios

# Função para obter o limite de conexões
def obter_limite_conexoes(username):
    try:
        with open('/root/usuarios.db', 'r') as arquivo:
            linhas = arquivo.readlines()
            for linha in linhas:
                partes = linha.strip().split()
                if len(partes) == 2 and partes[0] == username:
                    return int(partes[1])
            return None  # Limite não encontrado para o usuário
    except FileNotFoundError:
        return None  # Arquivo de dados não encontrado

# Função para obter a data de vencimento da conta do usuário
def obter_expiration_date(username):
    try:
        # Obter a data de vencimento da conta usando o comando chage
        comando = f"chage -l {username}"
        resultado = subprocess.check_output(comando, shell=True).decode()
        linhas = resultado.strip().split('\n')
        for linha in linhas:
            if linha.startswith("Account expires"):
                partes = linha.split(":")
                expiration_date_str = partes[1].strip()
                expiration_date = datetime.datetime.strptime(expiration_date_str, "%b %d, %Y").date()
                return expiration_date.strftime("%d/%m/%Y")
        return None  # Data de vencimento não encontrada
    except subprocess.CalledProcessError:
        return None  # Usuário não encontrado ou comando chage falhou

# Função para calcular os dias restantes a partir da data de vencimento
def calcular_dias_restantes(expiration_date):
    data_atual = datetime.date.today()
    delta = expiration_date - data_atual
    return delta.days if delta.days >= 0 else 0

# Função para contar as conexões ativas
def contar_conexoes_ativas(username):
    try:
        comando_ssh = "ps -ef | grep -oP 'sshd: \\K\\w+(?= \\[priv\\])'"
        usuarios_ssh = subprocess.check_output(comando_ssh, shell=True).decode().strip().split('\n')
        usuario_especifico = f'{username}'
        # Conta o número de conexões para o usuário específico
        conexoes_usuario_especifico = usuarios_ssh.count(usuario_especifico)
        return conexoes_usuario_especifico  # Retorna o número de conexões
    except subprocess.CalledProcessError:
        return 0  # Usuário não possui conexões ativas

# Obter tempo de conexão
def obter_tempo_conectado(username):
    try:
        # Comando para listar os processos do usuário e capturar o tempo de execução mais longo
        comando_ps = f"ps -u {username} -o etime --sort=etime | tail -n 1"
        tempo_em_execucao = subprocess.check_output(comando_ps, shell=True).decode().strip()
        if tempo_em_execucao == "ELAPSED":
            return None  # Tempo de execução não disponível
        else:
            return tempo_em_execucao
    except subprocess.CalledProcessError:
        return None  # Usuário não está conectado

# Função para garantir o limite de conexões por usuário
def verificar_limites():
    while True:
        # Função para obter os usuários e seus limites permitidos
        def obter_usuarios_limites():
            usuarios_limites = {}
            try:
                with open('/root/usuarios.db', 'r') as arquivo:
                    for linha in arquivo:
                        partes = linha.strip().split()
                        if len(partes) >= 2:
                            usuario = partes[0]
                            limite = int(partes[1])
                            usuarios_limites[usuario] = limite
            except FileNotFoundError:
                pass  # Arquivo de configuração não encontrado
            return usuarios_limites

        usuarios_limites = obter_usuarios_limites()

        # Comando para obter os usuários conectados via SSH
        comando_ssh = "ps -ef | grep -oP 'sshd: \\K\\w+(?= \\[priv\\])'"

        # Executa o comando para obter os usuários conectados via SSH
        usuarios_ssh = subprocess.check_output(comando_ssh, shell=True).decode().strip().split('\n')

        # Dicionário para armazenar o número de conexões por usuário
        conexoes_por_usuario = {}

        # Conta o número de conexões para cada usuário
        for usuario in usuarios_ssh:
            conexoes_por_usuario[usuario] = conexoes_por_usuario.get(usuario, 0) + 1

        # Verifica se algum usuário ultrapassou o limite de conexões
        for usuario, conexoes in conexoes_por_usuario.items():
            limite_conexoes = usuarios_limites.get(usuario)
            if limite_conexoes is not None and conexoes > limite_conexoes:
                print(f"Desconectando usuário {usuario} por exceder o limite de conexões.")
                comando_desconectar = f"pkill -u {usuario}"
                subprocess.run(comando_desconectar, shell=True)

        time.sleep(3)  # Intervalo de verificação em segundos

# Thread para executar a função verificar_limites()
thread_limites = threading.Thread(target=verificar_limites)
thread_limites.daemon = True  # A thread será encerrada quando o programa principal terminar
thread_limites.start()  # Inicia a thread


# Rota para listar todos os usuários do sistema
@app.route('/check', methods=['GET'])
def listar_usuarios():
    usuarios = obter_usuarios()
    return jsonify(usuarios)

# Rota para retornar as informações de um usuário específico
@app.route('/check/<username>', methods=['GET'])
def buscar_usuario(username):
    usuarios = obter_usuarios()
    for usuario in usuarios:
        if usuario['username'] == username:
            expiration_date = obter_expiration_date(username)
            if expiration_date:
                # Crie um novo dicionário na ordem desejada
                new_usuario = {
                    "username": usuario["username"],
                    "count_connections": contar_conexoes_ativas(username),
                    "limit_connections": obter_limite_conexoes(username),
                    "expiration_date": expiration_date,
                    "expiration_days": calcular_dias_restantes(datetime.datetime.strptime(expiration_date, "%d/%m/%Y").date()),
                    "time_online": obter_tempo_conectado(username),
                    "uuid": None  # Adicione o valor correto aqui
                }
                return Response(json.dumps(new_usuario), mimetype='application/json')
            else:
                usuario['expiration_date'] = None
                usuario['expiration_days'] = None
                usuario['count_connections'] = 0
                return jsonify(usuario)
    return jsonify({"error": f"Usuário '{username}' não encontrado."}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7000)
