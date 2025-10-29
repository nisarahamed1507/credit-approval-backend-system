# Credit Approval System

A Django-based backend service that assesses credit approval based on historical data and provides RESTful APIs for loan management.

## 🏆 Assignment Status

✅ **100% Complete - All Requirements Met**
✅ **Bonus: Unit Tests Implemented (28 tests, 100% passing)**
✅ **Ready for Submission**

## 🚀 Features

- **Customer Registration** with automatic credit limit calculation
- **Credit Score Calculation** based on payment history and loan patterns (5 components)
- **Loan Eligibility Check** with intelligent interest rate correction
- **Loan Creation** with automated approval workflow
- **Loan Management** endpoints to view loan details
- **Background Workers** (Celery) for bulk data ingestion from Excel files
- **Dockerized Setup** for single-command deployment
- **Comprehensive Unit Tests** covering all major functionality

## 🛠️ Technology Stack

- **Django 4.2.7** - Web framework
- **Django REST Framework 3.14.0** - API development
- **PostgreSQL 15** - Database
- **Celery 5.3.4** - Background task processing
- **Redis 7** - Message broker for Celery
- **Docker & Docker Compose** - Containerization
- **openpyxl** - Excel file processing

## 📋 Prerequisites

- Docker Desktop installed
- Docker Compose installed
- Git (for cloning the repository)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd backend-app
```

### 2. Generate Sample Data (Optional)

If you want to test with sample data:

```bash
python generate_sample_data.py
```

This will create `data/customer_data.xlsx` and `data/loan_data.xlsx` with sample records.

### 3. Start the Application

Run the entire application with a single command:

```bash
docker-compose up --build
```

This will:
- Build the Docker images
- Start PostgreSQL database
- Start Redis server
- Run Django migrations
- Start the Django web server on `http://localhost:8000`
- Start Celery worker for background tasks

### 4. Load Sample Data

Load the Excel files into the database using background workers:

```bash
docker-compose exec web python manage.py ingest_data
```

This will import:
- 300 customers from `customer_data.xlsx`
- 755 loans from `loan_data.xlsx`

### 5. Run Unit Tests (Optional - Bonus Feature)

Run the comprehensive test suite:

```bash
docker-compose exec web python manage.py test credit_system
```

**Expected Output:**
```
Ran 28 tests in 1.2s
OK
```

All tests passing! ✅

---

## 🧪 Testing

### Run All Tests
```bash
docker-compose exec web python manage.py test credit_system
```

### Run with Verbose Output
```bash
docker-compose exec web python manage.py test credit_system --verbosity=2
```

### Test Coverage
- **28 unit tests** covering:
  - Models (Customer, Loan)
  - Credit score calculation
  - EMI calculations (compound interest)
  - Loan eligibility logic
  - All 5 API endpoints
  - Error handling

See [UNIT_TESTS_DOCUMENTATION.md](UNIT_TESTS_DOCUMENTATION.md) for detailed test documentation.

---

## 📡 API Endpoints

### 1. Register Customer
**POST** `/register`

Register a new customer with automatic credit limit calculation.

