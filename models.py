from datetime import datetime
from sqlalchemy import create_engine, Column, BigInteger, Integer, DateTime, String
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Type

engine = create_engine('sqlite:///database.db')
Session = sessionmaker(bind=engine)
Base = declarative_base()

class UserPoints(Base):  # type: ignore
    __tablename__ = 'user_points'
    
    user_id = Column(BigInteger, primary_key=True)
    points = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class RoleHierarchy(Base):  # type: ignore
    __tablename__ = 'role_hierarchy'
    
    role_name = Column(String, primary_key=True)
    point_threshold = Column(Integer, nullable=False)
    order = Column(Integer, nullable=False)