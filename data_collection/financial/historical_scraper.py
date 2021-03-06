from selenium import webdriver
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient, errors
from datetime import datetime, timedelta
from requests.compat import urljoin
import time
import sys

def main(args):
    if __name__ != "__main__":
        sys.path.insert(0, args.python_path)
        from utils.Storage import Storage
        from utils import twitter_analytics_helpers as tah

    driver = webdriver.PhantomJS()

    # Get parameters
    param_table = "PARAM_HISTORICAL_COLLECTION"
    parameters_list = ["LOGGING", "DESTINATION_TABLE"]

    parameters = tah.get_parameters(args.param_connection_string, param_table, parameters_list)

    # Get dataset name
    common_table = "PARAM_READ_DATE"
    common_list = ["BQ_DATASET"]
    common_where = lambda x: (x["ENVIRONMENT"] == args.environment) & (x["STATUS"] == 'active')

    common_parameters = tah.get_parameters(args.param_connection_string, common_table, common_list, common_where)

    # Get constituents
    storage = Storage(google_key_path=args.google_key_path)

    query = """
    SELECT a.CONSTITUENT_ID, a.CONSTITUENT_NAME, b.URL_KEY
    FROM MASTER_CONSTITUENTS a, PARAM_FINANCIAL_URL_KEYS b
    WHERE a.CONSTITUENT_ID = b.CONSTITUENT_ID
    """

    all_constituents = storage.get_sql_data_text_query(args.param_connection_string, query)

    # Get dates
    query = """
    SELECT max(date) as last_date FROM `{}.{}`
    """.format(common_parameters["BQ_DATASET"],parameters["DESTINATION_TABLE"])

    try:
        result = storage.get_bigquery_data(query=query,iterator_flag=False)
    except Exception as e:
        print(e)
        return

    from_date = result[0]["last_date"] + timedelta(days=1)
    ts = from_date.strftime("%d.%m.%Y")
    from_date_parts = ts.split(".")
    if from_date_parts[0][0] == "0":
        from_date_parts[0] = from_date_parts[0][1:]
    if from_date_parts[1][0] == "0":
        from_date_parts[1] = from_date_parts[1][1:]

    from_date = ".".join(from_date_parts)

    to_date = datetime.now().strftime("%d.%m.%Y")
    to_date_parts = to_date.split(".")
    if to_date_parts[0][0] == "0":
        to_date_parts[0] = to_date_parts[0][1:]
    if to_date_parts[1][0] == "0":
        to_date_parts[1] = to_date_parts[1][1:]

    to_date = ".".join(to_date_parts)

    if from_date == to_date:
        return

    dax_url = 'http://en.boerse-frankfurt.de/index/pricehistory/DAX/{}_{}#History'.format(from_date,to_date)
    constituent_base_url = 'http://en.boerse-frankfurt.de/stock/pricehistory/'
    constituent_date_url = '-share/FSE/{}_{}#Price_History'.format(from_date,to_date)

    if args.all:
        extract_historical_data(dax_url, driver, storage, common_parameters["BQ_DATASET"],
                                parameters["DESTINATION_TABLE"],constituent='DAX')
        for constituent_id, constituent_name, url_key in all_constituents:
            print("Extracting data for {} from {} to {}".format(constituent_name, from_date, to_date))
            extract_historical_data(urljoin(constituent_base_url, url_key + constituent_date_url),
                                    driver, storage, common_parameters["BQ_DATASET"],
            parameters["DESTINATION_TABLE"],constituent=(constituent_id, constituent_name))
            time.sleep(10)
    else:
        if args.constituent == 'DAX':
            extract_historical_data(dax_url, driver, storage, common_parameters["BQ_DATASET"],
            parameters["DESTINATION_TABLE"],constituent='DAX')
        else:
            for constituent_id, constituent_name, url_key in all_constituents:
                if constituent_id == args.constituent:
                    print("Extracting data for {} from {} to {}".format(constituent_name, from_date, to_date))
                    constituent_url = urljoin(constituent_base_url, url_key + constituent_date_url)
                    extract_historical_data(constituent_url, driver, storage, common_parameters["BQ_DATASET"],
                    parameters["DESTINATION_TABLE"],constituent=(constituent_id, constituent_name))

    driver.quit()

