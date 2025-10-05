from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

VECTOR_DIMENSION = 384


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    sequences = relationship("Sequence", back_populates="category")


class Letter(Base):
    __tablename__ = "letters"
    id = Column(Integer, primary_key=True)
    letter = Column(Text, unique=True, nullable=False)
    sequences = relationship("Sequence", back_populates="letter")


class Sequence(Base):
    __tablename__ = "sequences"
    id = Column(Integer, primary_key=True)
    sequence = Column(Text, nullable=False)
    morphology_url = Column(Text)
    letter_id = Column(Integer, ForeignKey("letters.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))

    letter = relationship("Letter", back_populates="sequences")
    category = relationship("Category", back_populates="sequences")
    words = relationship("Word", back_populates="sequence_relation")


class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True)
    arabic_word = Column(Text)
    english_text = Column(Text)
    verse_reference = Column(Text)
    sequence_id = Column(Integer, ForeignKey("sequences.id"))
    embedding = Column(Vector(VECTOR_DIMENSION))

    sequence_relation = relationship("Sequence", back_populates="words")
