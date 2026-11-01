#!/usr/bin/env python3
import time
import json
import subprocess
import urllib.request
import urllib.error

API_URL = "http://localhost:5000"

def enviar_requisicao(rota, metodo="GET", dados=None):
    """Envia requisições HTTP para a API local sem travar em erros 4xx/5xx."""
    corpo = json.dumps(dados).encode("utf-8") if dados else None
    headers = {"Content-Type": "application/json"} if dados else {}
    req = urllib.request.Request(f"{API_URL}{rota}", data=corpo, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None

def cenario_vendas():
    print("\n[+] Disparando 15 compras normais no checkout...")
    for i in range(15):
        enviar_requisicao("/checkout", metodo="POST")
        time.sleep(0.1)
    
    print("\n" + "="*60)
    print("✅ AÇÃO EXECUTADA COM SUCESSO!")
    print("👉 MUDAR PARA O NAVEGADOR: http://localhost:9090/graph")
    print("💡 O QUE MOSTRAR:")
    print("   Consulte: sum(rate(http_requests_total[1m])) by (endpoint)")
    print("   Veja o tráfego regular e o contador de vendas subindo.")
    print("="*60)

def cenario_erros_checkout():
    print("\n[+] Ativando falha de Gateway de Pagamento na API...")
    enviar_requisicao("/admin/caos", metodo="POST", dados={"falha_gateway": True})
    
    print("[+] Enviando requisições com falha (HTTP 504)...")
    for i in range(8):
        enviar_requisicao("/checkout", metodo="POST")
        time.sleep(0.2)
    
    print("\n" + "="*60)
    print("✅ FALHA INJETADA COM SUCESSO!")
    print("👉 MUDAR PARA O NAVEGADOR: http://localhost:9090/alerts")
    print("💡 O QUE MOSTRAR:")
    print("   Veja o alerta 'Falha-Gateway-Pagamento' passar de PENDING para FIRING.")
    print("="*60)

def cenario_queda_total():
    print("\n[+] Parando o contêiner da aplicação (docker compose stop app)...")
    subprocess.run(["docker", "compose", "stop", "app"], check=False)
    
    print("\n" + "="*60)
    print("✅ CONTÊINER PARADO COM SUCESSO!")
    print("👉 MUDAR PARA O NAVEGADOR:")
    print("   1. http://localhost:9090/targets -> Mostre o alvo 'aplicacao-monitorada' DOWN")
    print("   2. http://localhost:9093         -> Mostre o incidente chegando no Alertmanager")
    print("="*60)

def restaurar_ambiente():
    print("\n[+] Religando o contêiner 'app'...")
    subprocess.run(["docker", "compose", "start", "app"], check=False)
    
    print("[+] Aguardando a API responder para limpar o modo de falha...")
    for _ in range(8):
        time.sleep(1)
        if enviar_requisicao("/") == 200:
            enviar_requisicao("/admin/caos", metodo="POST", dados={"falha_gateway": False, "latencia_checkout_seg": 0.0})
            break

    print("\n" + "="*60)
    print("✅ AMBIENTE 100% RESTAURADO!")
    print("👉 MUDAR PARA O NAVEGADOR:")
    print("   Veja os alvos voltarem para UP (verde) e os alertas serem resolvidos.")
    print("="*60)

def menu():
    while True:
        print("\n" + "="*50)
        print("  PAINEL DE TESTES DO SEMINÁRIO (NETSHOP)")
        print("="*50)
        print(" [1] Gerar Vendas Normais (Tráfego Saudável)")
        print(" [2] Simular Pico de Erros 5xx no Checkout (Alerta L7)")
        print(" [3] Derrubar a Aplicação (Target DOWN / Alertmanager)")
        print(" [4] Restaurar Ambiente (Tudo Verde)")
        print(" [0] Sair")
        print("="*50)
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            cenario_vendas()
        elif opcao == "2":
            cenario_erros_checkout()
        elif opcao == "3":
            cenario_queda_total()
        elif opcao == "4":
            restaurar_ambiente()
        elif opcao == "0":
            print("Saindo do painel.")
            break
        else:
            print("Opção inválida.")
        
        input("\n[Pressione ENTER para voltar ao menu quando terminar de mostrar no navegador...]")

if __name__ == "__main__":
    menu()