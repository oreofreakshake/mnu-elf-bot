# MNU-elf-bot
A Telegram bot designed to help MNU (Maldives National University) students manage their academic schedule and access important resources. While the bot aims to make student life easier, remember that your academic success still requires your dedication.

## Features
### Current Features
- Automated Timetable Generation
  - Get your personalized class schedule instantly
  - Support for up to 4 subjects (expandable upon request)
- Resource Hub
  - Quick access to essential college-related links
  - Centralized repository for academic resources
- Smart Notifications
  - Automated class time reminders

### Coming Soon
- Assignment Tracker
  - Set and manage assignment deadlines
  - Customizable reminder system
  - Exam schedule management

## How to Use
### Timetable System
- Join our support [group](https://t.me/MNUelf) to access the latest schedules
- Share your official class schedule from MNU Viber groups in the support [group](https://t.me/MNUelf)
- The bot will be updated with the latest timetable information
- Access your personalized schedule anytime through the bot

## Contributing
All contributions are welcome! Here's how you can help:
- Fork and ⭐ the repository
- Submit pull requests
- Suggestion to improve the bot
Feel free to use this code for your own projects (with attribution).

## Important Disclaimers
_By using this bot, you acknowledge and agree to the following_

1. Responsibility
  - The bot creator nor the bot itself is not liable for missed classes
  - Users are responsible for providing updated schedules
  - Regular verification of the schedules are recommended (let someone know about the latest update of the schedule, this is a community driven project)
2. Independence
  - This is an unofficial tool, not affiliated with MNU
  - Cannot integrate with official MNU systems (Moodle, self-service, My portal) due to security protocols
3. Open Source Notice
  - This bot is open-source and may be forked
  - We're not responsible for modified versions
  - Verify authenticity:
    - Check bot username
    - Contact developer directly
    - Join the official support [group](https://t.me/MNUelf)
4. Usage Philosophy
  - The bot is a supplement, not a replacement for personal responsibility
  - Use it to enhance, not eliminate, your academic engagement

## Useful Links
- Support Group: https://t.me/MNUelf

## How to run locally
1. Prepare .env
```
cp .env.example .env
```

configure at least

```
BOT_TOKEN=your_botfather_token
TELEGRAM_BOT_USERNAME=your_bot_username
ADMIN_TELEGRAM_IDS=your_numeric_telegram_id

POSTGRES_DB=timetable
POSTGRES_USER=mnuelf
POSTGRES_PASSWORD=local-database-password

BOT_SERVICE_TOKEN=local-development-token
SESSION_DAYS=7
SECURE_COOKIES=false
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```
`BOT_SERVICE_TOKEN` is the token you enter on the local sign-in screen.

On a fresh database, a successful local sign-in creates an administrator for the first numeric ID in `ADMIN_TELEGRAM_IDS`. Sending `/start` to the bot afterward fills in that administrator's Telegram profile details.

2. Start development mode `localhost:5173` 
```
docker compose -f compose.yml -f compose.dev.yml --profile dev up -d --build postgres api worker bot frontend-dev
```

4. View logs
```
docker compose -f compose.yml -f compose.dev.yml --profile dev logs -f
```

6. Test the production-style frontend locally `localhost:8080` 
```
docker compose -f compose.yml -f compose.dev.yml up -d --build frontend
```

8. Stop Locally
```
docker compose -f compose.yml -f compose.dev.yml --profile dev down
```
