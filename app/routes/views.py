from django.shortcuts import render
from rest_framework import generics
from rest_framework.views import APIView
from . import forms as route_forms
import os
import os.path
import json
from rest_framework import status
from rest_framework.response import Response
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
import pandas as pd
import joblib 
from predict_route import get_prediction
import sys
import requests
from dir_api_resp import process_resp


class RouteMapView(generics.RetrieveAPIView):
    def get(self, request):
        lineid = request.query_params.get('lineid')
        start_stop = int(request.query_params.get('start'))
        end_stop = int(request.query_params.get('end'))
        routeID = request.query_params.get('routeid')
        url = staticfiles_storage.url('json/routemaps/{}_routemap.json'.format(lineid))
        with open(settings.BASE_DIR + url) as f:
                linemap = json.loads(f.read())
        routemap = linemap[routeID]
        on_route = False
        data = []

        for stop in routemap:
            try:
                if stop["id"] == start_stop:
                    on_route = True
                if on_route:
                    data.append(stop) 
                if stop["id"] == end_stop:
                    on_route = False
            except:
                pass

        return Response(data, status=status.HTTP_200_OK)


class RoutePredictView(generics.RetrieveAPIView):

    def get(self, request):

        #data_dir = settings.BASE_DIR + staticfiles_storage.url('model_integration')
        data_dir = 'C:\\Users\\rbyrn\\Desktop\\dublinbus\\app\\model_integration'
        lineid = request.query_params.get('lineid')
        routeid = request.query_params.get('routeid')
        start_stop = request.query_params.get('start_stop')
        end_stop = request.query_params.get('end_stop')
        try:
            model_pickle = os.path.join(data_dir, 'pickle_file/XG_{}.pkl'.format(lineid))
            model = joblib.load(open(model_pickle, 'rb'))
        except:
            return Response("ERROR: incorrect file structure", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        direction = 0
        with open(os.path.join(data_dir,'stop_sequence/stop_{0}.csv'.format(lineid)), 'r') as f:
            for line in f:
                if line.split(",")[1] == routeid:
                    direction = line.split(",")[2]
                    break
        if direction == 0:
            return Response("ERROR: cannot get direction", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        m_args = {
            'lineid': lineid,
            'start_stop': start_stop,
            'end_stop': end_stop,
            'direction': direction,
            'time_secs': "60000",
            'dow': "4",
            'holiday': "0",
            'rain': "0.0",
            'temp': "9.5",
            'vp': "10.6",
            'rh': "89.0"
        }

        data = {}
        data["journey_info"] = get_prediction(model, m_args, data_dir)

        if "error" in data["journey_info"].keys():
            if data["journey_info"]["error"] == "file structure error":
                return Response("ERROR IN FILE STRUCTURE", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response("ERROR IN MODEL", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data, status=status.HTTP_200_OK)


class RouteFindView(generics.RetrieveAPIView):
    def get(self, request):

        addr_suffix = ",Dublin,Ireland"
        start_addr = request.query_params.get('start_addr') + addr_suffix
        end_addr = request.query_params.get('end_addr') + addr_suffix
        api_url = "https://maps.googleapis.com/maps/api/directions/" + \
            "json?origin={0}&destination={1}&alternatives=true&mode=transit&key=AIzaSyBTqQ5XI6Z3N5j26PNXbFKUxUFfq8dnGV8".format(
                start_addr, end_addr, os.environ.get('DIR_API_KEY'))

        try:
            res = requests.get(api_url)
        except Exception as e:
            error_data = "ERROR, problem with google API"
            return Response(error_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        json_resp = json.loads(res.text)

        try:
            routes = json_resp['routes']
            x = routes[0]
        except IndexError:
            error_data = "ERROR, no routes found"
            return Response(error_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        data = process_resp(routes)

        return Response(data, status=status.HTTP_200_OK)


class RealTimeInfoView(generics.RetrieveAPIView):
    def get(self, request):

        stopid = request.query_params.get('stopid')

        print("StopID searched for is:", stopid)

        api_url = "https://data.smartdublin.ie/cgi-bin/rtpi/realtimebusinformation?stopid=" + stopid + "&format=json"

        try:
            res = requests.get(api_url)
        except Exception as e:
            error_data = "ERROR, problem with Real Time API"
            return Response(error_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        json_resp = json.loads(res.text)

        return Response(json_resp, status=status.HTTP_200_OK)
