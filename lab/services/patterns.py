# Patterns: Strategy (route pricing), Factory Method (notifications), Adapter (maps), Observer (events)
from abc import ABC,abstractmethod
class TariffStrategy(ABC):
    @abstractmethod
    def price(self,km):...
class StandardTariff(TariffStrategy):
    def price(self,km):return round(km*20,2)
class ExpressTariff(TariffStrategy):
    def price(self,km):return round(km*30,2)
class TariffContext:
    def __init__(self,strategy:TariffStrategy):self.strategy=strategy
    def quote(self,km):return self.strategy.price(km)
class EmailNotification:
    def send(self,message):return 'email:'+message
class SMSNotification:
    def send(self,message):return 'sms:'+message
class NotificationFactory:
    @staticmethod
    def make(channel):
        constructors={'email':EmailNotification,'sms':SMSNotification}
        if channel not in constructors:raise ValueError('Невідомий канал')
        return constructors[channel]()
class LegacyMapsAdapter:
    def __init__(self,legacy_client):self.client=legacy_client
    def distance(self,start,end):return self.client.get_route({'from':start,'to':end})['distance_km']
class EventBus:
    def __init__(self):self.subscribers={}
    def subscribe(self,kind,callback):self.subscribers.setdefault(kind,[]).append(callback)
    def publish(self,kind,payload):
        for callback in self.subscribers.get(kind,[]):callback(payload)