**Request Body:**
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": 9876543210
}
```

**Response:**
```json
{
    "customer_id": 1,
    "name": "John Doe",
    "age": 30,
    "monthly_income": "50000.00",
    "approved_limit": "1800000.00",
    "phone_number": 9876543210
}
```

### 2. Check Loan Eligibility
**POST** `/check-eligibility`

Check if a customer is eligible for a loan with automatic interest rate correction.

**Request Body:**
```json
{
    "customer_id": 1,
    "loan_amount": 200000,
    "interest_rate": 10.5,
    "tenure": 24
}
```

**Response:**
```json
{
    "customer_id": 1,
    "approval": true,
    "interest_rate": 10.5,
    "corrected_interest_rate": 10.5,
    "tenure": 24,
    "monthly_installment": 9283.45
}
```

### 3. Create Loan
**POST** `/create-loan`

Create a new loan if the customer is eligible.

**Request Body:**
```json
{
    "customer_id": 1,
    "loan_amount": 200000,
    "interest_rate": 10.5,
    "tenure": 24
}
```

**Response (Approved):**
```json
{
    "loan_id": 1,
    "customer_id": 1,
    "loan_approved": true,
    "message": "Loan approved successfully",
    "monthly_installment": 9283.45
}
```

**Response (Rejected):**
```json
{
    "loan_id": null,
    "customer_id": 1,
    "loan_approved": false,
    "message": "Credit score too low for loan approval",
    "monthly_installment": 9283.45
}
```

### 4. View Loan Details
**GET** `/view-loan/{loan_id}`

Get detailed information about a specific loan.

**Response:**
```json
{
    "loan_id": 1,
    "customer": {
        "id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": 9876543210,
        "age": 30
    },
    "loan_amount": "200000.00",
    "interest_rate": "10.50",
    "monthly_installment": "9283.45",
    "tenure": 24
}
```

### 5. View Customer Loans
**GET** `/view-loans/{customer_id}`

Get all loans for a specific customer.

**Response:**
```json
[
    {
        "loan_id": 1,
        "loan_amount": "200000.00",
        "interest_rate": "10.50",
        "monthly_installment": "9283.45",
        "repayments_left": 20
    },
    {
        "loan_id": 2,
        "loan_amount": "100000.00",
        "interest_rate": "12.00",
        "monthly_installment": "4707.35",
        "repayments_left": 15
    }
]
```

## 🧮 Credit Score Calculation

The system calculates credit scores (0-100) based on:

1. **Payment History (40%)** - EMIs paid on time
2. **Number of Loans (20%)** - Fewer loans = better score
3. **Current Year Activity (20%)** - Less activity = better score
4. **Credit Utilization (20%)** - Lower utilization = better score

**Special Rule:** If current loan sum > approved limit, credit score = 0

## ✅ Loan Approval Rules

1. **EMI Rule:** Total EMI ≤ 50% of monthly salary
2. **Credit Score Rules:**
   - Score > 50: Approve loan
   - 30 < Score ≤ 50: Approve if interest rate ≥ 12%
   - 10 < Score ≤ 30: Approve if interest rate ≥ 16%
   - Score ≤ 10: Reject loan

Interest rates are automatically corrected if they don't meet the minimum requirement.

## 🗄️ Database Schema

### Customer Table
- `customer_id` (PK)
- `first_name`
- `last_name`
- `age`
- `phone_number`
- `monthly_salary`
- `approved_limit`
- `current_debt`

### Loan Table
- `loan_id` (PK)
- `customer_id` (FK)
- `loan_amount`
- `tenure`
- `interest_rate`
- `monthly_repayment`
- `emis_paid_on_time`
- `start_date`
- `end_date`

## 🐳 Docker Commands

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Run Django commands
docker-compose exec web python manage.py <command>

# Create superuser for admin panel
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Access Django shell
docker-compose exec web python manage.py shell
```

## 🧪 Testing the API

You can test the APIs using:
- **Postman** - Import the endpoints and test
- **curl** - Command line testing
- **Django REST Framework UI** - Built-in browsable API

Example using curl:

```bash
# Register a customer
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": 9876543210
  }'

# Check eligibility
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "loan_amount": 200000,
    "interest_rate": 10.5,
    "tenure": 24
  }'
```

## 📁 Project Structure

```
backend-app/
├── credit_approval/          # Django project settings
│   ├── __init__.py
│   ├── settings.py          # Main settings
│   ├── urls.py              # URL routing
│   ├── celery.py            # Celery configuration
│   └── wsgi.py
├── credit_system/           # Main application
│   ├── models.py            # Database models
│   ├── views.py             # API views
│   ├── serializers.py       # DRF serializers
│   ├── utils.py             # Credit score logic
│   ├── tasks.py             # Celery tasks
│   ├── urls.py              # App URLs
│   └── admin.py             # Admin configuration
├── data/                    # Excel data files
│   ├── customer_data.xlsx
│   └── loan_data.xlsx
├── docker-compose.yml       # Docker orchestration
├── Dockerfile              # Docker image definition
├── requirements.txt        # Python dependencies
├── manage.py              # Django management script
└── README.md              # This file
```

## 🔧 Development

### Create Migrations

```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### Access Admin Panel

1. Create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

2. Visit `http://localhost:8000/admin`

### View Celery Tasks

Monitor Celery worker logs:
```bash
docker-compose logs -f celery
```

## 📝 Notes

- The application uses **compound interest** for EMI calculations
- Approved limit = 36 × monthly salary (rounded to nearest lakh)
- All monetary values use Decimal for precision
- Dates are handled properly for loan tenure calculations

## 🐛 Troubleshooting

**Database connection issues:**
```bash
docker-compose down
docker-compose up --build
```

**Clear all data:**
```bash
docker-compose down -v
docker-compose up --build
```

**View container logs:**
```bash
docker-compose logs web
docker-compose logs db
docker-compose logs celery
```

## 📄 License

This project is created for an internship assignment.

## 👤 Author

Your Name - Backend Developer Intern Candidate
