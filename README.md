# 🤖 Vantavail AI Telegram Automation

<p align="center">
  <strong>Professional AI-Powered Telegram Auto-Reply Desktop Application</strong>
</p>

<p align="center">
Built with Python • PyQt6 • Telethon • DeepSeek • Gemini
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/PyQt6-Desktop_App-41CD52?style=for-the-badge">
  <img src="https://img.shields.io/badge/Telegram-MTProto-26A5E4?style=for-the-badge&logo=telegram&logoColor=white">
  <img src="https://img.shields.io/badge/AI-Gemini_|_DeepSeek-purple?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-MIT-success?style=for-the-badge">
</p>

<p align="center">
  <strong>Automate Telegram conversations intelligently using modern AI providers.</strong>
</p>

---

## 📚 Table of Contents

* Overview
* Screenshots
* Features
* Technology Stack
* Project Structure
* Quick Start
* Usage
* Architecture
* Project Status
* Roadmap
* Contributing
* License
* Support

---

## 📖 Overview

Vantavail AI Telegram Automation is a desktop application that connects directly to Telegram through the MTProto API and automatically responds to incoming private messages using advanced AI models such as DeepSeek and Google Gemini.

Designed with a modern PyQt6 interface, the application provides real-time monitoring, configurable chat scopes, conversation logging, and flexible automation controls while maintaining a responsive user experience through asynchronous processing.

---

## 📸 Application Preview

<p align="center">
  <img src="assets/dashboard-connected.png" width="48%">
  <img src="assets/automation-control.png" width="48%">
</p>

<p align="center">
  <img src="assets/chat-scope.png" width="48%">
  <img src="assets/security.png" width="48%">
</p>

<p align="center">
  <img src="assets/scheduled-appointments.png" width="48%">
  <img src="assets/settings.png" width="48%">
</p>

---

## ✨ Features

- 🤖 AI-powered automatic replies
- 💬 Telegram MTProto integration
- ⚡ DeepSeek AI support
- ⚡ Google Gemini AI support
- 🎨 Modern PyQt6 desktop interface
- 📊 Real-time monitoring dashboard
- 📋 Chat inclusion & exclusion management
- 🔒 SQLite conversation logging
- 🚀 Fully asynchronous architecture
- ⚙️ Dynamic AI provider switching

---

## 🛠 Technology Stack

| Category      | Technology              |
| ------------- | ----------------------- |
| Language      | Python 3.11+            |
| GUI Framework | PyQt6                   |
| Telegram API  | Telethon                |
| Database      | SQLite                  |
| Networking    | aiohttp                 |
| AI Providers  | DeepSeek, Google Gemini |
| Configuration | dotenv                  |

---

## 📂 Project Structure

```text
chat_automation_app/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── assets/ 
│   ├── dashboard-connected.png
│   ├── automation-control.png
│   ├── chat-scope.png
│   ├── security.png
│   ├── scheduled-appointments.png
│   └── settings.png
├── ui/
│   ├── main_window.py
│   └── components.py
│
├── core/
│   ├── telegram_client.py
│   └── ai_handler.py
│
└── database/
    └── db_manager.py
```

---

## 🚀 Quick Start

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Firaol-devsec-labs/vantavail-AI-chat-automation.git

cd vantavail-AI-chat-automation
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Create Telegram API Credentials

1. Sign in to https://my.telegram.org
2. Open **API Development Tools**
3. Create a new application
4. Copy your API ID and API Hash

### 4️⃣ Configure Environment Variables

```bash
cp .env.example .env
```

Example configuration:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key

# OR

AI_PROVIDER=gemini
GEMINI_API_KEY=your_api_key
```

### 5️⃣ Launch Application

```bash
python main.py
```

On first launch, Telethon will request:

* Telegram phone number
* Verification code

After successful login, a local session file is stored for future authentication.

---

## 🛠 Usage

### Dashboard

Monitor:

* Connection status
* Provider status
* Activity metrics
* Automation statistics

### Automation

* Enable or disable auto-replies
* Select AI provider
* Configure automation behavior

### Chat Scope Management

#### All Private Chats Except Listed

Automatically responds to all private chats except those added to the exclusion list.

#### Only Listed Chats

Responds only to chats explicitly added to the inclusion list.

### Logs & History

Review:

* AI-generated replies
* Message history
* Activity logs

---

## 🏗 Architecture

```mermaid
flowchart LR

User --> Telegram

Telegram --> Telethon_Client

Telethon_Client --> AI_Handler

AI_Handler --> DeepSeek

AI_Handler --> Gemini

AI_Handler --> SQLite_Database

Telethon_Client --> Dashboard

Dashboard --> User
```

---

## 📈 Project Status

| Component                      | Status          |
| ------------------------------ | ----------------|
| Telegram MTProto Integration   | ✅ Complete     |
| DeepSeek Integration           | ✅ Complete     |
| Gemini Integration             | ✅ Complete     |
| PyQt6 Dashboard                | ✅ Complete     |
| SQLite Logging                 | ✅ Complete     |
| Chat Scope Management          | ✅ Complete     |
| Async Processing               | ✅ Complete     |
| Responsive Layout Improvements | 🚧 In Progress |
| Persistent Memory System       | 🚧 Planned     |
| Smart User Recognition         | 🚧 Planned     |

---

## 🗺️ Roadmap

### Version 1.1

* 📱 Responsive UI improvements
* 🧠 Persistent conversation memory
* 👥 Smart user recognition
* 📊 Enhanced analytics dashboard
* 📝 Advanced logging controls

### Future Releases

* Multi-account support
* Plugin architecture
* Additional AI providers
* Exportable reports
* Extended security controls

---

## 🤝 Contributing

Contributions are welcome.

```bash
git fork
git checkout -b feature/new-feature
```

Submit a pull request describing your improvements.

Before submitting:

```bash
flake8
```

---

## 📄 License

Distributed under the MIT License.

See the LICENSE file for additional information.

---

## 📞 Support

**Maintainer:** Firaol Terefa

**Telegram:** @vantavails

**Email:** [firaolterefatolosa@gmail.com](mailto:firaolterefatolosa@gmail.com)

---

<p align="center">
  ⭐ If you find this project useful, consider giving it a star.
</p>

<p align="center">
Built with ❤️ using Python, Telethon, PyQt6, DeepSeek, and Gemini.
</p>
