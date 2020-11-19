import requests
import json
import boto3
from decimal import Decimal
import datetime



API_KEY = 'K2kU0N2tMsKGZ33YpchEn2-82WpU_j7EeN43F7p56ep1c3c5VboTBzuKk0TEsalnTV5fbqFH98Lp3KDuXUeLotNaJso9oYDJaZdDTyMfTt21ja-UCQ081BNCn-aEX3Yx'
HEADERS = {'Authorization': 'bearer %s' % API_KEY}





def DetailedInfo(business_id):
    END_POINT = 'https://api.yelp.com/v3/businesses/{}'.format(business_id)
    response = requests.get(url=END_POINT,headers= HEADERS )


def search(term):
    END_POINT = 'https://api.yelp.com/v3/businesses/search'
    for offset in range(0, 1, 1):
        PARAMETERS = {
            'term' : 'Food',
            'limit': 5,
            'location': 'manhattan',
            'offset': offset
        }
        PARAMETERS['term']=term
        response = requests.get(url=END_POINT,params =PARAMETERS,headers= HEADERS )
        outputData(response,term)



def outputData(response,term):
    business_data = response.json()
    db = boto3.resource('dynamodb')
    table = db.Table('YelpRestaurant')

    for data in business_data['businesses']:
     
        business_id = data['id']

        END_POINT = 'https://api.yelp.com/v3/businesses/{}'.format(business_id)
        reps = requests.get(url=END_POINT,headers= HEADERS ).json()

        reps['cuisine'] =term
        reps['Timestamp'] =datetime.datetime.now().isoformat()

        reps = json.loads(json.dumps(reps), parse_float=Decimal)
        table.put_item(Item = reps) 

    


terms=['French','Japanese','Chinese','Italian','Indian','Fast Food', 'Breakfast','Cafeteria']
for term in terms:
    search(term)
    print(term,'is done')


