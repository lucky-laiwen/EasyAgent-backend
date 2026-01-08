from database import Base
from sqlalchemy import Column, Integer, DateTime, ForeignKey ,func ,BigInteger,SmallInteger
from sqlalchemy.orm import relationship

class UserFriend(Base):
    __tablename__ = 'user_friend'

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    friend_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    status = Column(SmallInteger, default=0, comment='0=待确认,1=已确认,2=被拉黑')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    friend = relationship("User", foreign_keys=[friend_id], lazy="joined")
