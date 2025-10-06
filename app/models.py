from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .database import Base


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

    __table_args__ = (UniqueConstraint('sequence', 'letter_id', name='_sequence_letter_uc'),)


class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True)
    arabic_word = Column(Text)
    transliteration = Column(Text)
    english_text = Column(Text)
    verse_reference = Column(Text, nullable=False, unique=True)
    quran_verse = Column(Text)
    sequence_id = Column(Integer, ForeignKey("sequences.id"))

    sequence_relation = relationship("Sequence", back_populates="words")
    embeddings = relationship("Embedding", back_populates="word")


class EmbeddingModel(Base):
    __tablename__ = "embedding_models"
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    dimension = Column(Integer, nullable=False)
    embeddings = relationship("Embedding", back_populates="model")


class Embedding(Base):
    __tablename__ = "embeddings"
    id = Column(Integer, primary_key=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("embedding_models.id"), nullable=False)
    
    # IMPORTANT: All vectors in this table must have the same dimension (1024)
    # for indexing to work. If you add models with different dimensions
    # in the future, the best practice is to create a new table for them.
    embedding = Column(Vector(1024))

    word = relationship("Word", back_populates="embeddings")
    model = relationship("EmbeddingModel", back_populates="embeddings")

    __table_args__ = (UniqueConstraint('word_id', 'model_id', name='_word_model_uc'),)
