# Discord Bot Setup Guide

## 1. Create a Discord Application

Open:

https://discord.com/developers/applications

Click:

- New Application

Choose a name for your bot.

---

## 2. Create the Bot

Inside the application:

- Go to Bot
- Click Add Bot

---

## 3. Enable Intents

Enable:

- Message Content Intent
- Server Members Intent
- Presence Intent

---

## 4. Copy the Bot Token

Inside the Bot section:

- Reset Token
- Copy the token

Then run:

- discord-helper setup

Paste the token when requested.

---

## 5. Invite the Bot

Go to:

OAuth2 -> URL Generator

Scopes:

- bot
- applications.commands

Permissions:

- Send Messages
- Read Messages
- Connect
- Speak
- Use Voice Activity

Copy generated URL and open it in your browser.

---

## 6. Run the Bot

Run:

- discord-helper doctor
- discord-helper run
