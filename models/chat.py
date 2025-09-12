from database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey , Text ,func
class Chat(Base):
    __tablename__ = 'chat'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    user_id = Column(Integer, ForeignKey('user.id'))
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())