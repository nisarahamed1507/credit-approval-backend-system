from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta

from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerResponseSerializer,
    LoanEligibilityRequestSerializer,
    LoanEligibilityResponseSerializer,
    CreateLoanRequestSerializer,
    CreateLoanResponseSerializer,
    LoanDetailSerializer,
    CustomerLoansSerializer
)
from .utils import (
    calculate_credit_score,
    calculate_monthly_installment,
    check_loan_eligibility
)


@api_view(['POST'])
def register_customer(request):
    """
    Register a new customer
    Calculate approved_limit = 36 * monthly_salary (rounded to nearest lakh)
    """
    serializer = CustomerRegistrationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Calculate approved limit: 36 * monthly_salary, rounded to nearest lakh
    monthly_income = Decimal(str(data['monthly_income']))
    approved_limit = monthly_income * 36
    
    # Round to nearest lakh (100,000)
    lakh = Decimal('100000')
    approved_limit = (approved_limit / lakh).quantize(Decimal('1')) * lakh
    
    # Create customer
    with transaction.atomic():
        # Get the next customer_id
        last_customer = Customer.objects.order_by('-customer_id').first()
        next_id = (last_customer.customer_id + 1) if last_customer else 1
        
        customer = Customer.objects.create(
            customer_id=next_id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            phone_number=data['phone_number'],
            monthly_salary=monthly_income,
            approved_limit=approved_limit,
            current_debt=Decimal('0.00')
        )
    
    # Return response
    response_serializer = CustomerResponseSerializer(customer)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def check_eligibility(request):
    """
    Check loan eligibility for a customer
    """
    serializer = LoanEligibilityRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Check if customer exists
    try:
        customer = Customer.objects.get(customer_id=data['customer_id'])
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check eligibility
    eligibility_result = check_loan_eligibility(
        customer_id=data['customer_id'],
        loan_amount=data['loan_amount'],
        interest_rate=data['interest_rate'],
        tenure=data['tenure']
    )
    
    # Prepare response
    response_data = {
        'customer_id': data['customer_id'],
        'approval': eligibility_result['approval'],
        'interest_rate': float(eligibility_result['interest_rate']),
        'corrected_interest_rate': float(eligibility_result['corrected_interest_rate']),
        'tenure': data['tenure'],
        'monthly_installment': float(eligibility_result['monthly_installment'])
    }
    
    response_serializer = LoanEligibilityResponseSerializer(data=response_data)
    if response_serializer.is_valid():
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def create_loan(request):
    """
    Create a new loan if eligible
    """
    serializer = CreateLoanRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Check eligibility
    eligibility_result = check_loan_eligibility(
        customer_id=data['customer_id'],
        loan_amount=data['loan_amount'],
        interest_rate=data['interest_rate'],
        tenure=data['tenure']
    )
    
    if not eligibility_result['approval']:
        response_data = {
            'loan_id': None,
            'customer_id': data['customer_id'],
            'loan_approved': False,
            'message': eligibility_result.get('message', 'Loan not approved based on credit criteria'),
            'monthly_installment': float(eligibility_result['monthly_installment'])
        }
        response_serializer = CreateLoanResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Loan is approved, create it
    try:
        customer = Customer.objects.get(customer_id=data['customer_id'])
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Use corrected interest rate
    final_interest_rate = eligibility_result['corrected_interest_rate']
    monthly_installment = eligibility_result['monthly_installment']
    
    # Calculate start and end dates
    start_date = date.today()
    end_date = start_date + relativedelta(months=data['tenure'])
    
    with transaction.atomic():
        # Get the next loan_id
        last_loan = Loan.objects.order_by('-loan_id').first()
        next_loan_id = (last_loan.loan_id + 1) if last_loan else 1
        
        loan = Loan.objects.create(
            loan_id=next_loan_id,
            customer=customer,
            loan_amount=data['loan_amount'],
            tenure=data['tenure'],
            interest_rate=final_interest_rate,
            monthly_repayment=monthly_installment,
            emis_paid_on_time=0,
            start_date=start_date,
            end_date=end_date
        )
    
    response_data = {
        'loan_id': loan.loan_id,
        'customer_id': data['customer_id'],
        'loan_approved': True,
        'message': 'Loan approved successfully',
        'monthly_installment': float(monthly_installment)
    }
    
    response_serializer = CreateLoanResponseSerializer(data=response_data)
    if response_serializer.is_valid():
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def view_loan(request, loan_id):
    """
    View details of a specific loan
    """
    try:
        loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response(
            {'error': 'Loan not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = LoanDetailSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def view_loans_by_customer(request, customer_id):
    """
    View all current loans for a specific customer
    """
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all current/active loans (can include both current and past loans)
    # Based on the requirement, we'll show all loans for the customer
    loans = Loan.objects.filter(customer=customer).order_by('-start_date')
    
    serializer = CustomerLoansSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
