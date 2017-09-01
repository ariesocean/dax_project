import sys
sys.path.insert(0, '../utils')
from DB import DB
from sortedcontainers import SortedListWithKey
from collections import defaultdict
import math
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

'''
argv[0]: connection_string
argv[1]: database
argv[2]: number of days back to collect tweets from
'''
def main(argv):

    database = DB(argv[0], argv[1])
    col = database.get_collection('tweets')

    d = datetime.today() - timedelta(days=7)

    cursor = col.find({'constituent': "BMW", "date":{"$gte":d}}, {"_id": -1, "id_str": 1, "favorite_count": 1,
                                                "retweet_count": 1, "text": 1, "processed_text": 1, "place": 1,
                                                "user": 1})
    results = list(cursor)

    stock = 9
    low = stock*0.8
    high = stock*1.2


    #prices = price_analytics(results,low,high)
    #print("Prices")
    #print_prices(prices)
    #print("Countries")
    #print_countries(results)
    countries = get_countries(results, low, high)
    make_chart(countries, "BMW")


def general_analytics(cursor: list):
    vocabulary = defaultdict(int)
    top_retweeted = SortedListWithKey(key=lambda x: x["retweet_count"])
    top_fav = SortedListWithKey(key=lambda x: x["favorite_count"])
    top_followed = SortedListWithKey(key=lambda x: x["user"]['followers_count'])
    prices = []

    for tweet in cursor:
        text = tweet["processed_text"]

        for word in tweet["processed_text"]:
            vocabulary[word] += 1

        top_retweeted.add(tweet)
        if len(top_retweeted) > 50:
            top_retweeted.pop(0)

        top_fav.add(tweet)
        if len(top_fav) > 500:
            top_fav.pop(0)

        top_followed.add(tweet)
        if len(top_followed) > 50:
            top_followed.pop(0)

    return vocabulary, top_retweeted, top_fav, top_followed

def price_analytics(cursor:list, low, high):
    prices = []
    for tweet in cursor:
        text = tweet["processed_text"]

        for word in tweet["processed_text"]:
            try:
                number = float(word)
                if number < high and number > low:
                    prices.append((number, tweet))
            except:
                pass

    return prices

def print_prices(prices):
    prices.sort(key=lambda x: x[0], reverse=True)
    prices_only, tweets = zip(*prices)

    total = sum(prices_only)
    print("Highest price: {}".format(prices_only[0]))
    print("Lowest price: {}".format(prices_only[-1]))

    prices_frequency = defaultdict(int)
    for p in prices_only:
        prices_frequency[math.ceil(p)] += 1

    print("General Twitter target prices:")
    sorted_by_frequency = sorted(prices_frequency.items(), key=lambda x: x[1], reverse=True)

    if len(prices_only) == 0:
        print("No price information available")
        return


    for p1, p2 in sorted_by_frequency:
        percent = p2*100/len(prices_only)
        #if percent > 10:
        print("EUR {} ({}%)".format(p1, float(percent)))


    #Get prices mentioned more often by influencers
    influencer_prices = []
    for price, tweet in prices:
        if tweet['user']['followers_count'] >= 200:
            influencer_prices.append(price)

    influencer_frequency = defaultdict(int)
    for p in influencer_prices:
        influencer_frequency[math.ceil(p)] += 1

    influencer_frequency_sorted = sorted(influencer_frequency.items(), key=lambda x: x[1], reverse=True)

    if len(influencer_prices) < 0:
        return
    print("Top influencers target prices:")
    for p1, p2 in influencer_frequency_sorted:
        percent = p2*100/len(influencer_prices)
        #if percent > 10:
        print("EUR {} ({}%)".format(p1, float(percent)))

def print_results(results:list):
    for item in reversed(results):
        print(item['semi_processed_text'])

def print_term_results(vocabulary:dict):
    for key,word in [('recal',"Recall"), ('sale','Sales'), ('financi', 'Financial'), ('bearish','Bearish'),
                ('bullish', 'Bullish')]:
        if key in vocabulary:
            print("{}:{}".format(word, vocabulary[key]))

'''
returns: a list of (country,percent) tuples
'''
def get_countries(cursor:list, low, high):
    countries = defaultdict(float)

    for tweet in cursor:
        for word in tweet["processed_text"]:
            try:
                number = float(word)
                if number < high and number > low:
                    if tweet['place'] is not None:
                        if 'country_code' in tweet['place'].keys():
                            countries[tweet['place']['country_code']] += 1
                    break
            except:
                pass

    if len(countries) < 0:
        return None

    for key in countries.keys():
        countries[key] = countries[key]

    return sorted(countries.items(), key=lambda x: x[1], reverse=True)


'''
data: can be list of (label,value)
'''
def make_chart(data:list, constituent):

    #labels = 'Frogs', 'Hogs', 'Dogs', 'Logs'
    #sizes = [15, 30, 45, 10]
    #explode = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')
    labels, sizes = zip(*data)

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    plt.savefig('./charts/countries_{}.png'.format(constituent), bbox_inches='tight')

    #plt.show()








if __name__ == "__main__":
    main(sys.argv[1:])