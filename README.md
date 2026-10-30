# GoPlan ✈️

A modern, algorithmically-driven intelligent travel planning and hotel booking application powered by **Multi-Criteria Decision Making (MCDM)**, **Orienteering Route Optimization**, **Weather-Robust Planning**, **Dynamic Perishable Room Pricing**, and **Dynamic UPI / Check-In QR Passes**.

**Live Demo:** [https://goplan.onrender.com/](https://goplan.onrender.com/)

---

## 📋 Overview

GoPlan elevates travel planning beyond basic distance heuristics into an end-to-end decision intelligence platform. It computes optimal transport modes using **Best-Worst Method (BWM)** and **TOPSIS / MAUT**, models genuine live ticket pricing across Indian Railways (IRCTC), State Road Transport (SRTC), and airline GDS feeds, solves the **Orienteering Problem** for multi-day itineraries with live **Open-Meteo** weather shielding, manages dynamic hotel pricing with **Mystery Hotel Deals**, and delivers instant smartphone check-in passes via pure-vector SVG QR codes.

---

## ✨ Features

### 1. Intelligent Multi-Criteria Transport Recommendation
- **Best-Worst Method (BWM) - Rezaei / Murad et al. (2015, 2016)**:
  - Solves linear optimization using only $(2n - 3)$ reference comparisons between the user's "most important" and "least important" criteria (Cost, Travel Time, $\text{CO}_2$ Emissions, Comfort).
  - Eliminates rank-reversal anomalies inherent in legacy AHP pairwise matrices.
- **TOPSIS & Multi-Attribute Utility Theory (MAUT)**:
  - Computes Euclidean distance to the Positive-Ideal Solution ($A^*$) and Negative-Ideal Solution ($A^-$).
  - Incorporates diminishing marginal returns on price to model realistic traveler preference curves.
- **Algorithmic Transparency ("Why this recommendation?")**:
  - Provides a complete criterion-by-criterion utility breakdown explaining exactly why a specific transport mode was chosen.

### 2. Genuine Live Ticket Pricing Engine
- 🚂 **Indian Railways (IRCTC)**: Exact telescopic passenger fare slabs published by the Ministry of Railways for Second Sitting (2S), AC Chair Car (CC), Sleeper Class (SL), 3-Tier AC (3A), and 2-Tier AC (2A).
- 🚌 **State Transport (SRTC)**: Government-notified per-km fare tables for Ordinary Express vs. Premium AC Volvo / Shivneri / Airavat.
- ✈️ **Airline GDS**: Live Amadeus Flight Offers API integration with real-time route baselines and one-click deep-link verification to Google Flights.

### 3. Weather-Robust Orienteering Itinerary Builder
- **Tourist Trip Design Problem (TTDP)**:
  - Formulates daily sightseeing as an Orienteering Problem, greedily maximizing cumulative attraction utility per hour subject to daily time budgets.
- **Open-Meteo Weather Shielding**:
  - Fetches real-time 7-day meteorological forecasts for the destination.
  - Automatically activates **Sheltered Swaps** when rain probability exceeds 40%, swapping exposed outdoor sights for indoor cultural museums, science centers, or art galleries.
- **Optimal Climate Window**:
  - Identifies the best seasonal months to visit based on historical precipitation and temperature bands.

### 4. Portfolio Budget Optimizer (Knapsack Problem)
- Implements a pure-Python Multi-Choice Knapsack dynamic programming solver.
- Automatically generates three Pareto-optimal trip portfolios:
  - **Cheapest Option**: Minimum spend maximizing budget conservation.
  - **Fastest Option**: Minimized travel time.
  - **Greenest Option**: Lowest carbon footprint ($\text{CO}_2$ emissions).

### 5. Real Hotel Booking & Multi-Room Layouts
- **TomTom POI Search API (Category 7314)**: Live hotel queries around destination coordinates with verified heritage and city-center accommodations.
- **Multi-Room Configurations**:
  - 🛏️ **1 Bed Room** (Standard / Deluxe Double, 320 sq ft, up to 2 guests).
  - 🛏️🛏️ **2 Bed Room** (Executive Suite / 2 BHK, 650 sq ft, up to 4 guests).
  - 🛏️🛏️🛏️ **3 Bed Room** (Presidential Villa / 3 BHK, 1,150 sq ft, up to 6+ guests).
- **Dynamic Perishable Room Pricing**:
  - Automatically adjusts nightly rates based on booking lead-time ($T - t$) and real-time occupancy demand counters.
- **Opaque Mystery Deals (Balancing Policy)**:
  - Deeply discounted 4-star and 5-star mystery hotel rates (up to 30% savings) that balance hotel inventory across candidates with secret reveal upon confirmed booking.

### 6. Dynamic Auto-Filled UPI QR Code & Tiered Returns
- **Dynamic UPI Payment (NPCI `upi://pay` Spec)**:
  - Automatically generates an instant UPI QR code encoded with payee details (`jiyanshujain321@oksbi`, Payee: Jiyanshu Jain) and the **exact booking total auto-filled** upon scanning in Google Pay, PhonePe, Paytm, BHIM, or Cred.
- **Tiered Omnichannel Cancellation Policy**:
  - Time-decaying refund tiers protecting traveler and property commitments:
    - *Early Bird* (> 7 days before check-in): 100% full refund.
    - *Flexible Standard* (3–7 days before check-in): 75% refund.
    - *Last Minute* (1–3 days before check-in): 25% refund.
    - *Non-Refundable* (< 24 hours before check-in): 0% refund.

### 7. Scannable Digital Check-In QR Pass
- Generates a full-capacity, high-resolution vector SVG QR code on the confirmation ticket.
- When scanned by any smartphone camera (Google Lens, iPhone Camera, Samsung QR), it instantly presents verified booking details:
  ```text
  === GOPLAN DIGITAL CHECK-IN PASS ===
  Booking ID: #BKGUEST1
  Lead Traveler: Aarav Patel
  Total Passengers: 4 Travelers
  Email: aarav@example.com
  Phone: 9876543210
  Destination: Hampi, Karnataka
  Stay: Heritage Resort Hampi
  Check-In Date: 2026-10-29
  Total Paid: Rs. 14440.00
  Status: CONFIRMED & VERIFIED
  ===================================
  ```

---

## 🛠️ Tech Stack

### Backend
- **Python 3.10+**
- **Django 5.2+** - High-level Python web framework
- **qrcode & Pillow** - Dynamic QR code matrix & image generation
- **Requests** - HTTP client for TomTom and Open-Meteo REST APIs
- **PostgreSQL** - Production database via `psycopg2-binary`
- **Gunicorn** - Production WSGI HTTP server
- **SQLite3** - Zero-configuration local development database

### Frontend
- **HTML5 & CSS3** - Modern dark-mode glassmorphic interface with `backdrop-filter: blur(28px)`
- **Font Awesome 6.5 & Plus Jakarta Sans** - Icons and typography
- **Django Template Engine** - Server-side rendering

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Git

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/jiyanshuj/GoPlan.git
   cd GoPlan
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS / Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables (Optional)**
   Create a `.env` file in the project root:
   ```env
   DEBUG=True
   SECRET_KEY=your_django_secret_key
   TOMTOM_API_KEY=your_tomtom_api_key_here
   AMADEUS_CLIENT_ID=your_amadeus_client_id  # Optional
   AMADEUS_CLIENT_SECRET=your_amadeus_secret # Optional
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```
   Open `http://127.0.0.1:8000/` in your browser.

---

## 📁 Project Structure

```
GoPlan/
├── manage.py                 # Django management script
├── db.sqlite3               # Local SQLite database
├── requirements.txt         # Production dependencies (Django, qrcode, Pillow, etc.)
├── .gitignore               # Environment & build ignores
│
├── goplan/                  # Project configuration
│   ├── settings.py          # Django settings & database routing
│   ├── urls.py              # Root URL router
│   ├── wsgi.py              # WSGI server application
│   └── asgi.py              # ASGI application
│
├── web/                     # Core application
│   ├── forms.py             # TripForm with BWM criteria selectors
│   ├── views.py             # View controllers (trip_view, final, payment, pay, booking_success)
│   ├── urls.py              # App URL routes
│   ├── api.py               # TomTom geocoding, route calculation & hotel search
│   ├── mcdm.py              # Best-Worst Method (BWM) & TOPSIS/MAUT ranking engine
│   ├── live_prices.py       # IRCTC slabs, SRTC bus tariffs & live GDS flight search
│   ├── itinerary.py         # Orienteering problem & weather-robust planner (Open-Meteo)
│   ├── optimizer.py         # Knapsack budget portfolios, mystery deals & cancellation tiers
│   ├── qr.py                # Pure-Python SVG check-in pass & auto-filled UPI QR generator
│   ├── tests.py             # Automated unit & end-to-end integration test suite
│   ├── models.py            # Model definitions
│   └── admin.py             # Admin registrations
│
├── templates/               # Glassmorphic UI templates
│   ├── trip_form.html       # Landing page with interactive Indian destinations showcase
│   ├── success.html         # Transport rankings, why-panel, itinerary & budget portfolios
│   ├── booking.html         # Room layouts (1/2/3 Bed), live hotel list & mystery deals
│   ├── form.html            # Guest information form with live stay summary
│   ├── payment.html         # Dynamic UPI QR with auto-filled amount & cancellation policy
│   ├── booking_success.html # Verified digital boarding pass with scannable QR pass
│   └── error.html           # Graceful fallback error view
│
└── static/                 # Static assets (brand logos, hero imagery, badges)
```

---

## 🧪 Testing

The repository contains comprehensive automated unit and integration tests covering form validation, BWM weight derivation, TOPSIS matrix normalization, Orienteering heuristic sequencing, weather robustness, Knapsack portfolio generation, dynamic room pricing, tiered cancellations, and full end-to-end booking workflows with QR pass generation.

Run the test suite:
```bash
python manage.py test
```

Expected output:
```text
Creating test database for alias 'default'...
.........................
----------------------------------------------------------------------
Ran 25 tests in ~8.0s

OK
Destroying test database for alias 'default'...
```

---

## 📝 API Endpoints & Routes

| Method | Route | Description |
|---|---|---|
| `GET` / `POST` | `/` | Trip planning form, distance calculation, BWM & MCDM results |
| `GET` | `/home/` | Alias route for trip planner |
| `GET` | `/booking/` | Hotel selection with multi-room configs, MAUT ranking & mystery deals |
| `GET` / `POST` | `/forming/` | Guest details capture form |
| `GET` / `POST` | `/pay/` | Payment page with dynamic auto-filled UPI QR code |
| `GET` | `/success/` | Booking confirmation ticket with scannable Digital Check-In QR Pass |

---

## 🌐 Production Deployment

GoPlan is configured for deployment on [Render](https://render.com/):

1. **Build Command**:
   ```bash
   pip install -r requirements.txt && python manage.py migrate
   ```
2. **Start Command**:
   ```bash
   gunicorn goplan.wsgi:application
   ```
3. Set `DEBUG=False` and supply `TOMTOM_API_KEY` and optional `DATABASE_URL` (PostgreSQL) in your Render dashboard environment variables.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by [Jiyanshu Jain](https://github.com/jiyanshuj)**
