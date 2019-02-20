import os

from whoosh import writing
import whoosh.fields
from whoosh.index import create_in, open_dir, exists_in
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import QueryParser, MultifieldParser

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect


class Subscription:

    def __init__(self, table, schema, index):
        self.table = table
        self.primary_key = inspect(table).primary_key[0]
        self.name = table.__tablename__
        self.schema = schema
        self.index = index

        self._search_query = None

        # commit trackers
        self.new = list()
        self.modified = list()
        self.deleted = list()

    @property
    def search_query(self):
        return self._search_query

    @search_query.setter
    def search_query(self, searcher):
        if isinstance(searcher, Searcher):
            self._search_query = searcher
        else:
            raise AttributeError(f'search query should be of instance Searcher not {searcher}')

    def get_document_from_table_entry(self, entry):
        whoosh_document = dict()
        for field_name, field in self.schema.items():
            whoosh_document[field_name] = str(getattr(entry, field_name))
        return whoosh_document

    def reset_after_commit(self):
        self.new = list()
        self.modified = list()
        self.deleted = list()

    def __repr__(self):
        return f'Subscription({self.name, self.schema})'


class Searcher:

    def __init__(self, subscription, session):
        self.subscription = subscription
        self.session = session
        self.parser = MultifieldParser(subscription.table.__searchable__, self.subscription.schema)

    def __call__(self, query, limit=None, plugin=None):
        qp = QueryParser(query, schema=self.subscription.schema)
        if plugin:
            qp.add_plugin(plugin)

        pk = self.subscription.primary_key
        results = self.subscription.index.searcher().search(self.parser.parse(query), limit=limit)
        keys = [x[pk.name] for x in results]
        return self.session.query(self.subscription.table).filter(pk.in_(keys))


class IndexSubscriber:

    def __init__(self, session, whoosh_base_path):
        self.whoosh_base_path = whoosh_base_path
        self.session = session
        self.subscriptions = dict()

        event.listen(Session, "before_commit", self.isolate_all_new_database_action)
        event.listen(Session, "after_commit", self.add_remove_or_modify_committed_entries)

    def subscribe(self, table, index_from_scratch=False):
        schema = self.transform_table_to_whoosh_schema(table)
        index = self.get_or_create_whoosh_index(table, schema)

        subscription = Subscription(table=table, schema=schema, index=index)
        self.subscriptions[table.__tablename__] = subscription
        setattr(table, 'search_query', Searcher(subscription, self.session))

        if index_from_scratch:
            self.index_current_table_entries(table)

    def get_or_create_whoosh_index(self, table, schema):
        index_path = os.path.join(self.whoosh_base_path, table.__tablename__)
        if exists_in(index_path):
            index = open_dir(index_path)
        else:
            if not os.path.exists(index_path):
                os.makedirs(index_path)
            index = create_in(index_path, schema)
        return index

    @staticmethod
    def transform_table_to_whoosh_schema(table):
        schema_kwargs = dict()
        for pk in inspect(table).primary_key:
            schema_kwargs[pk.name] = whoosh.fields.ID(stored=True, unique=True)

        if isinstance(table.__searchable__, list):
            for field_name in table.__searchable__:
                field = getattr(table, field_name)
                if type(field.type) in (sqlalchemy.types.Text,
                                        sqlalchemy.types.UnicodeText,
                                        sqlalchemy.types.TEXT,
                                        sqlalchemy.types.VARCHAR,
                                        sqlalchemy.types.NVARCHAR,
                                        sqlalchemy.types.String,
                                        sqlalchemy.types.STRINGTYPE):
                    schema_kwargs[field.name] = whoosh.fields.TEXT(analyzer=StemmingAnalyzer(), stored=True)

        elif isinstance(table.__searchable__, dict):
            schema_kwargs.update(table.__searchable__)

        else:
            error = f'__searchable__ should be a list of string or a dictionary of column: whoosh field'
            raise ValueError(error)

        return whoosh.fields.Schema(**schema_kwargs)

    def index_current_table_entries(self, table):
        subscription = self.subscriptions[table.__tablename__]
        sql_results = self.session.query(table).all()

        writer = subscription.index.writer()
        writer.commit(mergetype=writing.CLEAR)

        with subscription.index.writer() as writer:
            for entry in sql_results:
                document = subscription.get_document_from_table_entry(entry=entry)
                writer.add_document(**document)

    def isolate_all_new_database_action(self, session):
        for entry in session.new:
            table_name = entry.__class__.__tablename__
            subscription = self.subscriptions.get(table_name, None)
            if subscription is not None:
                subscription.new.append(entry)

        for entry in session.deleted:
            table_name = entry.__class__.__tablename__
            subscription = self.subscriptions.get(table_name, None)
            if subscription is not None:
                subscription.deleted.append(entry)

        for entry in session.dirty:
            table_name = entry.__class__.__tablename__
            subscription = self.subscriptions.get(table_name, None)
            if subscription is not None:
                subscription.modified.append(entry)

    def add_remove_or_modify_committed_entries(self, session):

        for table_name, subscription in self.subscriptions.items():
            with subscription.index.writer() as writer:

                pk = subscription.primary_key.name
                for entry in subscription.deleted:
                    writer.delete_by_term(pk, str(getattr(entry, pk)))

                for entry in subscription.modified:
                    whoosh_document = subscription.get_document_from_table_entry(entry=entry)
                    writer.update_document(**whoosh_document)

                other_entries = subscription.new + subscription.modified
                for entry in other_entries:
                    whoosh_document = subscription.get_document_from_table_entry(entry=entry)
                    writer.add_document(**whoosh_document)

                subscription.reset_after_commit()