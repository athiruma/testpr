import json
import os
import boto3
import tempfile
from datetime import datetime, timedelta
from time import strftime
import time

from elasticsearch import Elasticsearch



class ElasticSearchOperations:
    """
    This class related to ElasticSearch operations
    """

    # sleep time between checks is 10 sec
    SLEEP_TIME = 10
    # ElasticSearch fetch data of last 15 minutes
    ES_FETCH_MIN_TIME = 15
    # max search results
    MAX_SEARCH_RESULTS = 1000
    MIN_SEARCH_RESULTS = 100

    def __init__(self, es_host: str, es_port: str, region: str = '', bucket: str = '', logs_bucket_key: str = '',
                 timeout: int = 2000):
        self.__es_host = es_host
        self.__es_port = es_port
        self.__region = region
        self.__timeout = timeout
        self.__es = Elasticsearch([{'host': self.__es_host, 'port': self.__es_port}])
        if region:
            self.__bucket = bucket
            self.__logs_bucket_key = logs_bucket_key
            self.__iam_client = boto3.client('iam', region_name=region)
            self.__trail_client = boto3.client('cloudtrail', region_name=region)

    def upload_to_elasticsearch(self, index: str, data: dict, doc_type: str = '_doc', es_add_items: dict = None):
        """
        This method is upload json data into elasticsearch
        :param index: index name to be stored in elasticsearch
        :param data: data must me in dictionary i.e. {'key': 'value'}
        :param doc_type:
        :param es_add_items:
        :return:
        """
        # read json to dict
        json_path = ""

        # Add items
        if es_add_items:
            for key, value in es_add_items.items():
                data[key] = value

        # utcnow - solve timestamp issue
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow()  # datetime.now()

        # Upload data to elastic search server
        try:
            if isinstance(data, dict):  # JSON Object
                self.__es.index(index=index, doc_type=doc_type, body=data)
            else:  # JSON Array
                for record in data:
                    self.__es.index(index=index, doc_type=doc_type, body=record)
            return True
        except Exception as err:
            raise err

    def get_query_data_between_range(self, start_datetime: datetime, end_datetime: datetime):
        """
        This method returns the query to fetch the data in between ranges
        @return:
        """
        query = {
            "query": {
                "bool": {
                    "filter": {
                        "range": {
                            "timestamp": {
                                "format": "yyyy-MM-dd HH:mm:ss"
                            }
                        }
                    }
                }
            }
        }
        query['query']['bool']['filter']['range']['timestamp']['lte'] = str(end_datetime.replace(microsecond=0))
        query['query']['bool']['filter']['range']['timestamp']['gte'] = str(start_datetime.replace(microsecond=0))
        return query

    def fetch_data_between_range(self, es_index: str, start_datetime: datetime, end_datetime: datetime):
        """
        This method fetches the data in between range
        @param es_index:
        @param start_datetime:
        @param end_datetime:
        @return:
        """
        if self.__es.indices.exists(index=es_index):
            query_body = self.get_query_data_between_range(start_datetime=start_datetime, end_datetime=end_datetime)
            data = self.__es.search(index=es_index, body=query_body, doc_type='_doc').get('hits')
            if data:
                return data['hits']
        return []

    def delete_data_in_between_in_es(self, es_index: str, start_datetime: datetime, end_datetime: datetime):
        """
        This method deletes the data in between two ranges
        @param es_index:
        @param start_datetime:
        @param end_datetime:
        @return:
        """
        if self.__es.indices.exists(index=es_index):
            query_body = self.get_query_data_between_range(start_datetime=start_datetime, end_datetime=end_datetime)
            print(f'Clearing data from {start_datetime} to  {end_datetime} ')
            return self.__es.delete_by_query(index=es_index, body=query_body)

    def delete_data_in_es(self, es_index: str):
        """
        This method delete the data in the index
        @param es_index: index_name
        @return:
        """
        if self.__es.indices.exists(index=es_index):
            return self.__es.indices.delete(index=es_index)
