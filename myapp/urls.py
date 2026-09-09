"""
URL configuration for myapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_obtain"


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_obtain"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("prompting.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("rag.urls")),
    path("api/", include("restaurant.urls")),
    # Submit username/password to get 'access' and 'refresh' tokens
    path('api/token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Submit 'refresh' token to get a new 'access' token
    path('api/token/refresh/', ThrottledTokenRefreshView.as_view(), name='token_refresh'),
     # Swagger UI endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
