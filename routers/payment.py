from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
import models, schemas
import os
import time
from datetime import datetime, timezone

router = APIRouter(prefix="/api/payment", tags=["Payment"])

# Legacy Manual UPI/UTR Endpoints - Disabled in favor of Cashfree
#
# @router.post("/create-order")
# def create_payment_order(...):
#     ...
#
# @router.post("/submit-utr")
# def submit_utr(...):
#     ...

