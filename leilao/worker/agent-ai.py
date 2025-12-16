
import os
import json
import time
import logging
import redis
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ai-agent-worker")

REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class AIAgentWorker:

    def __init__(self):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY não configurada")

        if not SMTP_USER or not SMTP_PASSWORD:
            logger.warning("Credenciais SMTP não configuradas — e-mail será ignorado")

        if not DISCORD_WEBHOOK_URL:
            logger.warning("Webhook do Discord não configurado")

        self.client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("Cliente OpenAI inicializado com sucesso")

        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=6379,
            decode_responses=True,
            )
        logger.info(f"Conectado ao Redis em {REDIS_HOST}")

    def run(self):
        while True:
            try:
                self.listen_events()
            except redis.ConnectionError:
                logger.warning("Redis indisponível, tentando novamente em 5s...")
                time.sleep(5)
            except Exception as e:
                logger.exception(f"Erro inesperado: {e}")
                time.sleep(5)

    def listen_events(self):
        pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe("leiloes_finalizados")

        logger.info("Escutando canal Redis: leiloes_finalizados")

        for message in pubsub.listen():
            try:
                auction_data = json.loads(message["data"])
                if auction_data.get("tipo_evento") == "leilao_finalizado":
                    self.process_auction(auction_data)
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")

    def process_auction(self, auction_data):
        leilao_id = auction_data.get("leilao_id", "N/A")
        logger.info(f"Processando leilão {leilao_id}")

        report = self.generate_full_report(auction_data)

        self.send_email(auction_data, report)
        self.post_discord(auction_data, report)

        logger.info(f"Leilão {leilao_id} concluído")

    def generate_full_report(self, auction_data):
        prompt = f"""
            Gere um relatório COMPLETO e profissional sobre o leilão finalizado. Não deixe nenhuma informação como placeholher (exemplos: [nome], (valor), ect.). Não adicione nenhuma informação que não foi solicitada.

            Inclua:
            - Resumo do leilão
            - Item e descrição
            - Preço inicial e final
            - Número de lances
            - Nome do vencedor

            DADOS:
            Item: {auction_data['titulo']}
            Descrição: {auction_data['descricao']}
            Preço inicial: R$ {auction_data['preco_inicial']:.2f}
            Preço final: R$ {auction_data['preco_final']:.2f}
            Total de lances: {auction_data['total_lances']}
            Vencedor: {auction_data.get('vencedor', {}).get('usuario', 'Nenhum')}
            """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um analista especialista em leilões."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.6
        )

        return response.choices[0].message.content

    def send_email(self, auction_data, report):
        winner = auction_data.get("vencedor")
        if not winner or not SMTP_USER or not SMTP_PASSWORD:
            return

        subject = f"Parabéns! Você venceu o leilão: {auction_data['titulo']}"

        body = f"""
            Olá {winner.get('usuario', 'Cliente')},

            Parabéns! Você venceu o leilão do item:
            {auction_data['titulo']}
            Valor final: R$ {auction_data['preco_final']:.2f}

            Segue abaixo o relatório completo do leilão e os próximos passos:

            {report}
            """

        self._send_smtp_email(winner["email"], subject, body)

    def _send_smtp_email(self, to_email, subject, body):
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email enviado para {to_email}")

    def post_discord(self, auction_data, report):
        if not DISCORD_WEBHOOK_URL:
            return

        winner = auction_data.get("vencedor", {})
        winner_name = winner.get("usuario", "Ninguém")

        message = f"""
            **LEILÃO FINALIZADO**

            **Parabéns {winner_name}!**
            Item: **{auction_data['titulo']}**
            Valor final: **R$ {auction_data['preco_final']:.2f}**

            📄 **Relatório completo**
            {report}
            """

        payload = {
            "content": message,
            "username": "Leilão Bot"
        }

        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )

        if response.status_code == 204:
            logger.info("Mensagem enviada para o Discord")
        else:
            logger.error(f"Erro Discord: {response.status_code}")

if __name__ == "__main__":
    worker = AIAgentWorker()
    worker.run()
