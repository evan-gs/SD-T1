from flask import Flask, jsonify, request, render_template, send_from_directory
from datetime import datetime
from zoneinfo import ZoneInfo
import redis
import os
import json
import time
import threading

time_zone = ZoneInfo("America/Sao_Paulo")
app = Flask(__name__)
redis_host = os.getenv("REDIS_HOST", "redis-service")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

def agora():
    return datetime.now(tz=time_zone)

def ajustar_datetime(dt_str):
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=time_zone)
    return dt

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

    horario_termino = ajustar_datetime(dados['horario_termino'])
    if horario_termino <= agora():
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


    return jsonify({'id': leilao_id, 'message': 'Leilão criado!'})

@app.route('/view-auctions', methods=['GET'])
def listar_leiloes():
    leiloes = []

    for leilao_id in r.smembers('leiloes_ativos'):
        leilao = r.hgetall(leilao_id)

        # Verificar se expirou
        if leilao.get('horario_termino'):
            if agora() > ajustar_datetime(leilao['horario_termino']):
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
    lances_data = r.zrevrange(f"lances:{auction_id}", 0, -1, withscores=False)
    lances = [json.loads(lance) for lance in lances_data]

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

    campos_obrigatorios = ['leilao_id', 'usuario', 'email', 'valor']
    for campo in campos_obrigatorios:
        if campo not in dados or not dados[campo]:
            return jsonify({'ERROR': f'Campo {campo} é obrigatório'}), 400

    leilao_id = dados['leilao_id']
    usuario = dados['usuario'].strip()
    email = dados['email'].strip()
    valor = float(dados['valor'])

    while True:
        try:
            with r.pipeline() as pipe: # pipeline para evitar escrita concorrente, se o valor referente ao leilao_id mudar as operacoes sao canceladas
                pipe.watch(leilao_id)

                leilao = pipe.hgetall(leilao_id)
                if not leilao or leilao.get('ativo') != 'true':
                    pipe.unwatch()
                    return jsonify({'ERROR': 'Leilão inválido'}), 400

                preco_atual = float(leilao.get('preco_atual', leilao['preco_inicial']))
                if valor <= preco_atual:
                    pipe.unwatch()
                    return jsonify({'ERROR': 'Lance deve ser maior que o atual'}), 400

                lance = {
                    'usuario': usuario,
                    'valor': valor,
                    'email': email,
                    'data': agora().isoformat()
                }

                pipe.multi()
                pipe.hset(leilao_id, 'preco_atual', valor)
                pipe.zadd(f"lances:{leilao_id}", {json.dumps(lance): valor})
                pipe.execute()

                break

        except redis.WatchError:
            # outro usuário registou novo valor
            continue

    mensagem = {
        'leilao_id': leilao_id,
        'usuario': usuario,
	'email': email,
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

def finalizar_leiloes():
     while True:
        try:
            for leilao_id in list(r.smembers('leiloes_ativos')):
                leilao = r.hgetall(leilao_id)

                if leilao.get('horario_termino'):
                    try:
                        if agora() > ajustar_datetime(leilao['horario_termino']):
                            r.hset(leilao_id, 'ativo', 'false')
                            r.srem('leiloes_ativos', leilao_id)

                            lances_data = r.zrevrange(f"lances:{leilao_id}", 0, -1, withscores=False)
                            lances = [json.loads(lance) for lance in lances_data]

                            vencedor = lances[0] if lances else None

                            evento = {
                                'leilao_id': leilao_id,
                                'titulo': leilao.get('titulo', ''),
                                'descricao': leilao.get('descricao', ''),
                                'preco_inicial': float(leilao.get('preco_inicial', 0)),
                                'preco_final': float(leilao.get('preco_atual', 0)),
                                'horario_termino': leilao.get('horario_termino', ''),
                                'criador_email': leilao.get('criador_email', ''),
                                'total_lances': len(lances),
                                'vencedor': vencedor,
                                'todos_lances': lances,
                                'data_finalizacao': agora().isoformat(),
                                'tipo_evento': 'leilao_finalizado'
                            }

                            r.publish('leiloes_finalizados', json.dumps(evento))
                            app.logger.info(f"Evento publicado: leilão {leilao_id} finalizado")

                    except Exception as e:
                        app.logger.error(f"Erro ao processar leilão {leilao_id}: {e}")

            time.sleep(30)

        except Exception as e:
            app.logger.error(f"Erro no verificador: {e}")
            time.sleep(30)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    verificador_thread = threading.Thread(target=finalizar_leiloes, daemon=True)
    verificador_thread.start()
    app.run(host='0.0.0.0', port=5000)
