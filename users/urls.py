from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import *

urlpatterns = [
    # ---------------------- OTP VERIFICATION ----------------------
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),

    # ---------------------- USER REGISTRATION ---------------------
    path('register/manager/', ManagerRegisterView.as_view(), name='register-manager'),

    # ---------------------- AUTHENTICATION ------------------------
    path('login/', LoginView.as_view(), name='user_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
