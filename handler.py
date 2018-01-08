import os
dir_path = os.path.dirname(os.path.realpath(__file__))
import sys
sys.path.append(dir_path + "/lib/")

from hesburgh import heslog, hesutil
import json
import re
import shared

unrecognizedEvent = { "statusCode": 422, "body": "Unrecognized event." }
invalidEntry = { "statusCode": 422, "body": "Invalid Contentful entry." }

def hook(event, context):
  heslog.setContext({})
  heslog.addLambdaContext(event, context)

  headers = event.get("headers", {})
  if not headers:
    return unrecognizedEvent
  cfTopic = headers.get("X-Contentful-Topic")
  if cfTopic is None:
    heslog.error("No CF Topic")
    return unrecognizedEvent

  topicMatch = re.search(r'^ContentManagement.Entry.(.*)', cfTopic)
  if topicMatch is None:
    heslog.error("No topic match")
    return unrecognizedEvent

  eventType = topicMatch.group(1)
  heslog.addContext(topic=eventType)
  if eventType != "auto_save":
    heslog.info("Topic is not one we care about")
    return { "statusCode": 304, "body": "" }

  body = json.loads(event.get("body", ""))

  sysId = body.get('sys', {}).get('id')
  if sysId is None:
    heslog.error("No sysId")
    return invalidEntry

  alephNumber = body.get("fields", {}).get("alephSystemNumber", {}).get("en-US")
  heslog.addContext(aleph=alephNumber)
  if not alephNumber:
    heslog.error("No Aleph number")
    return { "statusCode": 304, "body": "No aleph number found" }

  alephItem = shared.getAleph(alephNumber)
  fields = body.get("fields", {})

  # If anything is different, update it
  #  This should stop a potential infinite update loop
  if shared.isDifferent(alephItem, fields):
    shared.updateContentful(sysId, body.get("sys", {}).get("version", 1), alephItem, fields)

  heslog.info("Returning 200 OK")
  return { "statusCode": 200, "body": "" }
