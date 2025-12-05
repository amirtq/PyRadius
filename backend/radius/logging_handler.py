import logging

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        from .models import RadiusLog
        from django.conf import settings
        
        try:
            msg = self.format(record)
            RadiusLog.objects.create(
                level=record.levelname,
                logger=record.name,
                message=msg
            )
            
            # Retention logic
            limit = getattr(settings, 'RADIUS_LOG_RETENTION', 1000)
            if limit:
                # Keep only the latest 'limit' logs
                # Retrieve IDs of the most recent 'limit' logs
                ids_to_keep = list(RadiusLog.objects.values_list('id', flat=True)[:limit])
                
                if len(ids_to_keep) == limit:
                    # If we have reached the limit, delete everything else
                    RadiusLog.objects.exclude(id__in=ids_to_keep).delete()
                
        except Exception:
            self.handleError(record)
