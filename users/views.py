from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from project_tracker.utils.response_handler import build_response
from rest_framework.permissions import AllowAny
import logging
logger = logging.getLogger('tracker_logger')



User = get_user_model()

class SendOTPView(generics.GenericAPIView):
    serializer_class = SendOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.debug("Entered SendOTPView.post()")
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.save()
            logger.info(f"OTP sent successfully to {data.get('email')}")
            return build_response(True, f"OTP sent successfully to {data.get('email')}")
        except ValidationError as e:
            logger.warning(f"Validation error: {e.detail}")
            return build_response(False, errors=e.detail)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return build_response(False, message="Failed to send OTP", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
class VerifyOTPView(generics.GenericAPIView):
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.debug("Entered VerifyOTPView.post()")
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.save()
            logger.info(f"OTP verified successfully for {data.get('email')}")
            return build_response(
                success=True,
                message="OTP verified successfully",
                data={"email_token": data.get("email_token")},
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as e:
            logger.warning(f"Validation error in VerifyOTPView: {e.detail}")
            return build_response(False, errors=e.detail)
        except Exception as e:
            logger.error(f"Unexpected error in VerifyOTPView: {e}", exc_info=True)
            return build_response(False, "Something went wrong while verifying OTP", status.HTTP_500_INTERNAL_SERVER_ERROR)
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.debug("Entered LoginView.post()")
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            logger.info(f"Login successful for {data.get('email')}")
            return build_response(True, "Login successful", data=data, status_code=status.HTTP_200_OK)
        except ValidationError as e:
            logger.warning(f"Validation error in LoginView: {e.detail}")
            return build_response(False, errors=e.detail)
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}", exc_info=True)
            return build_response(False, "Invalid credentials", status.HTTP_401_UNAUTHORIZED)

class ManagerRegisterView(generics.CreateAPIView):
    serializer_class = ManagerRegisterSerializer
    queryset = User.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        logger.debug("Entered ManagerRegisterView.create()")

        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            logger.info(f"Manager registered successfully: {user.email}")

            return build_response(
                success=True,
                message="Manager registered successfully",
                data={
                    "role": user.role,
                    "access": access_token,
                    "refresh": refresh_token
                },
                status_code=status.HTTP_201_CREATED
            )

        except ValidationError as e:
            logger.warning(f"Validation error during manager registration: {e.detail}")
            return build_response(False, errors=e.detail)

        except Exception as e:
            logger.error(f"Unexpected error in ManagerRegisterView: {e}", exc_info=True)
            return build_response(False, "Something went wrong during registration", status.HTTP_500_INTERNAL_SERVER_ERROR)