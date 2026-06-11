# 📦 Telegram Chat Automation App

[![GitHub license](https://img.shields.io/github/license/your-username/chat-automation-app?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org/downloads/)
[![Stars](https://img.shields.io/github/stars/your-username/chat-automation-app?style=flat-square)](https://github.com/your-username/chat-automation-app/stargazers)

---

## ✨ Overview

A **professional‑grade** Python desktop application that connects to **Telegram via the MTProto API** and **automatically replies** to private messages using **AI providers** like **DeepSeek** or **Google Gemini**. The UI is built with **PyQt6**, featuring a modern dark theme, real‑time dashboard, and a persistent SQLite log.

---

## 📂 Project Structure

```text
chat_automation_app/
├── main.py                # Entry point – bootstraps Qt UI + async loop
├── config.py              # Loads and validates .env variables
├── requirements.txt       # Python dependencies
├── .env.example           # Template for environment variables
│
├── ui/                    # PyQt6 UI components
│   ├── main_window.py
│   └── components.py
│
├── core/                  # Core logic
│   ├── telegram_client.py # Telethon MTProto client & message handler
│   └── ai_handler.py      # Async wrapper for DeepSeek / Gemini APIs
│
└── database/              # SQLite helper
    └── db_manager.py
```

---

## 🚀 Quick Start

### 1️⃣ Prerequisites

- **Python 3.11+** (recommended via `pyenv` or `conda`)
- A **Telegram account** (not a bot token) – we use the **user MTProto API**

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Obtain Telegram API credentials

1. Visit **[my.telegram.org](https://my.telegram.org)** and log in.
2. Open **API development tools** → **Create new application**.
3. Copy the **API ID** and **API Hash**.

### 4️⃣ Configure the environment

```bash
# Copy the example and edit the placeholders
cp .env.example .env
```

Edit `.env` and fill in:

- `TELEGRAM_API_ID` & `TELEGRAM_API_HASH`
- Choose a provider (`AI_PROVIDER=deepseek` or `gemini`) and set the corresponding API key.

### 5️⃣ Run the application

```bash
python main.py
```

On first launch Telethon will prompt for your **phone number** and the **verification code** Telegram sends. After successful login a session file (`Vantavail_session.session`) is saved for future runs.

---

## 🛠️ Usage

| Page | Functionality |
|------|----------------|
| **Dashboard** | Shows connection status and basic stats |
| **Automation** | Toggle auto‑reply, select AI provider, enable/disable scopes |
| **Chat Scopes** | Add/remove chats from *exclusion* or *inclusion* lists |
| **Logs & History** | View all AI‑generated replies |
| **Settings** | Edit API keys directly from the UI (overrides `.env`) |

### Scope Modes

- **All Private Chats Except Listed** – replies to everyone except the chats you add to the exclusion list.
- **Only Listed Chats** – replies **only** to the chats you explicitly add.

---

## 🏗️ Architecture Highlights

- **Async event loop** runs in a **dedicated background thread**, keeping the Qt UI responsive.
- **TelegramBotClient** emits Qt **signals** to safely update the UI from the async thread.
- AI calls use **`aiohttp`** with **automatic retries** and exponential back‑off.
- SQLite access is guarded by a **threading lock**, preventing race conditions.

---

## 📦 Adding a New AI Provider

1. Add the provider’s API key to `.env.example` and `config.py`.
2. Implement a `_call_<provider>()` method in `core/ai_handler.py`.
3. Extend the `if/elif` chain in `AIHandler.get_reply()`.
4. Add the provider to the `QComboBox` in `ui/main_window.py → AutomationPage`.

---

## 📄 License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and open a pull request. Follow the existing code style and run `flake8` before submitting.

---

## 📞 Support

For questions or issues, open a GitHub **Issue** or contact the maintainer at **Firaol** (Telegram username: `@Firaol`).
