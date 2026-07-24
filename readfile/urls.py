from django.urls import path
from .views import read_input, cleanup_session, analyze_catalog, cluster_trend, keyword_search

app_name = "readfile"

urlpatterns = [
    path('upload/', read_input, name='upload'),
    path('cleanup/', cleanup_session, name='cleanup'),
    path('analyze/', analyze_catalog, name='analyze_catalog'),
    path('cluster-trend/', cluster_trend, name='cluster-trend'),
    path('keyword-search/', keyword_search, name='keyword-search'),
]