def extract_historical_data(url, driver, storage_client, dataset_name,table_name,constituent=None):
    from utils.Storage import Storage
    from utils import twitter_analytics_helpers as tah

    if isinstance(constituent, tuple):
        constituent_id = constituent[0]
        constituent_name = constituent[1]
        constituent_old_name = tah.get_old_constituent_name(constituent_id)

    driver.get(url)
    rows = []
    time.sleep(20)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    table = soup.find(id=re.compile(r'grid-table-.*'))
    if table is None:
        print("Not able to load the data for " + constituent)
        return
    table_body = table.find('tbody')
    table_row = table_body.find('tr')

    if constituent == 'DAX':
        while table_row.find_next_sibling('tr'):
            data = table_row.find_all('td')
            try:
                date = datetime.strptime(data[0].string, "%d/%m/%Y")
                date_string = date.strftime('%Y-%m-%d %H:%M:%S')

                rows.append({'constituent': 'DAX',
                             'date':date_string,
                             'opening_price': float(data[3].string.replace(',', '')),
                             'closing_price': float(data[2].string.replace(',', '')),
                             'daily_high': float(data[4].string.replace(',', '')),
                             'daily_low': float(data[5].string.replace(',', '')),
                             'turnover': None,
                             'volume': float(data[1].string.replace(',','')),
                             'constituent_id':"DAX",
                            'constituent_name':"DAX"
                })
            except AttributeError as e:
                pass

            table_row = table_row.find_next_sibling('tr')

        data = table_row.find_all('td')

        try:
            date = datetime.strptime(data[0].string, "%d/%m/%Y")
            date_string = date.strftime('%Y-%m-%d %H:%M:%S')

            rows.append({'constituent': 'DAX',
                         'date': date_string,
                         'opening_price': float(data[3].string.replace(',', '')),
                         'closing_price': float(data[2].string.replace(',', '')),
                         'daily_high': float(data[4].string.replace(',', '')),
                         'daily_low': float(data[5].string.replace(',', '')),
                         'turnover': None,
                         'volume': float(data[1].string.replace(',', '')),
                         'constituent_id':"DAX",
                         'constituent_name':"DAX"
                         })
        except Exception as e:
            print(e)
    else:
        while table_row.find_next_sibling('tr'):
            data = table_row.find_all('td')
            try:
                date = datetime.strptime(data[0].string, "%d/%m/%Y")
                date_string = date.strftime('%Y-%m-%d %H:%M:%S')

                rows.append({'constituent': constituent_old_name,
                             'date':date_string,
                             'opening_price': float(data[1].string.replace(',', '')),
                             'closing_price': float(data[2].string.replace(',', '')),
                             'daily_high': float(data[3].string.replace(',', '')),
                             'daily_low': float(data[4].string.replace(',', '')),
                             'turnover': float(data[5].string.replace(',', '')),
                             'volume': float(data[6].string.replace(',','')),
                             'constituent_name':constituent_name,
                            'constituent_id':constituent_id
                })
            except AttributeError as e:
                print(e)

            table_row = table_row.find_next_sibling('tr')

        data = table_row.find_all('td')

        try:
            date = datetime.strptime(data[0].string, "%d/%m/%Y")
            date_string = date.strftime('%Y-%m-%d %H:%M:%S')

            rows.append({'constituent': constituent_old_name,
                         'date': date_string,
                         'opening_price': float(data[1].string.replace(',', '')),
                         'closing_price': float(data[2].string.replace(',', '')),
                         'daily_high': float(data[3].string.replace(',', '')),
                         'daily_low': float(data[4].string.replace(',', '')),
                         'turnover': float(data[5].string.replace(',', '')),
                         'volume': float(data[6].string.replace(',', '')),
                         'constituent_name':constituent_name,
                         'constituent_id':constituent_id
                         })
        except AttributeError as e:
            print(e)

    try:
        storage_client.insert_bigquery_data(dataset_name, table_name, rows)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('python_path', help='The connection string')
    parser.add_argument('google_key_path', help='The path of the Google key')
    parser.add_argument('param_connection_string', help='The connection string')
    parser.add_argument('environment', help='production or test')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-a", "--all", action="store_true", help='save historical data for all constituents')
    group.add_argument("-c", "--constituent", help="save historical data for specific constituent")
    args = parser.parse_args()
    sys.path.insert(0, args.python_path)
    from utils.Storage import Storage
    from utils import twitter_analytics_helpers as tah
    main(args)