from hesburgh import heslog, hesutil
import json
import re
import urllib2
import urllib

unrecognizedEvent = { "statusCode": 422, "body": "Unrecognized event." }
invalidEntry = { "statusCode": 422, "body": "Invalid Contentful entry." }

def getAleph(alephNumber):
  url = hesutil.getEnv("ALEPH_URL", throw=True)
  url = url.replace("<<systemNumber>>", alephNumber)

  req = urllib2.Request(url)
  response = ""
  try:
    response = urllib2.urlopen(req)
  except urllib2.HTTPError as e:
    heslog.error("%s" % e.code)
    heslog.error(e.read())
    return None
  except urllib2.URLError as e:
    heslog.error(e.reason)
    return None

  return json.loads(response.read())


def updateContentful(entryId, version, updateInfo):
  heslog.addContext(version=version)
  url = hesutil.getEnv("CONTENTFUL_URL", throw=True)
  url = url.replace("<<entryId>>", entryId)

  data = {
    "fields": {
      "title": {
        "en-US": updateInfo.get("name"),
      },
      "description": {
        "en-US": updateInfo.get("description"),
      },
      "purl": {
        "en-US": updateInfo.get("purl"),
      },
      "alephSystemNumber": {
        "en-US": updateInfo.get("systemNumber"),
      }
    }
  }

  headers = {
    "Content-Type": "application/vnd.contentful.management.v1+json",
    "X-Contentful-Content-Type": "resource",
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
    "X-Contentful-Version": version,
  }

  req = urllib2.Request(url, data=json.dumps(data), headers=headers)
  req.get_method = lambda: 'PUT'
  try:
    urllib2.urlopen(req)
  except urllib2.HTTPError as e:
    heslog.error("%s" % e.code)
    heslog.error(e.read())
  except urllib2.URLError as e:
    heslog.error(e.reason)


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
    return { "statusCode": 422, "body": "No aleph number found" }

  alephItem = getAleph(alephNumber)
  currentTitle = body.get("fields", {}).get("title", {}).get("en-US")
  currentDesc = body.get("fields", {}).get("description", {}).get("en-US")
  currentPurl = body.get("fields", {}).get("purl", {}).get("en-US")

  # If anything is different, update it
  #  This should stop a potential infinite update loop
  if (currentDesc != alephItem.get("description")
      or currentPurl != alephItem.get("purl")):
    alephItem["systemNumber"] = alephNumber
    alephItem["name"] = currentTitle
    updateContentful(sysId, body.get("sys", {}).get("version", 1), alephItem)

  heslog.info("Returning 200 OK")
  return { "statusCode": 200, "body": "" }
