import requests
import os
from dotenv import load_dotenv

# Charger les variables depuis le fichier .env
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Étape 1 : Récupérer les derniers messages pour trouver le chat_id
def get_chat_id():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    data = response.json()

    print("\n🔍 Résultat des messages visibles :\n")

    for result in data.get("result", []):
        message = result.get("message") or result.get("channel_post")
        if message:
            chat = message["chat"]
            print("📢 Titre du chat :", chat.get("title"))
            print("🆔 Chat ID       :", chat["id"])
            print("📝 Message       :", message.get("text"))
            print("-" * 40)

# Étape 2 : Envoyer un message dans le canal
def send_test_message():
    message = "✅ Hello test test test another one !"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    response = requests.post(url, data=payload)

    print("\n📨 Message envoyé")
    print("Status code :", response.status_code)
    print("Réponse :", response.json())

# --- Lancer le script ---
if __name__ == "__main__":
    get_chat_id()
    send_test_message()
