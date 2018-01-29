# This allows gevent to be imported from the ./lib diretory
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
import sys
sys.path.append(dir_path + "/lib/")

import gevent.monkey
gevent.monkey.patch_all()
import gevent

from hesburgh import heslog, hesutil
import json
import re
import shared
import urllib2
import time

# Issue: the first response that returns the api limit header will have actually gone through
# successfully - all the subsequent calls will fail until the limit is lifted. This is great
# except that we're in threads so we don't know if we're the first one to hit the error or not
# so we retry everything. If we retry a previously successful call we'll now get a version mismatch error

# The contentful calls per second is 10, so do 5 at a time (update + publish = 10 max calls) to get around ^ issue
concurentItems = 5


def updateItem(item):
  fields = item.get("fields", {})

  alephNumber = item.get("fields", {}).get("alephSystemNumber", {}).get("en-US")
  sysId = item.get('sys', {}).get('id')

  if not alephNumber:
    heslog.warn("No Aleph number for %s" % (sysId))
    return None

  alephItem = shared.getAleph(alephNumber)
  if not alephItem:
    heslog.warn("Couldn't find item %s" % alephNumber)
    return None

  if shared.isDifferent(alephItem, fields):
    version = item.get("sys", {}).get("version", 1)

    updated = shared.updateContentful(sysId, version, alephItem, fields)
    if not updated:
      return
    shared.publishContentful(sysId, updated.get("sys", {}).get("version", 1))


def run(event, context):
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

  start = 0

  timer = hesutil.Timer()
  while len(items) > 0:
    threads = []
    use = items[:concurentItems]
    items = items[concurentItems:]

    heslog.info("Processing items %s through %s" % (start, start + len(use) - 1))
    start += concurentItems
    timer.start()
    for item in use:
      threads.append(gevent.spawn(updateItem, item))

    gevent.joinall(threads)
    dt = timer.end()
    # sleep to make it less likely we hit the contentful api limit
    time.sleep(1)


  heslog.info("Returning 200 OK")
  return { "statusCode": 200, "body": "" }
