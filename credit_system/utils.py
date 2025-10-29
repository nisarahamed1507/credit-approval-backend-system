from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from .models import Customer, Loan
from django.db.models import Sum, Q, Count


def calculate_credit_score(customer):
    """
    Calculate credit score for a customer based on:
    1. Past loans paid on time
    2. Number of loans taken in the past
    3. Loan activity in the current year
    4. Loan approved volume
    5. Critical rule: If sum of current loans > approved_limit, score = 0
    
    Returns: Credit score (0-100)
    """
    
    # Get all loans for the customer
    all_loans = Loan.objects.filter(customer=customer)
    
    if not all_loans.exists():
        return 50  # Default score for new customers
    
    # Critical Rule: Check if current loans exceed approved limit
    current_loans = all_loans.filter(end_date__gte=date.today())
    total_current_loan_amount = current_loans.aggregate(
        total=Sum('loan_amount')
    )['total'] or Decimal('0.00')
    
    if total_current_loan_amount > customer.approved_limit:
        return 0
    
    score = 0
    
    # Component 1: Past loans paid on time (40 points max)
    total_loans = all_loans.count()
    total_emis = all_loans.aggregate(total=Sum('tenure'))['total'] or 0
    total_emis_paid_on_time = all_loans.aggregate(
        total=Sum('emis_paid_on_time')
    )['total'] or 0
    
    if total_emis > 0:
        payment_ratio = total_emis_paid_on_time / total_emis
        score += int(payment_ratio * 40)
    
    # Component 2: Number of loans taken (20 points max)
    # Fewer loans is better (less risk)
    if total_loans == 0:
        score += 20
    elif total_loans == 1:
        score += 18
    elif total_loans == 2:
        score += 15
    elif total_loans == 3:
        score += 12
    elif total_loans <= 5:
        score += 8
    else:
        score += 5
    
    # Component 3: Loan activity in current year (20 points max)
    current_year = date.today().year
    current_year_loans = all_loans.filter(
        Q(start_date__year=current_year) | Q(end_date__year=current_year)
    ).count()
    
    if current_year_loans == 0:
        score += 20  # No recent loans = less risk
    elif current_year_loans == 1:
        score += 15
    elif current_year_loans == 2:
        score += 10
    else:
        score += 5
    
    # Component 4: Loan approved volume (20 points max)
    # Lower utilization of approved limit is better
    if customer.approved_limit > 0:
        utilization_ratio = total_current_loan_amount / customer.approved_limit
        if utilization_ratio <= Decimal('0.3'):
            score += 20
        elif utilization_ratio <= Decimal('0.5'):
            score += 15
        elif utilization_ratio <= Decimal('0.7'):
            score += 10
        else:
            score += 5
    
    # Ensure score is between 0 and 100
    return min(max(score, 0), 100)


def calculate_monthly_installment(loan_amount, interest_rate, tenure):
    """
    Calculate monthly installment using compound interest formula
    
    EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
    Where:
    P = Principal loan amount
    r = Monthly interest rate (annual rate / 12 / 100)
    n = Number of months (tenure)
    """
    if tenure <= 0:
        return Decimal('0.00')
    
    P = Decimal(str(loan_amount))
    annual_rate = Decimal(str(interest_rate))
    n = int(tenure)
    
    # Convert annual rate to monthly rate
    r = annual_rate / Decimal('12') / Decimal('100')
    
    if r == 0:
        # If interest rate is 0, EMI is just principal divided by tenure
        return P / Decimal(str(n))
    
    # Calculate (1 + r)^n
    power = (Decimal('1') + r) ** n
    
    # Calculate EMI
    emi = P * r * power / (power - Decimal('1'))
    
    # Round to 2 decimal places
    return emi.quantize(Decimal('0.01'))


def check_loan_eligibility(customer_id, loan_amount, interest_rate, tenure):
    """
    Check if a customer is eligible for a loan based on:
    1. Credit score
    2. Current EMI to salary ratio
    3. Interest rate corrections based on credit score
    
    Returns: dict with approval status, corrected interest rate, and monthly installment
    """
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return {
            'approval': False,
            'interest_rate': interest_rate,
            'corrected_interest_rate': interest_rate,
            'monthly_installment': Decimal('0.00'),
            'message': 'Customer not found'
        }
    
    # Calculate credit score
    credit_score = calculate_credit_score(customer)
    
    # Calculate monthly installment
    monthly_installment = calculate_monthly_installment(loan_amount, interest_rate, tenure)
    
    # Check EMI rule: Sum of all current EMIs should not exceed 50% of monthly salary
    current_loans = Loan.objects.filter(
        customer=customer,
        end_date__gte=date.today()
    )
    total_current_emi = current_loans.aggregate(
        total=Sum('monthly_repayment')
    )['total'] or Decimal('0.00')
    
    total_emi_with_new_loan = total_current_emi + monthly_installment
    max_allowed_emi = customer.monthly_salary * Decimal('0.5')
    
    if total_emi_with_new_loan > max_allowed_emi:
        return {
            'approval': False,
            'interest_rate': interest_rate,
            'corrected_interest_rate': interest_rate,
            'monthly_installment': monthly_installment,
            'message': 'Total EMI exceeds 50% of monthly salary'
        }
    
    # Determine approval and corrected interest rate based on credit score
    approval = False
    corrected_interest_rate = Decimal(str(interest_rate))
    message = ''
    
    if credit_score > 50:
        approval = True
    elif 30 < credit_score <= 50:
        if interest_rate >= 12:
            approval = True
        else:
            approval = True
            corrected_interest_rate = Decimal('12.00')
    elif 10 < credit_score <= 30:
        if interest_rate >= 16:
            approval = True
        else:
            approval = True
            corrected_interest_rate = Decimal('16.00')
    else:  # credit_score <= 10
        approval = False
        message = 'Credit score too low for loan approval'
    
    # Recalculate monthly installment if interest rate was corrected
    if corrected_interest_rate != Decimal(str(interest_rate)):
        monthly_installment = calculate_monthly_installment(
            loan_amount, 
            corrected_interest_rate, 
            tenure
        )
    
    return {
        'approval': approval,
        'interest_rate': Decimal(str(interest_rate)),
        'corrected_interest_rate': corrected_interest_rate,
        'monthly_installment': monthly_installment,
        'message': message,
        'credit_score': credit_score
    }


def get_current_emi_sum(customer):
    """
    Calculate the sum of all current EMIs for a customer
    """
    current_loans = Loan.objects.filter(
        customer=customer,
        end_date__gte=date.today()
    )
    total_emi = current_loans.aggregate(
        total=Sum('monthly_repayment')
    )['total'] or Decimal('0.00')
    
    return total_emi
