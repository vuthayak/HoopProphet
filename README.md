# HoopProphet🏀

HoopProphet is a full-stack basketball analytics and prediction platform. It leverages machine learning to predict NBA game outcomes, analyze player performance, and provide advanced basketball statistics and prop line analysis. Now featuring AI-powered model performance summaries using Gemini 2.5 Flash!

## Features

- **NBA Player & Team Search:** Instantly search and select NBA players and teams.
- **Statistical Predictions:** Predict player stats for upcoming games using machine learning models.
- **Prop Line Analysis:** Get recommendations on over/under prop bets based on model predictions.
- **AI Model Performance Summary:** Receive concise, actionable insights about model accuracy and strengths, powered by Gemini 2.5 Flash.
- **Modern UI:** Built with React and Material-UI for a responsive, interactive experience.
- **API Powered:** FastAPI backend serves player/team data and prediction endpoints.

## Tech Stack

- **Frontend:** React, Material-UI, Framer Motion
- **Backend:** FastAPI, NBA_API, scikit-learn, pandas, xgboost
- **AI:** Gemini 2.5 Flash (Google Generative AI)
- **Containerization:** Docker, Docker Compose

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop) and [Docker Compose](https://docs.docker.com/compose/)
- Gemini API key (for AI summaries)

### Development Quick Start

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/HoopProphet.git
   cd HoopProphet
   ```

2. **Set up your environment variables:**
   - Create a `.env` file in the project root:
     ```
     GEMINI_API_KEY=your_actual_gemini_api_key_here
     ```

3. **Build and run the app:**
   ```sh
   docker-compose up --build
   ```

4. **Access the app:**
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Project Structure

```
HoopProphet/
├── hoopprophet/         # React frontend
├── server/              # FastAPI backend
├── docker-compose.yml
├── .env                 # Environment variables (not tracked by git)
├── README.md
```

### Environment Variables

- The frontend uses `REACT_APP_API_BASE` to determine the backend API URL (set automatically in Docker Compose).
- The backend uses `GEMINI_API_KEY` for Gemini 2.5 Flash integration.

### Development

- **Frontend only:**  
  ```sh
  cd hoopprophet
  npm install
  npm start
  ```
  (Set `REACT_APP_API_BASE=http://localhost:8000` if running backend locally.)

- **Backend only:**  
  ```sh
  cd server
  pip install -r requirements.txt
  uvicorn app:app --reload --host 0.0.0.0 --port 8000
  ```

## API Endpoints

- `GET /players` — List all NBA players
- `GET /teams` — List all NBA teams
- `POST /predict` — Predict player stats (requires player and team info; includes AI model summary)
- `GET /health` — Health check

## AI Model Summary

- After each prediction, HoopProphet uses Gemini 2.5 Flash to generate a personalized summary of model performance, accuracy, and actionable betting insights.
---

*Powered by [NBA API](https://github.com/swar/nba_api), open-source machine learning, and Gemini 2.5 Flash AI.*