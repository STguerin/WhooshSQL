import datetime

from whoosh.fields import TEXT
from whoosh.analysis import StemmingAnalyzer

from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session
from sqlalchemy.schema import Column
from sqlalchemy.types import DateTime, Integer, Text, UnicodeText

from whooshsql.core import IndexSubscriber


# On memory sql lite
engine = create_engine('sqlite:///:memory:', echo=True)
session = Session(bind=engine)
Base = declarative_base()


# create a table with a more complex setup
class Post(Base):
    __tablename__ = 'post'
    __searchable__ = {'title': TEXT(stored=True, field_boost=2.0, analyzer=StemmingAnalyzer()),
                      'body': TEXT(stored=True, field_boost=1.0, analyzer=StemmingAnalyzer())}

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    body = Column(UnicodeText)
    created = Column(DateTime, default=datetime.datetime.utcnow())

    def __repr__(self):
        return '{0}(title={1})'.format(self.__class__.__name__,
                                       self.title)


Base.metadata.create_all(engine)
p1 = Post(title='love barcelona', body='it is the best city in the world even before madrid!')
p2 = Post(title='love madrid', body='it is the second best city in the world after barcelona!')
session.bulk_save_objects([p1, p2])
session.commit()

# you can also index from scratch
index_subscriber = IndexSubscriber(session=session, whoosh_base_path='index')
index_subscriber.subscribe(Post, index_from_scratch=True)


# normal search, this does not keep whoosh score
Post.whoosh.search('barcelona').all()
Post.whoosh.search('madrid').all()

# ordered result based on whoosh score
results = Post.whoosh.search_all_ordered('madrid')
results = Post.whoosh.search_all_ordered('barcelona')