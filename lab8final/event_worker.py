"""Asynchronous subscriber; no HTTP request waits for this process."""
import argparse
import os
import time
from trips_service.repository import TripsRepository

def main():
    parser = argparse.ArgumentParser(description='TripCreated notification subscriber')
    parser.add_argument('--once', action='store_true', help='Deliver queued events once and exit')
    parser.add_argument('--interval', type=float, default=0.5)
    args = parser.parse_args()
    repo = TripsRepository(os.getenv('TRIPS_DB_PATH', 'data/trips.sqlite'))
    print('Worker TripCreated -> Notification started', flush=True)
    while True:
        delivered = repo.deliver_pending()
        if delivered:
            print(f'Delivered {delivered} TripCreated event(s)', flush=True)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == '__main__':
    main()
