from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from .models import Trip, LogEntry
from .serializers import TripSerializer, LogEntrySerializer
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import os

load_dotenv()
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        
        response_data = generate_eld_logs(trip)
        return Response(response_data)
    
    def retrieve(self, request, *args, **kwargs):
        trip = self.get_object()
        return Response({
            "trip": TripSerializer(trip).data,
            "eld_logs": generate_eld_logs(trip)
        })


def get_coordinates(location_name):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{location_name}.json?access_token={MAPBOX_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "features" in data and data["features"]:
        coordinates = data["features"][0]["geometry"]["coordinates"]
        return f"{coordinates[0]},{coordinates[1]}"
    return None


def get_route_info(origin_name, stops, destination_name):
    waypoints = [get_coordinates(stop) for stop in stops if get_coordinates(stop)]
    origin = get_coordinates(origin_name)
    destination = get_coordinates(destination_name)
    
    if not origin or not destination:
        return None, None
    
    route_points = ";".join([origin] + waypoints + [destination])
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{route_points}?access_token={MAPBOX_API_KEY}&overview=full&geometries=geojson"
    response = requests.get(url)
    data = response.json()
    
    if "routes" in data and data["routes"]:
        duration_hours = data["routes"][0]["duration"] / 3600
        distance_miles = data["routes"][0]["distance"] * 0.000621371
        return duration_hours, distance_miles
    return None, None


def generate_eld_logs(trip):
    stops = trip.pickup_location.split(",") if trip.pickup_location else []
    duration_hours, distance_miles = get_route_info(trip.current_location, stops, trip.dropoff_location)
    
    if duration_hours is None:
        return {"error": "Unable to calculate route."}
    
    total_driving_hours = min(11, duration_hours)
    total_on_duty_hours = total_driving_hours + 1.5 + (len(stops) * 0.5)  # Extra 30 min per stop
    remaining_hours = max(0, 14 - total_on_duty_hours)  # 14-hour duty limit
    fuel_stops = int(distance_miles // 1000)  # Fueling every 1,000 miles
    
    log_entries = []
    start_time = datetime.now()
    odometer = 0
    
    locations = [trip.current_location] + stops + [trip.dropoff_location]
    segment_distance = distance_miles / max(1, len(locations) - 1)
    segment_duration = total_driving_hours / max(1, len(locations) - 1)
    
    daily_logs = []
    current_log = []
    current_hours = 0
    
    for i, location in enumerate(locations):
        if current_hours >= 14:  # New day starts
            daily_logs.append(current_log)
            current_log = []
            current_hours = 0
            start_time += timedelta(hours=10)  # Mandatory 10-hour reset
        
        current_log.append({
            "time": start_time.strftime("%I:%M:%S %p"),
            "status": "ON DUTY" if i == 0 or i == len(locations) - 1 else "STOPPED",
            "remarks": f"Stop at {location}",
            "odometer": odometer
        })
        start_time += timedelta(minutes=30 if 0 < i < len(locations) - 1 else 90)
        current_hours += 1.5 if i == 0 or i == len(locations) - 1 else 0.5
        
        if i < len(locations) - 1:
            current_log.append({
                "time": start_time.strftime("%I:%M:%S %p"),
                "status": "DRIVING",
                "remarks": "En route to next stop",
                "odometer": odometer + segment_distance
            })
            odometer += segment_distance
            start_time += timedelta(hours=segment_duration)
            current_hours += segment_duration
    
    if current_log:
        daily_logs.append(current_log)
    
    response_data = {
        "driver_name": trip.driver_name,
        "vehicle_id": trip.vehicle_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "remaining_hours": remaining_hours,
        "hours_summary": {
            "total_driving_hours": total_driving_hours,
            "total_on_duty_hours": total_on_duty_hours,
            "fuel_stops": fuel_stops
        },
        "daily_logs": daily_logs
    }
    
    return response_data


class LogEntryViewSet(viewsets.ModelViewSet):
    queryset = LogEntry.objects.all()
    serializer_class = LogEntrySerializer
