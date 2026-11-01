import time
import random
from flask import Flask, request, jsonify, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST
)

app = Flask(__name__)

# ==============================================================================
# ESTADO DE ENGENHARIA DO CAOS (Controlado remotamente pelo script do seminário)
# ==============================================================================
MODO_CAOS = {
    "latencia_checkout_seg": 0.0,  # Tempo extra injetado no pagamento (QoS/SLA)
    "falha_gateway": False         # Simula queda do provedor de pagamento (HTTP 504)
}

ROTAS_IGNORADAS = ('/metrics', '/admin/caos')

# ==============================================================================
# 1. DEFINIÇÃO DAS MÉTRICAS (Os 4 Sinais de Ouro: Tráfego, Erros, Latência, Saturação)
# ==============================================================================

# Tráfego e Erros HTTP (200, 401, 504, etc.)
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total de requisicoes HTTP recebidas pela NetShop',
    ['method', 'endpoint', 'status']
)

# Latência com buckets ajustados de 25ms até 5s para cálculo preciso de p95
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'Tempo de resposta das requisicoes HTTP em segundos',
    ['method', 'endpoint'],
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
)

# Saturação: Gauge sobe quando a requisição entra e desce quando termina
ACTIVE_REQUESTS = Gauge(
    'http_requests_in_progress',
    'Requisicoes HTTP sendo processadas simultaneamente'
)

# Métrica intuitiva de negócio/operação para enriquecer o Grafana
CHECKOUT_COUNT = Counter(
    'netshop_vendas_total',
    'Total de tentativas de compra no checkout',
    ['resultado']
)

# ==============================================================================
# 2. HOOKS DE INSTRUMENTAÇÃO
# ==============================================================================

@app.before_request
def start_timer():
    request.start_time = time.time()
    request.monitorar = request.path not in ROTAS_IGNORADAS
    if request.monitorar:
        ACTIVE_REQUESTS.inc()

@app.after_request
def record_metrics(response):
    if getattr(request, 'monitorar', False):
        latency = time.time() - request.start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(latency)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
    return response

@app.teardown_request
def end_request(exc=None):
    # Garante que o Gauge sempre decremente, mesmo se ocorrer exceção interna
    if getattr(request, 'monitorar', False):
        ACTIVE_REQUESTS.dec()

# ==============================================================================
# 3. ROTAS DO E-COMMERCE "NETSHOP"
# ==============================================================================

@app.route('/')
def home():
    """Healthcheck e visão geral da API."""
    return jsonify({
        "servico": "NetShop E-commerce API",
        "status": "online",
        "modo_caos_ativo": MODO_CAOS
    }), 200

@app.route('/produtos', methods=['GET'])
def listar_produtos():
    """Navegação rápida de catálogo (10ms a 40ms) - Simula tráfego normal."""
    time.sleep(random.uniform(0.01, 0.04))
    return jsonify({
        "produtos": [
            {"id": 1, "nome": "Roteador Gigabit Dual-Band", "preco": 350.0},
            {"id": 2, "nome": "Switch Gerenciavel 24 Portas", "preco": 1200.0},
            {"id": 3, "nome": "Appliance Firewall UTM", "preco": 2800.0}
        ]
    }), 200

@app.route('/login', methods=['POST'])
def login():
    """
    Autenticação de clientes.
    Usada para demonstrar segurança: rajadas de senha inválida geram flood de HTTP 401.
    """
    time.sleep(random.uniform(0.02, 0.05))
    dados = request.get_json(force=True, silent=True) or {}
    senha = dados.get("senha", "")

    if senha == "cliente123":
        return jsonify({"mensagem": "Login realizado com sucesso", "token": "jwt-simulado"}), 200

    return jsonify({"erro": "Credenciais invalidas"}), 401

@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Finalização de compra e comunicação com Gateway de Pagamento externo.
    Sensível à injeção de latência (QoS) e falhas de upstream (HTTP 504).
    """
    # Latência normal de processamento (100ms a 250ms) + latência de caos se ativa
    atraso_base = random.uniform(0.10, 0.25)
    time.sleep(atraso_base + MODO_CAOS["latencia_checkout_seg"])

    if MODO_CAOS["falha_gateway"]:
        CHECKOUT_COUNT.labels(resultado="falha_gateway").inc()
        return jsonify({
            "erro": "Gateway Timeout: Provedor de pagamento nao respondeu"
        }), 504

    CHECKOUT_COUNT.labels(resultado="aprovada").inc()
    return jsonify({
        "mensagem": "Pedido aprovado com sucesso!",
        "protocolo": random.randint(10000, 99999)
    }), 200

# ==============================================================================
# 4. CONTROLE DE CAOS & TELEMETRIA
# ==============================================================================

@app.route('/admin/caos', methods=['GET', 'POST'])
def gerenciar_caos():
    """Endpoint de controle para o script interativo injetar ou limpar anomalias."""
    if request.method == 'POST':
        dados = request.get_json(force=True, silent=True) or {}
        if "latencia_checkout_seg" in dados:
            MODO_CAOS["latencia_checkout_seg"] = float(dados["latencia_checkout_seg"])
        if "falha_gateway" in dados:
            MODO_CAOS["falha_gateway"] = bool(dados["falha_gateway"])
    return jsonify({"modo_caos": MODO_CAOS}), 200

@app.route('/metrics')
def metrics():
    """Exposição das métricas no padrão OpenMetrics para scraping do Prometheus."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)