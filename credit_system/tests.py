from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from credit_system.models import Customer, Loan
from credit_system.utils import (
    calculate_credit_score,
    calculate_monthly_installment,
    check_loan_eligibility
)


class CustomerModelTest(TestCase):
    """Test cases for Customer model"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="John",
            last_name="Doe",
            age=30,
            phone_number=9876543210,
            monthly_salary=Decimal('50000.00'),
            approved_limit=Decimal('1800000.00'),
            current_debt=Decimal('0.00')
        )
    
    def test_customer_creation(self):
        """Test customer is created correctly"""
        self.assertEqual(self.customer.first_name, "John")
        self.assertEqual(self.customer.last_name, "Doe")
        self.assertEqual(self.customer.monthly_salary, Decimal('50000.00'))
    
    def test_customer_string_representation(self):
        """Test customer string representation"""
        expected = f"John Doe (ID: 1)"
        self.assertEqual(str(self.customer), expected)


class LoanModelTest(TestCase):
    """Test cases for Loan model"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Jane",
            last_name="Smith",
            age=28,
            phone_number=9123456789,
            monthly_salary=Decimal('75000.00'),
            approved_limit=Decimal('2700000.00'),
            current_debt=Decimal('100000.00')
        )
        
        self.loan = Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('300000.00'),
            tenure=24,
            interest_rate=Decimal('12.00'),
            monthly_repayment=Decimal('14122.04'),
            emis_paid_on_time=20,
            start_date=date.today() - relativedelta(months=4),
            end_date=date.today() + relativedelta(months=20)
        )
    
    def test_loan_creation(self):
        """Test loan is created correctly"""
        self.assertEqual(self.loan.customer, self.customer)
        self.assertEqual(self.loan.loan_amount, Decimal('300000.00'))
        self.assertEqual(self.loan.tenure, 24)
    
    def test_loan_string_representation(self):
        """Test loan string representation"""
        expected = f"Loan 1 - Customer 1"
        self.assertEqual(str(self.loan), expected)


