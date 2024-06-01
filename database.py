from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    wallet_address = Column(String, unique=True)
    referral_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referrals = relationship('User', backref='referrer', remote_side=[id])

DATABASE_URL = 'postgres://ldiueqzskvrgow:be012ee6b6cee9dc6f30ca0a8a37ae17b90fb5c5e142a6efe4cb15494e10bf48@ec2-52-31-2-97.eu-west-1.compute.amazonaws.com:5432/d4a91jiqud73el'

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
