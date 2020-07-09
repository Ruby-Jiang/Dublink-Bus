from django.urls import path, include
from app import views as index_views
from . import views as route_views

urlpatterns = [
	path('api/routemaps/', route_views.RouteMapView.as_view(), name="routemap"),
	path('api/predict/', route_views.RoutePredictView.as_view(), name="routes"),
	path('api/find_route/', route_views.RouteFindView.as_view(), name="find_route")
]