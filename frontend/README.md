# Web Dashboard - Frontend Setup

This directory contains the frontend for the Bulk Email Tool dashboard.

## Quick Start

```bash
# Install dependencies
npm install

# Development server
npm run serve

# Build for production
npm run build
```

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Dashboard.vue
│   │   ├── CampaignList.vue
│   │   ├── CreateCampaign.vue
│   │   ├── CampaignDetails.vue
│   │   ├── TemplateManager.vue
│   │   ├── AuditLogs.vue
│   │   └── Navigation.vue
│   ├── views/
│   │   ├── Login.vue
│   │   ├── Register.vue
│   │   ├── Home.vue
│   │   └── Profile.vue
│   ├── services/
│   │   └── api.js
│   ├── store/
│   │   └── index.js
│   ├── App.vue
│   └── main.js
├── package.json
└── vue.config.js
```

## Features

- **Authentication**: Login/Register with JWT tokens
- **Dashboard**: Real-time monitoring of email campaigns
- **Campaign Management**: Create, approve, and track campaigns
- **Template Editor**: Create and manage email templates
- **Recipient Management**: Upload and manage recipient lists
- **Analytics**: View detailed campaign statistics
- **Audit Logs**: Complete audit trail of all actions
- **Natural Language Queries**: Ask questions in plain English

## Environment Variables

Create a `.env` file:

```
VUE_APP_API_URL=http://localhost:8000/api/v1
VUE_APP_ENV=development
```

## Security Features

- JWT token-based authentication
- CSRF protection
- Secure cookie handling
- Input validation
- Rate limiting indicators
- Auto-logout on token expiry