class CreditScoreCalculationTest(TestCase):
    """Test cases for credit score calculation"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="User",
            age=35,
            phone_number=9999999999,
            monthly_salary=Decimal('100000.00'),
            approved_limit=Decimal('3600000.00'),
            current_debt=Decimal('0.00')
        )
    
    def test_new_customer_default_score(self):
        """Test that new customers with no loans get default score of 50"""
        score = calculate_credit_score(self.customer)
        self.assertEqual(score, 50)
    
    def test_credit_score_zero_when_debt_exceeds_limit(self):
        """Test critical rule: score = 0 when current loans > approved_limit"""
        # Create a current loan exceeding approved limit
        Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('4000000.00'),  # Exceeds 3,600,000 limit
            tenure=36,
            interest_rate=Decimal('15.00'),
            monthly_repayment=Decimal('150000.00'),
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date.today() + relativedelta(months=36)
        )
        
        score = calculate_credit_score(self.customer)
        self.assertEqual(score, 0)
    
    def test_credit_score_with_good_payment_history(self):
        """Test credit score with 100% on-time payments"""
        # Create a loan with all EMIs paid on time
        Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('500000.00'),
            tenure=12,
            interest_rate=Decimal('12.00'),
            monthly_repayment=Decimal('44000.00'),
            emis_paid_on_time=12,  # All 12 EMIs paid on time
            start_date=date.today() - relativedelta(months=12),
            end_date=date.today()
        )
        
        score = calculate_credit_score(self.customer)
        self.assertGreater(score, 50)  # Should be higher than default
        self.assertLessEqual(score, 100)
    
    def test_credit_score_range(self):
        """Test that credit score is always between 0 and 100"""
        # Create multiple loans with varying characteristics
        for i in range(3):
            Loan.objects.create(
                loan_id=i+1,
                customer=self.customer,
                loan_amount=Decimal('200000.00'),
                tenure=12,
                interest_rate=Decimal('10.00'),
                monthly_repayment=Decimal('17000.00'),
                emis_paid_on_time=10,
                start_date=date.today() - relativedelta(months=6),
                end_date=date.today() + relativedelta(months=6)
            )
        
        score = calculate_credit_score(self.customer)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class MonthlyInstallmentCalculationTest(TestCase):
    """Test cases for compound interest EMI calculation"""
    
    def test_compound_interest_calculation(self):
        """Test EMI calculation using compound interest formula"""
        loan_amount = 100000
        interest_rate = 12
        tenure = 12
        
        emi = calculate_monthly_installment(loan_amount, interest_rate, tenure)
        
        # Expected EMI for 100,000 at 12% for 12 months is approximately 8884.88
        self.assertAlmostEqual(float(emi), 8884.88, places=2)
    
    def test_zero_interest_rate(self):
        """Test EMI calculation with 0% interest rate"""
        loan_amount = 120000
        interest_rate = 0
        tenure = 12
        
        emi = calculate_monthly_installment(loan_amount, interest_rate, tenure)
        
        # With 0% interest, EMI should be principal / tenure
        expected = Decimal('10000.00')
        self.assertEqual(emi, expected)
    
    def test_different_tenures(self):
        """Test EMI calculation with different tenures"""
        loan_amount = 200000
        interest_rate = 10
        
        emi_12 = calculate_monthly_installment(loan_amount, interest_rate, 12)
        emi_24 = calculate_monthly_installment(loan_amount, interest_rate, 24)
        emi_36 = calculate_monthly_installment(loan_amount, interest_rate, 36)
        
        # Longer tenure should result in lower EMI
        self.assertGreater(emi_12, emi_24)
        self.assertGreater(emi_24, emi_36)
    
    def test_zero_tenure(self):
        """Test EMI calculation with zero tenure returns 0"""
        emi = calculate_monthly_installment(100000, 12, 0)
        self.assertEqual(emi, Decimal('0.00'))


class LoanEligibilityTest(TestCase):
    """Test cases for loan eligibility checking"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Eligible",
            last_name="Customer",
            age=40,
            phone_number=8888888888,
            monthly_salary=Decimal('100000.00'),
            approved_limit=Decimal('3600000.00'),
            current_debt=Decimal('0.00')
        )
    
    def test_high_credit_score_approval(self):
        """Test approval with credit score > 50"""
        # Create good payment history
        Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('200000.00'),
            tenure=12,
            interest_rate=Decimal('10.00'),
            monthly_repayment=Decimal('17583.00'),
            emis_paid_on_time=12,
            start_date=date.today() - relativedelta(months=12),
            end_date=date.today()
        )
        
        result = check_loan_eligibility(1, 300000, 10, 24)
        self.assertTrue(result['approval'])
    
    def test_emi_exceeds_50_percent_salary(self):
        """Test rejection when total EMI > 50% of monthly salary"""
        # Create existing loan with high EMI
        Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('1000000.00'),
            tenure=12,
            interest_rate=Decimal('12.00'),
            monthly_repayment=Decimal('88849.00'),  # High EMI
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date.today() + relativedelta(months=12)
        )
        
        # Try to add another loan
        result = check_loan_eligibility(1, 500000, 12, 24)
        self.assertFalse(result['approval'])
        self.assertIn('50%', result['message'])
    
    def test_interest_rate_correction_for_medium_credit(self):
        """Test interest rate correction for credit score 30-50"""
        # Request loan with low interest rate
        result = check_loan_eligibility(1, 200000, 8, 12)
        
        # Should correct interest rate to minimum 12% for this slab
        if 30 < result.get('credit_score', 0) <= 50:
            self.assertEqual(result['corrected_interest_rate'], Decimal('12.00'))
    
    def test_customer_not_found(self):
        """Test handling of non-existent customer"""
        result = check_loan_eligibility(9999, 100000, 10, 12)
        self.assertFalse(result['approval'])
        self.assertIn('not found', result['message'].lower())


