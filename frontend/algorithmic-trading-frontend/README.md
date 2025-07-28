# Algorithmic Trading System - Frontend

This is the Next.js frontend for the enterprise-grade algorithmic trading system. This project was initialized as part of Phase 4 of development.

## Project Overview

The frontend is a professional trading platform that integrates seamlessly with the backend services, including the NautilusTrader trading engine, FastAPI, and various databases. It now features robust user authentication and management capabilities, allowing users to securely register, log in, and manage their profiles. The application provides advanced charting, real-time dashboards, and intuitive trading interfaces, with enhanced frontend-backend integration for displaying AI-driven predictions.

## Getting Started

First, install the dependencies:

```bash
npm install
```

Then, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Available Scripts

- `npm run dev`: Runs the app in the development mode.
- `npm run build`: Builds the app for production.
- `npm run start`: Starts the production server.
- `npm run lint`: Lints the code.

## Architecture Notes

- **Framework**: Next.js with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**:
  - **Client-side**: Zustand for UI state.
  - **Server-side**: React Query for managing server state and caching.
- **API Calls**: Axios
- **Linting**: ESLint

### Project Structure

```
/src
|-- /app
|-- /components
|-- /hooks
|-- /services
|-- /store
|-- /types
|-- /utils
