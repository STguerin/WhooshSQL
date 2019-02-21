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

#### Setup a table
WhooshSQL has the common simple approach of Flask-WhooshAlchemy where you can add the searchable items as a list:
```python
Base = declarative_base()

class Post(Base):
    __tablename__ = 'post'
    __searchable__ = ['title', 'body'] #those field will be text field with StemmingAnalyzer

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    body = Column(Text)
```

#### Setup a session and add records
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

### You want more complex whoosh? no problem!
Instead of a list of column name, you can add a dictionary to unlock whoosh capabilities
```python
from whoosh.fields import TEXT
from whoosh.analysis import StemmingAnalyzer

Base = declarative_base()

class Post(Base):
    __tablename__ = 'post'
    __searchable__ = {'title': TEXT(stored=True, field_boost=2.0, analyzer=StemmingAnalyzer()),
                      'body': TEXT(stored=True, field_boost=1.0, analyzer=StemmingAnalyzer())}
                      
    id = Column(Integer, primary_key=True)
    title = Column(Text)
    body = Column(Text)
```
as you can see here, I added field boost so whoosh will score the results if it finds a match in TITLE first and then
it will check for in the BODY for that match. Flask-Alchemy does not keep track of the score whoosh give to the results
but WhooshSQL has that capability
```python
# search return a sql alchemy query, so you can call all, delete etc... (this does not keep track of whoosh score)
Post.whoosh.search('barcelona').all()  
Post.whoosh.search('madrid').all()

# ordered result based on whoosh score
results = Post.whoosh.search_all_ordered('madrid') # love madrid title first in list
results = Post.whoosh.search_all_ordered('barcelona') # love barcelona title first in list
```