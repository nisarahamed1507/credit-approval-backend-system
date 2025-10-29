from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Customer(models.Model):
    """Customer model to store customer information"""
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(validators=[MinValueValidator(18)])
    phone_number = models.BigIntegerField()
    monthly_salary = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    approved_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    current_debt = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['phone_number']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.customer_id})"


class Loan(models.Model):
    """Loan model to store loan information"""
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='loans'
    )
    loan_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tenure = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Loan tenure in months"
    )
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monthly_repayment = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="EMI amount"
    )
    emis_paid_on_time = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    start_date = models.DateField()
    end_date = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        indexes = [
            models.Index(fields=['customer', 'end_date']),
            models.Index(fields=['start_date']),
        ]

    def __str__(self):
        return f"Loan {self.loan_id} - Customer {self.customer.customer_id}"
    
    @property
    def is_active(self):
        """Check if loan is currently active"""
        from datetime import date
        return self.end_date >= date.today()
    
    @property
    def repayments_left(self):
        """Calculate remaining EMIs"""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        if not self.is_active:
            return 0
        
        # Calculate months between today and end date
        today = date.today()
        months_left = (self.end_date.year - today.year) * 12 + (self.end_date.month - today.month)
        return max(0, months_left)
