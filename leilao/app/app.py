from flask import Flask, jsonify, request, render_template, send_from_directory
from datetime import datetime
import redis
import os
import json

app = Flask(__name__)
redis_host = os.getenv("REDIS_HOST", "redis-service")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

@app.route('/create-auction', methods=['POST'])
def criar_leilao():
    dados = request.json
    campos_obrigatorios = ['titulo', 'descricao', 'preco_inicial', 'horario_termino']
    for campo in campos_obrigatorios:
        if campo not in dados or not dados[campo]:
            return jsonify({'ERROR': f'Campo {campo} é obrigatório'}), 400

    titulo = dados['titulo'].strip()
    descricao = dados['descricao'].strip()

    if not titulo:
        return jsonify({'ERROR': 'Título não pode ser vazio'}), 400

    if not descricao:
        return jsonify({'ERROR': 'Descrição não pode ser vazia'}), 400

    try:
        preco_inicial = float(dados['preco_inicial'])
        if preco_inicial <= 0:
            return jsonify({'ERROR': 'Preço inicial deve ser maior que zero'}), 400
    except (ValueError, TypeError):
        return jsonify({'ERROR': 'Preço inicial deve ser um número válido'}), 400

    horario_termino = datetime.fromisoformat(dados['horario_termino'])
    if horario_termino <= datetime.now():
        return jsonify({'ERROR': 'Horário de término deve ser no futuro'}), 400

    dados = request.json
    leilao_id = f"auction:{r.incr('contador_leiloes')}"
    dados_leilao = {
        'titulo': dados['titulo'],
        'descricao': dados['descricao'],
        'preco_inicial': dados['preco_inicial'],
        'preco_atual': dados['preco_inicial'], 
        'horario_termino': dados['horario_termino'],
        'ativo': 'true'
    }

    r.hset(leilao_id, mapping=dados_leilao)
    r.sadd('leiloes_ativos', leilao_id)
    r.delete(f"lances:{leilao_id}")

    return jsonify({'id': leilao_id, 'message': 'Leilão criado!'})

@app.route('/view-auctions', methods=['GET'])
def listar_leiloes():
    leiloes = []

    for leilao_id in r.smembers('leiloes_ativos'):
        leilao = r.hgetall(leilao_id)

        # Verificar se expirou
        if leilao.get('horario_termino'):
            if datetime.now() > datetime.fromisoformat(leilao['horario_termino']):
                r.hset(leilao_id, 'ativo', 'false')
                r.srem('leiloes_ativos', leilao_id)
                continue

        leilao['id'] = leilao_id
        leiloes.append(leilao)

    return jsonify(leiloes)

@app.route('/auction/<auction_id>', methods=['GET'])
def detalhes_leilao(auction_id):
    leilao = r.hgetall(auction_id)
    if not leilao:
        return jsonify({'ERROR': 'Leilão não encontrado'}), 404

    # Lista de lances
    lances = r.lrange(f"lances:{auction_id}", 0, -1)
    lances = [json.loads(lance) for lance in lances]

    resultado = {
        'id': auction_id,
        'titulo': leilao.get('titulo', ''),
        'descricao': leilao.get('descricao', ''),
        'preco_inicial': leilao.get('preco_inicial', 0),
        'preco_atual': leilao.get('preco_atual', 0),
        'horario_termino': leilao.get('horario_termino', ''),
        'ativo': leilao.get('ativo', 'false'),
        'lances': lances
    }

    return jsonify(resultado)

@app.route('/place-bid', methods=['POST'])
def fazer_lance():
    dados = request.json
    leilao_id = dados['leilao_id']
    usuario = dados['usuario']
    valor = float(dados['valor'])

    leilao = r.hgetall(leilao_id)
    if not leilao or leilao.get('ativo') != 'true':
        return jsonify({'ERROR': 'Leilão não encontrado ou inativo'}), 404

    # Verificar se expirou
    if leilao.get('horario_termino'):
        if datetime.now() > datetime.fromisoformat(leilao['horario_termino']):
            r.hset(leilao_id, 'ativo', 'false')
            r.srem('leiloes_ativos', leilao_id)
            return jsonify({'ERROR': 'Leilão expirado'}), 400

    # Verificar se lance é maior que o atual
    preco_atual = float(leilao.get('preco_atual', 0))
    if valor <= preco_atual:
        return jsonify({'ERROR': 'Lance deve ser maior que o atual'}), 400

    lance = {
        'usuario': usuario,
        'valor': valor,
        'data': datetime.now().isoformat()
    }

    r.hset(leilao_id, 'preco_atual', valor)
    r.rpush(f"lances:{leilao_id}", json.dumps(lance))

    mensagem = {
        'leilao_id': leilao_id,
        'usuario': usuario,
        'valor': valor,
        'data': lance['data'],
        'tipo': 'novo_lance'
    }

    r.publish('leilao_updates', json.dumps(mensagem))

    return jsonify({'message': 'Lance aceito!', 'novo_preco': valor})

@app.route('/notify')
def notificar_leiloes():
    def gerar():
        pubsub = r.pubsub()
        pubsub.subscribe('leilao_updates')

        for mensagem in pubsub.listen():
            if mensagem['type'] == 'message':
                yield f"data: {mensagem['data']}\n\n" # Funciona estilo linguagens dataflow/funcionais os dados sao gerados conforme necessarrio

    return app.response_class(
        gerar(),
        mimetype='text/event-stream'
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
