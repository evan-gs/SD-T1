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

# Operações possíveis

### Criar leilão (POST /create-auction)
- Responsável por cadastrar um novo leilão no sistema
- Recebe informações como título, descrição, preço inicial e horário de término
- O leilão é armazenado no Redis e passa a ficar disponível para receber lances até o horário definido

### Realizar lance (POST /place-bid)
- Permite que um usuário envie um lance para um leilão ativo
- O sistema verifica se o leilão existe, se ainda está ativo e se o valor do lance é maior que o lance atual
- Para evitar condições de corrida, a atualização do lance é feita utilizando mecanismos de concorrência do Redis para evotar escrita concorrente

### Listar leilões ativos (GET /view-auctions)
- Retorna todos os leilões que ainda estão ativos no sistema
- Essa operação é usada para que usuários visualizem quais leilões estão disponíveis para participação

### Ver detalhes de um leilão (GET /auction/<id>)
- Exibe todas as informações de um leilão específico: dados gerais do leilão, preço atual, histórico de lances ordenado
- Usada para acompanhamento detalhado do andamento do leilão

### Notificações em tempo real (GET /notify)
- Fornece eventos em tempo real utilizando pub/sub
- Sempre que um novo lance é realizado ou o estado do leilão muda, uma notificação é enviada para os clientes conectados

### Worker

O worker é um componente executado em segundo plano responsável por monitorar os leilões armazenados, verifica prazos de encerramento, encerra leilões, gera relatório via openai e parabeniza o vencedor no email e discord enviando também o relatório gerado

# Uso via curl

### Criar leilão
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

### Fazer lance
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

### Listar leilões ativos
```bash
curl -X GET http://localhost:30080/view-auctions
```

### Ver detalhes de um leilão
```bash
curl -X GET http://localhost:30080/auction/auction:1
```

### Acompanhar eventos
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

### Testes de pods

para matar um pod e ve-lo subindo novamente
```bash
sudo kubectl delete pod flask-app-74bcf694c5-jnckh -n leilao-ns
```

para derrubar todos os pods do namespace
```bash
sudo kubectl delete pod -l app=flask-app -n leilao-ns 
```

para aumentar as replicas
```bash
sudo kubectl scale deployment flask-app -n leilao-ns --replicas=3
```
