import sys
import itertools
import pandas as pd
sys.path.insert(0, 'dax_project-master')
from utils.Storage import Storage
from datetime import datetime

def get_news_tags_bq(args):
    # Get dataset name
    common_table = "PARAM_READ_DATE"
    common_list = ["BQ_DATASET", "FROM_DATE", "TO_DATE"]
    common_where = lambda x: (x["ENVIRONMENT"] == args.environment) & (x["STATUS"] == 'active')
    common_parameters = get_parameters(args.param_connection_string, common_table, common_list, common_where)

    print("news_tags")

    columns = ["Date", "constituent", "Tags", "Count", "constituent_name", "constituent_id", "From_date", "To_date"]

    query = """
    SELECT
  a.news_date AS Date,
  a.constituent,
  b.news_topics as Tags,
  COUNT(b.news_topics) AS Count,
  a.constituent_name,
  a.constituent_id,
  TIMESTAMP('{1}') as From_date, TIMESTAMP('{2}') as To_date
FROM
  `{0}.all_news` a,
(SELECT
  x.news_id,
  news_topics
FROM
  `{0}.all_news` AS x,
  UNNEST(news_topics) AS news_topics) b
WHERE a.news_id = b.news_id AND 
a.news_date BETWEEN TIMESTAMP ('{1}')
  AND TIMESTAMP ('{2}')
GROUP BY
  Date,
  a.constituent,
  b.news_topics,
  a.constituent_name,
  a.constituent_id;
    """.format(common_parameters["BQ_DATASET"],common_parameters["FROM_DATE"].strftime("%Y-%m-%d"),
               common_parameters["TO_DATE"].strftime("%Y-%m-%d"))

    storage_client = Storage.Storage(args.google_key_path)

    result = storage_client.get_bigquery_data(query, iterator_flag=True)
    to_insert = []

    for item in result:
        to_insert.append(dict((k,item[k].strftime('%Y-%m-%d %H:%M:%S')) if isinstance(item[k],datetime) else
                   (k,item[k]) for k in columns))

    try:
        storage_client.insert_bigquery_data(common_parameters["BQ_DATASET"], 'news_tag', to_insert)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('python_path', help='The connection string')
    parser.add_argument('google_key_path', help='The path of the Google key')
    parser.add_argument('param_connection_string', help='The MySQL connection string')
    parser.add_argument('environment', help='production or test')
    args = parser.parse_args()
    sys.path.insert(0, args.python_path)
    from utils.Storage import Storage
    from utils.twitter_analytics_helpers import *
    get_news_tags_bq(args)        
