from app.providers.alerts.base import AlertProvider

class AlertService:
    def __init__(self, alert_provider: AlertProvider):
        self.provider = alert_provider
