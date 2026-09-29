# sync/api_urls.py
from django.urls import path
from . import api

urlpatterns = [
    path("ping/", api.PingView.as_view()),          # HEAD or GET
    path("upload/", api.UploadView.as_view()),      # POST
    path("pair/", api.PairView.as_view()),
    path("download/", api.DownloadView.as_view()),  # GET ?catalog_version=N
]