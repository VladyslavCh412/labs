from security import service_headers
"""Independent HTTP bridge; NO direct access to either service's SQLite DB.
At-least-once: ack only after consumer success. Safe to replay one event.
"""
import argparse
import os
import time
import httpx


def pump_once(fleet_url, trips_url,client=None):
    def run(c):
        pending=c.get(fleet_url.rstrip('/')+'/fleet-events/outbox',headers=service_headers('bridge')).raise_for_status().json()
        stats={'delivered':0,'pending':0}
        for envelope in pending:
            if envelope['delivered']:
                continue
            stats['pending']+=1
            body=envelope['payload']
            response=c.post(trips_url.rstrip('/')+'/events/fleet-status',json=body,headers=service_headers('bridge'))
            response.raise_for_status()
            c.post(fleet_url.rstrip('/')+'/fleet-events/ack/'+envelope['event_id'],headers=service_headers('bridge')).raise_for_status()
            stats['delivered']+=1
        return stats
    if client is not None:return run(client)
    with httpx.Client(timeout=2.5) as c:return run(c)


def main():
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');p.add_argument('--interval',type=float,default=0.5)
    a=p.parse_args()
    fleet=os.getenv('FLEET_URL','http://127.0.0.1:8101')
    trips=os.getenv('TRIPS_URL','http://127.0.0.1:8102')
    while True:
        try:
            res=pump_once(fleet,trips)
            if res['delivered']:print('Delivered',res,flush=True)
        except httpx.HTTPError as exc:
            print('Retry later:',exc,flush=True)
            if a.once:raise
        if a.once:return
        time.sleep(a.interval)

if __name__=='__main__':main()
