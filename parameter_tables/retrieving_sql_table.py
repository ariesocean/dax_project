##Check if data has been added successfully
from pymongo import MongoClient, errors
#from google.cloud import storage
#from google.cloud.exceptions import GoogleCloudError, NotFound
import os
#import jsonpickle
from sqlalchemy import *
import json
import pandas as pd
from bs4 import BeautifulSoup
import urllib



def get_sql_data(args,sql_where=None):
    engine = create_engine(args.sql_connection_string)
    metadata = MetaData(engine)

    source_table = Table(args.sql_table_name, metadata, autoload=True)
    projection_columns = [source_table.columns[name] for name in args.sql_column_list]

    if sql_where:
        statement = select(projection_columns).where(sql_where(source_table.columns))
    else:
        statement = select(projection_columns)
    result = statement.execute()
    rows = result.fetchall()
    result.close()
    print rows
    return rows


if __name__ == "__main__":
    #sql_string = 'mysql+pymysql://igenie_readwrite:igenie@35.197.246.202/dax_project'
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sql_connection_string', help='The sql connection string')
    parser.add_argument('sql_table_name', help='The name of sql table')
<<<<<<< HEAD
    get_sql_data(args, sql_where=None)
    
=======
    parser.add_argument('sql_column_list',help='Name of the column list')
    args = parser.parse_args()
    rows=get_sql_data(args, sql_where=None)
    df = pd.DataFrame(list(rows))
    print df.head()
>>>>>>> d33d1d5b47fc0f9be12a45e3e87455f211f875fe
