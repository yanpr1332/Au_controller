"""Canonical current software and scoped native verification: phase11."""
from __future__ import annotations
import argparse
from verify_phase11 import check

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Current Audition 26 release QA")
    p.add_argument("--sdk",action="store_true",help="Require live host and clean document list")
    p.add_argument("--full-tests",action="store_true",help="Run the current full regression suite")
    a=p.parse_args()
    check(full_tests=a.full_tests,sdk=a.sdk)
