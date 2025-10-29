from rest_framework import serializers
from .models import Customer, Loan


class CustomerRegistrationSerializer(serializers.Serializer):
    """Serializer for customer registration"""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=18)
    monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    phone_number = serializers.IntegerField()


class CustomerResponseSerializer(serializers.ModelSerializer):
    """Serializer for customer response"""
    monthly_income = serializers.DecimalField(
        source='monthly_salary', 
        max_digits=12, 
        decimal_places=2,
        read_only=True
    )
    name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['customer_id', 'name', 'age', 'monthly_income', 'approved_limit', 'phone_number']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class LoanEligibilityRequestSerializer(serializers.Serializer):
    """Serializer for loan eligibility check request"""
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    tenure = serializers.IntegerField(min_value=1)


class LoanEligibilityResponseSerializer(serializers.Serializer):
    """Serializer for loan eligibility check response"""
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=12, decimal_places=2)


class CreateLoanRequestSerializer(serializers.Serializer):
    """Serializer for create loan request"""
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    tenure = serializers.IntegerField(min_value=1)


class CreateLoanResponseSerializer(serializers.Serializer):
    """Serializer for create loan response"""
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_blank=True)
    monthly_installment = serializers.DecimalField(max_digits=12, decimal_places=2)


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Serializer for customer details in loan view"""
    id = serializers.IntegerField(source='customer_id')
    
    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'age']


class LoanDetailSerializer(serializers.ModelSerializer):
    """Serializer for viewing a single loan"""
    customer = CustomerDetailSerializer(read_only=True)
    monthly_installment = serializers.DecimalField(
        source='monthly_repayment',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Loan
        fields = ['loan_id', 'customer', 'loan_amount', 'interest_rate', 'monthly_installment', 'tenure']


class CustomerLoansSerializer(serializers.ModelSerializer):
    """Serializer for viewing all loans of a customer"""
    monthly_installment = serializers.DecimalField(
        source='monthly_repayment',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    repayments_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = Loan
        fields = ['loan_id', 'loan_amount', 'interest_rate', 'monthly_installment', 'repayments_left']
