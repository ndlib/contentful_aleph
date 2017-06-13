from hesburgh import heslog, hesutil
import json
import re
import shared
import urllib2

def run(event, context):
  heslog.setContext({})
  heslog.addLambdaContext(event, context)

  start = 0
  total = 100

  headers = {
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
  }
  baseUrl = hesutil.getEnv("CONTENTFUL_QUERY_URL", throw=True)

  items = []
  while start < total:
    url = baseUrl + "&skip=%s" % (start)

    req = urllib2.Request(url, headers=headers)
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

    responseObj = json.loads(response.read())

    start = responseObj.get("skip", 0) + responseObj.get("limit", 100)
    total = responseObj.get("total", 0)

    responseItems = responseObj.get("items", [])
    for item in responseItems:
      if item.get("sys", {}).get("archivedAt", None) is None:
        items.append(item)

  heslog.info("Updating %s items" % len(items))

  for item in items:
    currentTitle = item.get("fields", {}).get("title", {}).get("en-US")
    currentDesc = item.get("fields", {}).get("description", {}).get("en-US")
    currentPurl = item.get("fields", {}).get("purl", {}).get("en-US")

    alephNumber = item.get("fields", {}).get("alephSystemNumber", {}).get("en-US")
    heslog.addContext(aleph=alephNumber)
    if not alephNumber:
      heslog.error("No Aleph number for %s" % json.dumps(item))
      continue

    alephItem = shared.getAleph(alephNumber)
    heslog.debug("number: %s, title: %s" % (alephNumber, currentTitle))
    heslog.debug(json.dumps(alephItem))

    sysId = item.get('sys', {}).get('id')

    if (currentDesc != alephItem.get("description")
        or currentPurl != alephItem.get("purl")):
      alephItem["systemNumber"] = alephNumber
      alephItem["name"] = currentTitle
      # shared.updateContentful(sysId, item.get("sys", {}).get("version", 1), alephItem)
    else:
      heslog.info("Item is the same, not updating")

  heslog.info("Returning 200 OK")
  return { "statusCode": 200, "body": "" }