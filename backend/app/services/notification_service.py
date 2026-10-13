import logging
import os
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.enums import DeviceType, NotificationType
from app.models.notification import DeviceToken, Notification

logger = logging.getLogger("healora.notifications")

# Optional Firebase Admin SDK initialization
firebase_initialized = False
if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
    try:
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase Admin SDK: {e}")


class NotificationService:
    @staticmethod
    def send_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: NotificationType,
        reference_id: Optional[str] = None
    ) -> Notification:
        """
        Creates an in-app notification in the database and dispatches push notification if configured.
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            is_read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Dispatch push notification if Firebase is available
        if firebase_initialized:
            try:
                from firebase_admin import messaging
                tokens = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
                for token_obj in tokens:
                    msg = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=message,
                        ),
                        data={
                            "notification_type": notification_type.value,
                            "reference_id": str(reference_id or ""),
                        },
                        token=token_obj.token
                    )
                    messaging.send(msg)
            except Exception as e:
                logger.error(f"Error sending FCM push notification: {e}")
        else:
            logger.info(f"[Mock Push Notification] User {user_id} | Type: {notification_type.value} | Title: {title}")

        return notification

    @staticmethod
    def register_device_token(
        db: Session,
        user_id: int,
        token: str,
        device_type: DeviceType = DeviceType.ANDROID
    ) -> DeviceToken:
        existing = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.token == token
        ).first()

        if existing:
            existing.device_type = device_type
            db.commit()
            db.refresh(existing)
            return existing

        new_token = DeviceToken(
            user_id=user_id,
            token=token,
            device_type=device_type
        )
        db.add(new_token)
        db.commit()
        db.refresh(new_token)
        return new_token

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        unread_only: bool = False
    ) -> List[Notification]:
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == False)
        return query.order_by(Notification.created_at.desc()).all()

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> bool:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        if notification:
            notification.is_read = True
            db.commit()
            return True
        return False
