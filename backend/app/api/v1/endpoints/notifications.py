from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.notification import DeviceToken
from app.models.user import User
from app.schemas.notification import DeviceTokenRegister, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=List[NotificationResponse])
def get_my_notifications(
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return NotificationService.get_user_notifications(db, current_user.id, unread_only)


@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.post("/tokens", status_code=status.HTTP_201_CREATED)
def register_device_push_token(
    data: DeviceTokenRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token = NotificationService.register_device_token(
        db=db,
        user_id=current_user.id,
        token=data.token,
        device_type=data.device_type
    )
    return {"message": "Device token registered successfully", "id": token.id}
