# Projeto feito por 
 - Gabriel Evangelista Gonçalves da Silva - RA 802791
 - Gabriel Andrade - RA 815407

# Estrutura do Projeto

```bash
    leilao/
    ├── app/
    │   ├── app.py                # API Flask
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── static/
    │   │   └── style.css
    │   └── templates/
    │       └── index.html
    ├── k8s/
    │   ├── flask.yaml            # Deployment / Service do Flask
    │   ├── redis.yaml            # Redis
    │   └── namespace.yaml
    ├── worker/
    │   ├── agent-ai.py           # Worker que consome finalizações
    │   ├── Dockerfile
    │   ├── agent.yaml            # Deployment do worker
    │   ├── secrets.yaml
    │   └── deploy-worker.sh
    ├── deploy.sh                 # script de deploy Kubernetes
    ├── testes.sh                 # script de teste
    └── kind-config.yaml       
```

# Requisitos

- Docker
- Python 3.11
- kubectl 
- Redis
- curl (caso não queria usar localhost)
- date 

# Como rodar

```bash
cd leilao
chmod +x deploy.sh
./deploy.sh

cd worker
chmod +x deploy-worker.sh
./deploy-worker.sh
```

Se tudo foi bem sucedido será possível acessar a aplicação no endereço http://localhost:30080

# Uso via curl

## Criar leilão
```bash
curl -X POST http://localhost:30080/create-auction \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Xbox 360",
    "descricao": "Xbox 360 com Kinect",
    "preco_inicial": 1000,
    "horario_termino": "2025-12-16T23:00:00-03:00"
  }'
```

## Fazer lance
```bash
curl -X POST http://localhost:30080/place-bid \
  -H "Content-Type: application/json" \
  -d '{
    "leilao_id": "auction:1",
    "usuario": "Julio",
    "email": "julio@email.com",
    "valor": 1250
  }'
```

## Listar leilões ativos
```bash
curl -X GET http://localhost:30080/view-auctions
```

## Ver detalhes de um leilão
```bash
curl -X GET http://localhost:30080/auction/auction:1
```

## Acompanhar eventos
```bash
curl -X GET -N http://localhost:30080/notify
```

# Testes automatizados
```bash
cd leilao
chmod +x testes.sh
./testes.sh
```

Será criado um leilão e 10 lances concorrentes serão enviados, alguns falharam devido ao redis watch que os fará tentar novamente o lance quando o valor for alterado por outro lance e, se esse lance concorrente for maior, o atual falhará pois o preço é menor que o atual.
- !!!IMPORTANTE: esse script só funciona para a auction:1, se quiser testar mais de uma vez será necessário mudar esse valor no script {leilao_id} 

