from django.core.mail import send_mail
from rest_framework import serializers
from django.contrib.auth import get_user_model
from project_tracker import settings
from .models import EmailOTP
from django.core import signing
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
import logging
logger = logging.getLogger('tracker_logger')


User = get_user_model()



class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not value:
            logger.warning("Validation failed: empty email field.")
            raise serializers.ValidationError("Email is required.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        try:
            otp = EmailOTP.generate_otp()
            EmailOTP.objects.create(email=email, otp=otp)
            send_mail(
                subject='Login OTP',
               message = (
                f"Dear User,\n\n"
                f"Your One-Time Password (OTP) for verification is: {otp}\n\n"
                f"This OTP is valid for the next 5 minutes. "
                f"Please do not share this code with anyone.\n\n"
                f"Best regards,\n"
                f"Project Tracker Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"OTP generated and sent to {email}")
            return {"email": email}
        except Exception as e:
            logger.error(f"Failed to send OTP to {email}: {e}", exc_info=True)
            raise serializers.ValidationError("Failed to send OTP. Please try again later.")
    
class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data.get('email')
        otp = data.get('otp')
        logger.debug(f"Verifying OTP for email: {email}")

        otp_record = EmailOTP.objects.filter(email=email, otp=otp).order_by('-created_at').first()

        if not otp_record:
            logger.warning(f"Invalid OTP attempt for {email}")
            raise serializers.ValidationError({"otp": "Invalid OTP"})

        if not otp_record.is_valid():
            logger.warning(f"Expired or used OTP for {email}")
            raise serializers.ValidationError({"otp": "OTP expired or already used"})

        otp_record.mark_used()
        logger.info(f"OTP marked as used for {email}")

        token = signing.dumps({'email': email})
        data['email_token'] = token
        return data

    def create(self, validated_data):
        return {'email_token': validated_data['email_token'], 'email': validated_data['email']}

class ManagerRegisterSerializer(serializers.ModelSerializer):
    email_token = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email_token', 'first_name', 'last_name', 'password', 'confirm_password']

    def validate(self, data):
        logger.debug("Validating ManagerRegisterSerializer data")

        password = data.get('password')
        confirm_password = data.get('confirm_password')

        if password != confirm_password:
            logger.warning("Password mismatch during registration")
            raise serializers.ValidationError("Passwords do not match")

        email_token = data.get('email_token')
        try:
            payload = signing.loads(email_token, max_age=settings.EMAIL_TOKEN_MAX_AGE)
            email = payload.get('email')
            if not email:
                logger.warning("Email not found in token payload")
                raise serializers.ValidationError("Invalid email token data.")
        except signing.BadSignature:
            logger.warning("Invalid or tampered email token")
            raise serializers.ValidationError("Invalid or tampered email token.")
        except signing.SignatureExpired:
            logger.warning("Expired email token")
            raise serializers.ValidationError("Email token has expired.")
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
            raise serializers.ValidationError("Unable to validate email token.")

        # Attach email to validated data
        data['email'] = email
        return data

    def create(self, validated_data):
        logger.debug("Creating manager user")

        password = validated_data.pop('password')
        validated_data.pop('confirm_password', None)
        validated_data.pop('email_token', None)
        email = validated_data.pop('email')

        # Check existence efficiently
        if User.objects.filter(email=email).only('id').exists():
            logger.warning(f"User with email {email} already exists")
            raise serializers.ValidationError("User with this email already exists.")

        role = 'manager'
        user = User.objects.create(email=email, role=role, **validated_data)
        user.set_password(password)
        user.save()

        logger.info(f"Manager account created successfully for {email}")
        return user
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            logger.warning("Missing email or password in login request")
            raise serializers.ValidationError("Both email and password are required.")
        user = authenticate(email=email, password=password)
        if not user:
            logger.warning(f"Invalid credentials for email: {email}")
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            logger.warning(f"Inactive account login attempt for {email}")
            raise serializers.ValidationError("This account is inactive.")
        refresh = RefreshToken.for_user(user)
        logger.info(f"User logged in successfully: {email}")
        return {"email": user.email, "role": user.role, "access": str(refresh.access_token), "refresh": str(refresh)}
    