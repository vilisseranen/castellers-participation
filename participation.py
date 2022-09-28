#!/usr/bin/env python3

import configparser
import requests
import json
import argparse
from datetime import date

BASE_URL = "https://api.amunt.castellersdemontreal.info/api/v1/"

def read_creds():
    config = configparser.ConfigParser()
    config.read('creds')
    return (config['default']['username'], config['default']['password'])

def get_token():
    global token
    creds= read_creds()
    r = requests.post(BASE_URL+'login', json={"username":creds[0], 'password': creds[1]})
    token = json.loads(r.text)["access_token"]

def parse_args():
    global start, end, output, show_inscriptions, show_absents
    parser = argparse.ArgumentParser(description='Get participation and presence for castellers.')
    parser.add_argument('--show-inscriptions', type=bool, default=False, action=argparse.BooleanOptionalAction, help='Also show if the member was registered for the event or not.')
    parser.add_argument('--show-absents', type=bool, default=False, action=argparse.BooleanOptionalAction, help='Hide members that were never registered or present.')
    parser.add_argument('start', type=int, help='Timestamp for start of period.')
    parser.add_argument('end', type=int, help='Timestamp for end of period.')
    parser.add_argument('output', type=str, help='output file')
    args = parser.parse_args()
    start = args.start
    end = args.end
    output = args.output
    show_inscriptions = args.show_inscriptions
    show_absents = args.show_absents

def list_events():
    events_to_keep = []
    # Cheking 50 events before today and 20 after today
    r = requests.get(BASE_URL+'events?page=-1&limit=50', headers={'Authorization': 'Bearer: ' + token})
    events = json.loads(r.text)
    print("#events avant: {}".format(len(events)))
    r = requests.get(BASE_URL+'events?page=1&limit=50', headers={'Authorization': 'Bearer: ' + token})
    events += json.loads(r.text)
    for event in events:
        print(event)
        if event['endDate'] > start and event['startDate'] < end:
            events_to_keep.append(event)
    events_to_keep.sort(key = lambda x:x['startDate'])
    return events_to_keep

def list_members():
    r = requests.get(BASE_URL+'members', headers={'Authorization': 'Bearer: ' + token})
    return json.loads(r.text)

def get_participation(events, members):
    participation = {}
    for event in events:
        participation[event['uuid']] = {}
        r = requests.get(BASE_URL+'events/{}/members'.format(event['uuid']), headers={'Authorization': 'Bearer: ' + token})
        for member in json.loads(r.text):
            participation[event['uuid']][member['uuid']] = { "participation": member['participation'], "presence": member['presence']}
    return participation

def write_csv(events, members, participation):
    csv =[]
    header = ["", ""]
    subheader = ["Nom", "Type"]
    for event in events:
        header.append("{} {}".format(event["name"], date.fromtimestamp(event["startDate"])))
        if show_inscriptions:
            header.append("")
            subheader.append("inscription")
        subheader.append("presence")
    csv.append(",".join(header))
    csv.append(",".join(subheader))
    for member in members:
        always_absent = True
        line = ["{} {}".format(member["firstName"], member["lastName"])]
        line.append(member["type"])
        for event in events:
            inscription = participation[event['uuid']][member['uuid']]['participation']
            presence =  participation[event['uuid']][member['uuid']]['presence']
            if inscription and show_inscriptions:
                line.append(inscription)
                if inscription == "yes":
                    always_absent = False
            elif show_inscriptions:
                line.append("no")
            if presence:
                line.append(presence)
                if presence == "yes":
                    always_absent=False
            elif inscription == "yes" and presence != 'no':
                line.append("yes")
                always_absent=False
            else:
                line.append("no")

        if not always_absent or show_absents:
            csv.append(",".join(line))
    with open(output, 'w') as f:
        for line in csv:
            f.write(line)
            f.write('\n')


if __name__ == "__main__":
    parse_args()
    get_token()
    events = list_events()
    members = list_members()
    participation = get_participation(events, members)
    write_csv(events, members, participation)
