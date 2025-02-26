from django.db import models

class Trip(models.Model):
    driver_name = models.CharField(max_length=255) 
    vehicle_id = models.CharField(max_length=255)  
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    cycle_used = models.IntegerField()  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver_name} - {self.current_location} to {self.dropoff_location}"

class LogEntry(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    time = models.DateTimeField()
    status = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.status} at {self.time}"
