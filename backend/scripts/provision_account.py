"""Provision a local credential without passing its password in command arguments."""
import argparse
from getpass import getpass
from uuid import UUID
from app.core.database import SessionLocal
from app.services.auth_service import provision_account

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('username')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--teacher-id',type=UUID)
    group.add_argument('--student-id',type=UUID)
    args=parser.parse_args()
    password=getpass('Password (at least 12 characters): ')
    if getpass('Repeat password: ') != password:parser.error('Passwords do not match')
    with SessionLocal() as db:
        provision_account(db,args.username,password,teacher_id=args.teacher_id,student_id=args.student_id);db.commit()
    print('Account provisioned; password was not logged.')

if __name__=='__main__':main()