class RegisterCustomerAPITest(APITestCase):
    """Test cases for /register endpoint"""
    
    def test_register_customer_success(self):
        """Test successful customer registration"""
        url = reverse('register')
        data = {
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'age': 28,
            'monthly_income': 50000,
            'phone_number': 9876543210
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Alice Johnson')
        self.assertEqual(response.data['age'], 28)
        
        # Check approved_limit calculation: 36 * 50000 = 1,800,000
        self.assertEqual(Decimal(response.data['approved_limit']), Decimal('1800000.00'))
    
    def test_register_customer_approved_limit_calculation(self):
        """Test approved_limit = 36 * monthly_salary rounded to lakh"""
        url = reverse('register')
        data = {
            'first_name': 'Bob',
            'last_name': 'Smith',
            'age': 35,
            'monthly_income': 75000,
            'phone_number': 9123456789
        }
        
        response = self.client.post(url, data, format='json')
        
        # 75000 * 36 = 2,700,000
        self.assertEqual(Decimal(response.data['approved_limit']), Decimal('2700000.00'))
    
    def test_register_customer_missing_fields(self):
        """Test registration with missing required fields"""
        url = reverse('register')
        data = {
            'first_name': 'Incomplete',
            # Missing other required fields
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CheckEligibilityAPITest(APITestCase):
    """Test cases for /check-eligibility endpoint"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="Customer",
            age=30,
            phone_number=9999999999,
            monthly_salary=Decimal('100000.00'),
            approved_limit=Decimal('3600000.00'),
            current_debt=Decimal('0.00')
        )
    
    def test_check_eligibility_success(self):
        """Test successful eligibility check"""
        url = reverse('check-eligibility')
        data = {
            'customer_id': 1,
            'loan_amount': 200000,
            'interest_rate': 12,
            'tenure': 24
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('approval', response.data)
        self.assertIn('monthly_installment', response.data)
        self.assertIn('corrected_interest_rate', response.data)
    
    def test_check_eligibility_invalid_customer(self):
        """Test eligibility check with invalid customer ID"""
        url = reverse('check-eligibility')
        data = {
            'customer_id': 9999,
            'loan_amount': 100000,
            'interest_rate': 10,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CreateLoanAPITest(APITestCase):
    """Test cases for /create-loan endpoint"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Loan",
            last_name="Taker",
            age=32,
            phone_number=8888888888,
            monthly_salary=Decimal('150000.00'),
            approved_limit=Decimal('5400000.00'),
            current_debt=Decimal('0.00')
        )
        
        # Create good credit history
        Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('300000.00'),
            tenure=12,
            interest_rate=Decimal('10.00'),
            monthly_repayment=Decimal('26375.00'),
            emis_paid_on_time=12,
            start_date=date.today() - relativedelta(months=12),
            end_date=date.today()
        )
    
    def test_create_loan_success(self):
        """Test successful loan creation"""
        url = reverse('create-loan')
        data = {
            'customer_id': 1,
            'loan_amount': 200000,
            'interest_rate': 12,
            'tenure': 24
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        if response.data['loan_approved']:
            self.assertIsNotNone(response.data['loan_id'])
            self.assertGreater(response.data['loan_id'], 0)
    
    def test_create_loan_rejection(self):
        """Test loan rejection with appropriate message"""
        # Create customer with very low credit score scenario
        poor_customer = Customer.objects.create(
            customer_id=2,
            first_name="Poor",
            last_name="Credit",
            age=25,
            phone_number=7777777777,
            monthly_salary=Decimal('30000.00'),
            approved_limit=Decimal('1080000.00'),
            current_debt=Decimal('0.00')
        )
        
        # Create loan that exceeds approved limit
        Loan.objects.create(
            loan_id=2,
            customer=poor_customer,
            loan_amount=Decimal('1500000.00'),
            tenure=36,
            interest_rate=Decimal('18.00'),
            monthly_repayment=Decimal('60000.00'),
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date.today() + relativedelta(months=36)
        )
        
        url = reverse('create-loan')
        data = {
            'customer_id': 2,
            'loan_amount': 100000,
            'interest_rate': 10,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['loan_approved'])
        self.assertIsNone(response.data['loan_id'])
        self.assertIsNotNone(response.data['message'])


class ViewLoanAPITest(APITestCase):
    """Test cases for /view-loan/<loan_id> endpoint"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="View",
            last_name="Test",
            age=30,
            phone_number=9999999999,
            monthly_salary=Decimal('80000.00'),
            approved_limit=Decimal('2880000.00'),
            current_debt=Decimal('0.00')
        )
        
        self.loan = Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('300000.00'),
            tenure=24,
            interest_rate=Decimal('12.00'),
            monthly_repayment=Decimal('14122.04'),
            emis_paid_on_time=20,
            start_date=date.today() - relativedelta(months=4),
            end_date=date.today() + relativedelta(months=20)
        )
    
    def test_view_loan_success(self):
        """Test successful loan view with nested customer object"""
        url = reverse('view-loan', kwargs={'loan_id': 1})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['loan_id'], 1)
        
        # Check nested customer object
        self.assertIn('customer', response.data)
        self.assertEqual(response.data['customer']['id'], 1)
        self.assertEqual(response.data['customer']['first_name'], 'View')
        self.assertEqual(response.data['customer']['last_name'], 'Test')
        self.assertIn('phone_number', response.data['customer'])
        self.assertIn('age', response.data['customer'])
    
    def test_view_loan_not_found(self):
        """Test viewing non-existent loan"""
        url = reverse('view-loan', kwargs={'loan_id': 9999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ViewCustomerLoansAPITest(APITestCase):
    """Test cases for /view-loans/<customer_id> endpoint"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Multi",
            last_name="Loan",
            age=35,
            phone_number=8888888888,
            monthly_salary=Decimal('120000.00'),
            approved_limit=Decimal('4320000.00'),
            current_debt=Decimal('500000.00')
        )
        
        # Create multiple loans
        self.loan1 = Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=Decimal('200000.00'),
            tenure=24,
            interest_rate=Decimal('10.00'),
            monthly_repayment=Decimal('9205.00'),
            emis_paid_on_time=12,
            start_date=date.today() - relativedelta(months=12),
            end_date=date.today() + relativedelta(months=12)
        )
        
        self.loan2 = Loan.objects.create(
            loan_id=2,
            customer=self.customer,
            loan_amount=Decimal('300000.00'),
            tenure=36,
            interest_rate=Decimal('12.00'),
            monthly_repayment=Decimal('9956.00'),
            emis_paid_on_time=24,
            start_date=date.today() - relativedelta(months=24),
            end_date=date.today() + relativedelta(months=12)
        )
    
    def test_view_customer_loans_success(self):
        """Test viewing all loans for a customer"""
        url = reverse('view-loans', kwargs={'customer_id': 1})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)
        
        # Check required fields in each loan
        for loan in response.data:
            self.assertIn('loan_id', loan)
            self.assertIn('loan_amount', loan)
            self.assertIn('interest_rate', loan)
            self.assertIn('monthly_installment', loan)
            self.assertIn('repayments_left', loan)
    
    def test_view_customer_loans_not_found(self):
        """Test viewing loans for non-existent customer"""
        url = reverse('view-loans', kwargs={'customer_id': 9999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_view_customer_no_loans(self):
        """Test viewing loans for customer with no loans"""
        customer_no_loans = Customer.objects.create(
            customer_id=2,
            first_name="No",
            last_name="Loans",
            age=25,
            phone_number=7777777777,
            monthly_salary=Decimal('50000.00'),
            approved_limit=Decimal('1800000.00'),
            current_debt=Decimal('0.00')
        )
        
        url = reverse('view-loans', kwargs={'customer_id': 2})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 0)
