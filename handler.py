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
  currentTitle = body.get("fields", {}).get("title", {}).get("en-US")
  currentDesc = body.get("fields", {}).get("description", {}).get("en-US")
  currentPurl = body.get("fields", {}).get("purl", {}).get("en-US")

  # If anything is different, update it
  #  This should stop a potential infinite update loop
  if (currentDesc != alephItem.get("description")
      or currentPurl != alephItem.get("purl")):
    alephItem["systemNumber"] = alephNumber
    alephItem["name"] = currentTitle
    shared.updateContentful(sysId, body.get("sys", {}).get("version", 1), alephItem)

  heslog.info("Returning 200 OK")
  return { "statusCode": 200, "body": "" }
