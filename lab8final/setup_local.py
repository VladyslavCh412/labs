"""Generate unique local accounts and signing key; never commit data/."""
import json
import os
import secrets
from pathlib import Path
from security import PASSWORDS

ROOT=Path(__file__).resolve().parent


def configure():
    data=ROOT/'data';data.mkdir(exist_ok=True)
    key=data/'jwt.key'; users=data/'users.json'; credentials=data/'LOCAL_ACCOUNTS.txt'
    if not key.exists():key.write_text(secrets.token_urlsafe(48),encoding='utf-8')
    if not users.exists():
        records={}; lines=['FleetFlow: generated LOCAL accounts. Do not publish this file.']
        for role in ['manager','dispatcher','viewer']:
            password=secrets.token_urlsafe(12)
            records[role]={'role':role,'password_hash':PASSWORDS.hash(password)}
            lines.append(f'{role}: {password}')
        users.write_text(json.dumps(records,indent=2),encoding='utf-8')
        credentials.write_text('\n'.join(lines),encoding='utf-8')
    os.environ.setdefault('FLEETFLOW_JWT_SECRET',key.read_text(encoding='utf-8').strip())
    os.environ.setdefault('FLEETFLOW_USERS_PATH',str(users))
    os.environ.setdefault('FLEETFLOW_AUDIT_PATH',str(data/'audit.jsonl'))
    return credentials


if __name__=='__main__':
    print('Local configuration ready. Accounts:',configure())
