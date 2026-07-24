from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('visualize/', include("readfile.urls")),
    path('api/', include('readfile.urls')),


    #пока не факт что понадобиться это для авторизации
    path('api/v1/', include('djoser.urls')),
    path('api/v1/', include('djoser.urls.authtoken')),

]
