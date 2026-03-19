from sqlalchemy.orm import Session
from models.system_message import SystemMessage

def create_system_message(db: Session, title: str, content: str, user_id: int , action_type:int = 0) -> SystemMessage:
    system_message = SystemMessage(title=title, content=content, user_id=user_id,action_type=action_type)
    db.add(system_message)
    db.commit()
    db.refresh(system_message)
    return system_message