# 🏋️ FitZone Gym - Django Web Application

A full-stack Gym & Fitness Web Application with database-driven Diet Plans, User Authentication (Register & Login), Gym Membership Subscription Checkout, and a complete **Django REST API**. Built with **Django 6**, **SQLite3**, **Django REST Framework (DRF)**, and **Tailwind CSS**.

---

## 🌟 Features Implemented

1. **Gym Landing Web Page (`gym_web.html`)**
   - High-energy, responsive UI inspired by modern fitness brands.
   - Dynamic **Membership Plans** fetched directly from SQLite.
   - **Diet & Nutrition Plans Showcase** with live modal preview via AJAX.
   - Interactive **BMI Calculator** with automated diet recommendations.
   - Certified **Trainers showcase** from the database.
   - Testimonial slider, Member counters, and Contact inquiry form.

2. **Diet Plans in DB & Showcase ("add dite play in db and show")**
   - Full **DietPlan** model in SQLite storing:
     - Title, Category (*Muscle Gain, Weight Loss, Keto, High Protein, Vegetarian*)
     - Calorie target (kcal), Protein (g), Carbs (g), Fats (g)
     - Meal schedules (*Breakfast, Mid-Morning, Lunch, Evening Snack, Dinner*)
     - Daily water hydration goals and expert tips.
   - Dedicated **Diet Plans Database page** (`/diet-plans/`) with category filter pills.
   - Users can **Adopt Diet Plans** directly to their profile.

3. **Authentication (Register & Login)**
   - **Registration Page (`/register/`)**:
     - Modeled from `gym_form.html`.
     - Fields: Name, Email, Password, Phone, Age, Gender, Plan Choice, Fitness Goals.
     - Automatically creates account, member profile, and optional membership.
   - **Login Page (`/login/`)**:
     - Sleek dark glassmorphic UI modeled from `dash_logpage.html`.
     - Supports login with username or email + show/hide password toggle.

4. **Membership Checkout**
   - **Payment Checkout (`/checkout/<plan_id>/`)**:
     - Modeled from `payment.html`.
     - Pre-fills chosen plan and calculates total.
     - Supports discount coupons (e.g., `FIT10` for 10% off, `FIT20` for 20% off).
     - Selecting and purchasing a membership creates an active `Subscription` record in SQLite linked to the user.

5. **Complete REST API ("add restapi")**
   - Built with **Django REST Framework (DRF)**.
   - Browsable API interface available at `/api/`.
   - Endpoints:
     - `GET /api/plans/` - List active membership plans.
     - `GET /api/diet-plans/` - List all diet plans (filter with `?category=...`).
     - `GET /api/subscriptions/` - List member subscriptions.
     - `POST /api/subscriptions/` - Add subscription programmatically.
     - `GET /api/stats/` - Live aggregated metrics in JSON.
     - `POST /api/auth/register/` - Member registration via JSON.

---

## 🔑 Default Credentials

| Role | Username / Email | Password | Access |
|---|---|---|---|
| **Administrator** | `admin` / `admin@fitzone.com` | `admin123` | Full Django Admin Access |
| **Demo Member** | `john` / `john@example.com` | `password123` | Member Account + Diet Plans |

---

## 🚀 How to Run the Server

From the `D:\gym_project` directory:

```bash
cd D:\gym_project
python manage.py runserver 8000
```

Open your browser at:
- **Gym Website**: `http://127.0.0.1:8000/`
- **Diet Plans Database**: `http://127.0.0.1:8000/diet-plans/`
- **Member Registration**: `http://127.0.0.1:8000/register/`
- **Member Login**: `http://127.0.0.1:8000/login/`
- **REST API Root**: `http://127.0.0.1:8000/api/`
- **Django Admin Panel**: `http://127.0.0.1:8000/admin/`

---

## ⚡ REST API Reference

### 1. Diet Plans
- `GET /api/diet-plans/`
- `GET /api/diet-plans/?category=Muscle+Gain`
- `GET /api/diet-plans/1/`

### 2. Membership Plans
- `GET /api/plans/`
- `GET /api/plans/1/`

### 3. Subscriptions
- `GET /api/subscriptions/`
- `POST /api/subscriptions/`
  ```json
  {
    "customer_name": "Sarah Connor",
    "customer_email": "sarah@example.com",
    "plan_name": "Standard Plan",
    "price": 1999.00,
    "billing_cycle": "Monthly",
    "payment_method": "UPI",
    "status": "Active"
  }
  ```

### 4. Stats
- `GET /api/stats/`
  ```json
  {
    "total_plans": 4,
    "active_subscriptions": 2,
    "expiring_soon": 1,
    "expired_subscriptions": 1,
    "total_revenue_inr": 8996.0
  }
  ```
