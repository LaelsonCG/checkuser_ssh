#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Versão otimizada do SSH Connection Limiter
Detecta e desconecta usuários SSH quando excedem o limite
"""

from flask import Flask, jsonify, Response, request
import subprocess
import datetime
import json
import time
import threading
import os
import signal
import re
from pathlib import Path
from collections import defaultdict

app = Flask(__name__)

class SSHLimiterOptimized:
    """Classe otimizada para gerenciar limites de conexão SSH"""
    
    def __init__(self, config_path='/root/usuarios.db', cache_duration=30):
        self.config_path = config_path
        self.cache_duration = cache_duration
        self.cache_usuarios_limites = {}
        self.cache_timestamp = 0
        self.conexoes_memorizado = {}
    
    def obter_usuarios_limites(self):
        """Obter limites com cache"""
        tempo_atual = time.time()
        
        if tempo_atual - self.cache_timestamp < self.cache_duration:
            return self.cache_usuarios_limites
        
        usuarios_limites = {}
        try:
            with open(self.config_path, 'r') as f:
                conteudo = f.read()
                if not conteudo.strip():
                    print(f"⚠️  AVISO: Arquivo {self.config_path} está VAZIO!")
                    print(f"   Crie o arquivo com: echo 'root 5' > {self.config_path}")
                
                for linha in conteudo.split('\n'):
                    linha = linha.strip()
                    if not linha or linha.startswith('#'):
                        continue
                    partes = linha.split()
                    if len(partes) >= 2:
                        try:
                            usuarios_limites[partes[0]] = int(partes[1])
                        except ValueError:
                            print(f"⚠️  Linha inválida ignorada: {linha}")
                            continue
            
            if not usuarios_limites:
                print(f"⚠️  NENHUM limite configurado em {self.config_path}")
                
        except FileNotFoundError:
            print(f"❌ ERRO: Arquivo {self.config_path} NÃO ENCONTRADO!")
            print(f"   Crie o arquivo com:")
            print(f"   cat > {self.config_path} << 'EOF'")
            print(f"   root 5")
            print(f"   usuario1 2")
            print(f"   EOF")
        except PermissionError:
            print(f"❌ ERRO: Sem permissão para ler {self.config_path}")
            print(f"   Execute com: sudo python3 app-otimizado.py")
        except Exception as e:
            print(f"❌ ERRO ao ler {self.config_path}: {e}")
        
        self.cache_usuarios_limites = usuarios_limites
        self.cache_timestamp = tempo_atual
        return usuarios_limites
    
    def obter_conexoes_ssh_rapido(self):
        """Obter conexões SSH reais via leitura de /proc"""
        conexoes = defaultdict(int)
        
        try:
            for sessao in self._listar_sessoes_ssh_processo():
                conexoes[sessao["usuario"]] += 1
        
        except Exception as e:
            print(f"Erro ao obter conexões SSH: {e}")
        
        return dict(conexoes)

    def _ler_cmdline_processo(self, pid):
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                return f.read().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            return ""

    def _uid_real_processo(self, pid):
        try:
            with open(f"/proc/{pid}/status", "r", encoding="utf-8", errors="replace") as f:
                for linha in f:
                    if linha.startswith("Uid:"):
                        partes = linha.split()
                        if len(partes) >= 2:
                            return int(partes[1])
                        break
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            return None
        return None

    def _inicio_processo(self, pid):
        try:
            with open(f"/proc/{pid}/stat", "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()
            fim_comm = conteudo.rfind(")")
            if fim_comm == -1:
                return None
            campos = conteudo[fim_comm + 2:].split()
            if len(campos) < 20:
                return None
            return int(campos[19])
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            return None

    def _extrair_usuario_sshd(self, cmdline):
        match = re.match(r"^sshd:\s+([^\s@]+)(?:@|\s|$)", cmdline)
        if not match:
            return None
        usuario = match.group(1)
        if "[priv]" in cmdline:
            return None
        return usuario

    def _listar_sessoes_ssh_processo(self):
        """Listar sessões sshd reais do sistema, excluindo processos [priv] e auxiliares."""
        sessoes = []
        uids_usuario = {}
        try:
            for entrada in os.scandir("/proc"):
                if not entrada.name.isdigit():
                    continue

                pid = int(entrada.name)
                cmdline = self._ler_cmdline_processo(pid)
                if not cmdline.startswith("sshd: "):
                    continue

                usuario = self._extrair_usuario_sshd(cmdline)
                if not usuario:
                    continue

                uid_processo = self._uid_real_processo(pid)
                if usuario not in uids_usuario:
                    uids_usuario[usuario] = self._uid_do_usuario(usuario)
                uid_usuario = uids_usuario[usuario]
                if uid_processo is None or uid_usuario is None or uid_processo != uid_usuario:
                    continue

                inicio = self._inicio_processo(pid)
                if inicio is None:
                    continue

                sessoes.append({
                    "pid": pid,
                    "usuario": usuario,
                    "inicio": inicio,
                    "cmdline": cmdline,
                })
        except FileNotFoundError:
            pass

        return sessoes

    def _uid_do_usuario(self, usuario):
        try:
            import pwd
            return pwd.getpwnam(usuario).pw_uid
        except KeyError:
            return None
    
    def _uid_para_usuario(self, uid):
        """Converter UID para nome de usuário (com cache)"""
        try:
            import pwd
            return pwd.getpwuid(uid).pw_name
        except KeyError:
            return None
    
    def desconectar_sessoes_excedentes(self, usuario, conexoes, limite):
        """Desconectar apenas as sessões excedentes, priorizando as mais recentes"""
        conexoes_excedentes = conexoes - limite
        
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠️  "
              f"Usuário '{usuario}': {conexoes} conexões, limite: {limite}. "
              f"Desconectando {conexoes_excedentes} sessões...")
        
        try:
            sessoes = self._listar_sessoes_ssh_processo()
            sessoes_usuario = [sessao for sessao in sessoes if sessao["usuario"] == usuario]
            sessoes_usuario.sort(key=lambda item: item["inicio"], reverse=True)
            pids = [sessao["pid"] for sessao in sessoes_usuario[:conexoes_excedentes]]
            
            if not pids:
                print(f"  ℹ Nenhuma sessão SSH elegível encontrada para '{usuario}'")
                return
            
            # Desconectar cada PID individualmente
            for idx, pid_str in enumerate(pids, 1):
                try:
                    pid = int(pid_str)
                    # Usar SIGTERM (gracioso) nas sessões mais recentes primeiro
                    os.kill(pid, signal.SIGTERM)
                    print(f"  ✓ Desconectando sessão {idx}/{conexoes_excedentes}: PID {pid}")
                    time.sleep(0.2)
                
                except (ValueError, ProcessLookupError):
                    print(f"  ⚠ PID {pid_str} não encontrado")
                except PermissionError:
                    # Se não temos permissão para SIGTERM, tentar SIGKILL
                    try:
                        os.kill(int(pid_str), signal.SIGKILL)
                        print(f"  ✓ SIGKILL enviado ao PID {pid_str}")
                    except:
                        pass
        except Exception as e:
            print(f"  ❌ Erro ao desconectar {usuario}: {e}")


limiter = SSHLimiterOptimized(config_path='/root/usuarios.db')


def verificar_limites_otimizado():
    """Thread para verificar e enforçar limites de conexão"""
    while True:
        try:
            usuarios_limites = limiter.obter_usuarios_limites()
            
            if not usuarios_limites:
                time.sleep(1)
                continue
            
            conexoes_por_usuario = limiter.obter_conexoes_ssh_rapido()
            
            # Mostrar apenas usuários que excedem o limite
            excedentes = []
            for u, c in conexoes_por_usuario.items():
                limite = usuarios_limites.get(u)
                if limite and c > limite:
                    excedentes.append((u, c, limite))
            
            if excedentes:
                print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠️  {len(excedentes)} usuário(s) excedendo limite:")
                for u, c, lim in excedentes:
                    print(f"  🔴 {u}: {c}/{lim} conexões")
            
            # Verificar limites
            for usuario, conexoes in conexoes_por_usuario.items():
                limite = usuarios_limites.get(usuario)
                
                if limite is not None:
                    # Garantir que limite é int
                    try:
                        limite = int(limite)
                    except (ValueError, TypeError):
                        continue
                    
                    if conexoes > limite:
                        limiter.desconectar_sessoes_excedentes(usuario, conexoes, limite)
            
            time.sleep(1)
        
        except Exception as e:
            print(f"❌ Erro na verificação de limites: {e}")
            time.sleep(1)

# Iniciar thread de verificação
thread = threading.Thread(target=verificar_limites_otimizado, daemon=True)
thread.start()


# ============ ROTAS DA API ============

@app.route('/check', methods=['GET'])
def listar_usuarios():
    """Listar todos os usuários do sistema"""
    usuarios = []
    try:
        with open('/etc/passwd', 'r') as f:
            for linha in f:
                dados = linha.strip().split(':')
                usuarios.append({'username': dados[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify(usuarios)


@app.route('/check/<username>', methods=['GET'])
def buscar_usuario(username):
    """Buscar informações específicas de um usuário"""
    try:
        # Contar conexões
        conexoes_por_usuario = limiter.obter_conexoes_ssh_rapido()
        count_connections = conexoes_por_usuario.get(username, 0)
        
        # Obter limite
        usuarios_limites = limiter.obter_usuarios_limites()
        limit_connections = usuarios_limites.get(username)
        
        # Obter data de expiração
        expiration_date = _obter_expiration_date(username)
        
        dados_usuario = {
            "username": username,
            "count_connections": count_connections,
            "limit_connections": limit_connections,
            "expiration_date": expiration_date,
            "expiration_days": _calcular_dias_restantes(expiration_date) if expiration_date else None,
            "time_online": _obter_tempo_conectado(username)
        }
        
        return Response(json.dumps(dados_usuario), mimetype='application/json')
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/checkUser', methods=['POST'])
def verificar_usuario():
    """Endpoint para verificação via POST"""
    try:
        data = request.get_json()
        if not data or 'user' not in data:
            return jsonify({"error": "Dados de usuário ausentes"}), 400
        
        username = data['user']
        
        conexoes_por_usuario = limiter.obter_conexoes_ssh_rapido()
        usuarios_limites = limiter.obter_usuarios_limites()
        
        return jsonify({
            "username": username,
            "count_connection": conexoes_por_usuario.get(username, 0),
            "limiter_user": usuarios_limites.get(username),
            "expiration_date": _obter_expiration_date(username),
            "expiration_days": _calcular_dias_restantes(_obter_expiration_date(username)),
            "time_online": _obter_tempo_conectado(username)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ FUNÇÕES AUXILIARES ============

def _obter_expiration_date(username):
    """Obter data de expiração da conta"""
    try:
        resultado = subprocess.run(f"chage -l {username}", shell=True, 
                                 capture_output=True, text=True, timeout=5)
        for linha in resultado.stdout.split('\n'):
            if 'Account expires' in linha:
                data_str = linha.split(':')[1].strip()
                return data_str
        return None
    except:
        return None


def _calcular_dias_restantes(expiration_date):
    """Calcular dias até expiração"""
    if not expiration_date:
        return None
    try:
        date_obj = datetime.datetime.strptime(expiration_date.strip(), "%b %d, %Y").date()
        delta = (date_obj - datetime.date.today()).days
        return max(0, delta)
    except:
        return None


def _obter_tempo_conectado(username):
    """Obter tempo de conexão do usuário"""
    try:
        resultado = subprocess.run(f"ps -u {username} -o etime --sort=etime | tail -n 1",
                                 shell=True, capture_output=True, text=True, timeout=5)
        tempo = resultado.stdout.strip()
        return tempo if tempo and tempo != "ELAPSED" else None
    except:
        return None


if __name__ == '__main__':
    print("🚀 SSH Connection Limiter iniciado...")
    print("📊 Cache duration: 30s")
    print("⏱️  Verificação: a cada 3s")
    app.run(debug=True, host='0.0.0.0', port=7000)
