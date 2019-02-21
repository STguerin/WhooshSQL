# WhooshSQL ![travis-ci](https://travis-ci.org/STguerin/WhooshSQL.svg?branch=master)
Whoosh integration for SQL Alchemy based on Flask-WhooshAlchemy written by Karl Gyllstromk and WhooshAlchemy by Stefane Fermigier.
 
Simply integrates all whoosh fields and search plugins for a more complete solution while keeping the simplicity of use to a minimum.



#### Import sqlalchemy
```python
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session
from sqlalchemy.schema import Column
from sqlalchemy.types import DateTime, Integer, Text, UnicodeText
```

### setup a table
WhooshSQL has the common simple approach of Flask-WhooshAlchemy where you can add the searchable items as has a list:
```python
Base = declarative_base()

class Post(Base):
    __tablename__ = 'post'
    __searchable__ = ['title', 'body']

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    body = Column(Text)
```

#### setup a session and add records
```python
engine = create_engine('sqlite:///:memory:', echo=True)
Base.metadata.create_all(engine)
session = Session(bind=engine)

p1 = Post(title='love barcelona', body='it is the best city in the world even before madrid!')
p2 = Post(title='love madrid', body='it is the second best city in the world after barcelona!')
session.add_all([p1, p2])
session.commit()
```

#### now let's use WhooshSQL
```python
from whooshsql.core import IndexSubscriber

index_subscriber = IndexSubscriber(session=session, whoosh_base_path='index')
index_subscriber.subscribe(Post)

p1 = Post(title='love barcelona', body='it is the best city in the world even before madrid!')
p2 = Post(title='love madrid', body='it is the second best city in the world after barcelona!')
session.add_all([p1, p2])
session.commit()

Post.whoosh.search('barcelona').all()
Post.whoosh.search('madrid').all()
```

