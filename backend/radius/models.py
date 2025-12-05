from django.db import models

class RadiusLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20)
    logger = models.CharField(max_length=100)
    message = models.TextField()

    class Meta:
        db_table = 'radius_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.level} - {self.message[:50]}"
