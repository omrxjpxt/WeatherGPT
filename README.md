# WeatherGPT 🌦️

> Conversational weather decision intelligence for real-world travel and daily decisions.

WeatherGPT is an AI-powered weather decision system designed to answer questions beyond **"What's the weather?"**

Instead of only displaying forecasts, WeatherGPT combines weather conditions, route information, travel time, transport mode, hazards, and alerts to help answer questions such as:

> **"Tomorrow at 8 AM, should I travel from Noida to Gurgaon by bike?"**

The system evaluates the trip context, identifies relevant environmental risks, and produces an explainable recommendation.

---

## 🎯 Project Context

WeatherGPT is being developed for **Smart India Hackathon 2026** under the **Disaster Management** theme.

The project focuses on transforming raw weather information into actionable travel and safety intelligence.

---

## 💡 Core Idea

Traditional weather applications answer:

> "What is the weather?"

WeatherGPT aims to answer:

> "Given the weather, route, time, transport mode, and hazards, what should I do?"

The system combines:

- Weather forecasts
- Route information
- Travel time
- Transport mode
- Weather-triggered hazards
- Official/secondary alerts
- Deterministic risk analysis
- Scenario comparison
- What-if analysis
- AI-assisted natural-language interaction

---

## ✨ Key Features

| Feature | Status |
|---|---|
| Conversational weather assistant | ✅ Implemented |
| Trip analysis | ✅ Implemented |
| Weather-aware route evaluation | ✅ Implemented |
| Deterministic risk engine | ✅ Implemented |
| Transport-mode comparison | ✅ Implemented |
| What-if scenario analysis | ✅ Implemented |
| Local hazard intelligence | ✅ Implemented |
| Alert analysis | ✅ Implemented |
| Historical replay UI | ✅ Implemented |
| Voice interaction UI | ✅ Implemented |
| Weather provider integration | ✅ Implemented |
| Routing provider integration | 🟡 Provider-ready |
| Traffic integration | 🟡 Planned |
| LLM integration | 🟡 Planned |
| Firestore persistence | 🟡 Planned |
| Production API credentials | 🟡 Pending |
| Direct authoritative weather-alert integration | 🟡 Provider/access dependent |

---

# 🧠 How WeatherGPT Works

WeatherGPT separates **data collection**, **decision logic**, and **AI language generation**.

```text
User Query
    │
    ▼
Intent Extraction
    │
    ▼
Trip / Scenario Context
    │
    ├── Weather
    ├── Route
    ├── Transport Mode
    ├── Hazards
    └── Alerts
    │
    ▼
Deterministic Risk Engine
    │
    ├── Exposure
    ├── Hazard Relevance
    ├── Route Conditions
    ├── Time Constraints
    └── Alert Overrides
    │
    ▼
Decision Result
    │
    ▼
AI Explanation
    │
    ▼
Flutter UI
