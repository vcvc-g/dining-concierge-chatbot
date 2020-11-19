import json
import datetime
import os
import time
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):

    client = boto3.client('lex-runtime')
 
    
    userInput = event["messages"][0]['unstructured']['text']

    response = client.post_text(
        botName="MyLittleBot",
        botAlias="dinBot",
        userId='user',#+str(datetime.datetime.now()).replace(" ",""),
        sessionAttributes={
        },
        requestAttributes={
        },
        inputText= userInput
    )
    
    
    return {
        'headers': {
            'Access-Control-Allow-Origin': '*'
            
        },
        'messages': [ 
            {
            'type': "unstructured",
            'unstructured': {'text':response['message']}
            } 
        ]
    }
    
    