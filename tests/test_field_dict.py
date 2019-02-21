import datetime
from unittest import TestCase

from whoosh.fields import Schema, TEXT, ID
from whoosh.analysis import StemmingAnalyzer, NgramFilter

from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session
from sqlalchemy.schema import Column
from sqlalchemy.types import DateTime, Integer, Text, UnicodeText

from whooshsql.core import IndexSubscriber


class Tests(TestCase):

    def setUp(self):

        engine = create_engine('sqlite:///:memory:', echo=False)
        self.session = Session(bind=engine)

        Base = declarative_base()

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

        self.Post = Post
        Base.metadata.create_all(engine)

        self.index_manager = IndexSubscriber(session=self.session, whoosh_base_path='index')
        self.index_manager.subscribe(Post)

        p1 = self.Post(title='love barcelona', body='it is the best city in the world even before madrid!')
        p2 = self.Post(title='love madrid', body='it is the second best city in the world after barcelona!')
        self.session.add_all([p1, p2])
        self.session.commit()

    def test_unordered_search(self):
        res = list(self.Post.whoosh.search(u'barcelona'))
        self.assertEqual(len(res), 2)

        res = list(self.Post.whoosh.search(u'madrid'))
        self.assertEqual(len(res), 2)

    def test_ordered_search(self):
        p1 = self.Post(title='love barcelona', body='it is the best city in the world even before madrid!')
        p2 = self.Post(title='love madrid', body='it is the second best city in the world after barcelona!')
        self.session.bulk_save_objects([p1, p2])
        self.session.commit()

        results = self.Post.whoosh.search_all_ordered('madrid')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].id, 2)
        self.assertEqual(results[1].id, 1)

        results = self.Post.whoosh.search_all_ordered('barcelona')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].id, 1)
        self.assertEqual(results[1].id, 2)


