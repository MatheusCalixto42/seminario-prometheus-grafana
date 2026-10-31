import time
from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# ==============================================================================
# 1. DEFINIÇÃO DAS MÉTRICAS
# ==============================================================================

# Counter: Métrica que só incrementa. Usaremos para contar o volume de tráfego
# e contabilizar os códigos de status (200, 500, etc.) por rota.
REQUEST_COUNT = Counter(
	'http_requests_total',
	'Total de requisições HTTP recebidas pela API',
	['method', 'endpoint', 'status']
)

# Histogram: Registra durações em segundos para calcularmos latência e percentis.
REQUEST_LATENCY = Histogram(
	'http_request_duration_seconds',
	'Tempo de resposta das requisições HTTP em segundos',
	['method', 'endpoint'],
)


# ==============================================================================
# 2. INSTRUMENTAÇÃO DO CICLO DE VIDA (HOOKS)
# ==============================================================================

@app.before_request
def start_timer():
	# Guarda o tempo exato em que a requisição chegou ao servidor
	request.start_time = time.time()

@app.after_request
def record_metrics(responde):
	# IMPORTANTE: Ignoramos '/metrics' para que a própria raspagem do Prometheus
	# não suje as métricas de tráfego real da aplicação
	if request.path != '/metrics':
		latency = time.time() - request.start_time
		REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(latency)
        REQUEST_COUNT.labels(
            	method=request.method,
            	endpoint=request.path,
            	status=response.status_code
        ).inc()
    return response

# ==============================================================================
# 3. ROTAS DA APLICAÇÃO
# ==============================================================================

@app.route('/')
def home():
    """Rota saudável para simular tráfego normal (HTTP 200)."""
    return jsonify({
        "message": "API de pé e operante!",
        "status": "healthy"
    }), 200

@app.route('/erro')
def simulate_error():
    """
    Rota de falha proposital para simular erros HTTP 500.
    Será usada mais adiante para testar nossos alertas de picos de erro.
    """
    return jsonify({
        "error": "Falha interna simulada no servidor!",
        "status": "error"
    }), 500

@app.route('/metrics')
def metrics():
    """
    Endpoint de Telemetria.
    O Prometheus fará o scraping aqui. Retorna o texto formatado das métricas.
    """
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
	
if __name__ == '__main__':
    # 0.0.0.0 é fundamental para escutar em todas as interfaces de rede do container
    app.run(host='0.0.0.0', port=5000)