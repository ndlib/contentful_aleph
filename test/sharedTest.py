import unittest
from mock import Mock, patch
import shared
from hesburgh import hesutil
import json
import os

class SharedTestCase(unittest.TestCase):

  def makeField(self, data):
    return { "en-US": data }


  def getField(self, data, key):
    if "fields" in data:
      return data.get("fields").get(key, {}).get("en-US")
    elif key in data:
      return data.get(key).get("en-US")


  def setUp(self):
    self.alephUrl = "http://aleph/<<systemNumber>>"
    os.environ["ALEPH_URL"] = self.alephUrl
    self.contentfulUrl = "https://contentful"
    os.environ["CONTENTFUL_URL"] = self.contentfulUrl
    self.oauth = "oauthToken"
    os.environ["OAUTH"] = self.oauth

    self.alephItem = {
      "name": "test",
      "description": "desc",
      "purl": "test.com",
      "urls": [{ "url": "test.com", "title": "test" }, {"url": "google.com", "title": "google"}],
      "alephSystemNumber": 2,
    }

    self.cfIdenticalItem = {
      "title": self.makeField(self.alephItem.get("name")),
      "description": self.makeField(self.alephItem.get("description")),
      "purl": self.makeField(self.alephItem.get("purl")),
      "urls": self.makeField(self.alephItem.get("urls")),
      "alephSystemNumber": self.makeField(0),
    }

    self.cfDifferentItem = {
      "title": self.makeField("different"),
      "description": self.makeField("this is a different item"),
      "purl": self.makeField("such.wow"),
      "urls": self.makeField([ { "url": "such.wow", "title": None } ]),
      "alephSystemNumber": self.makeField(1),
    }


  def test_is_different_true(self):
    isDifferent = shared.isDifferent(self.alephItem, self.cfDifferentItem)
    self.assertTrue(isDifferent)


  def test_is_different_false(self):
    isDifferent = shared.isDifferent(self.alephItem, self.cfIdenticalItem)
    self.assertFalse(isDifferent)


  def test_getAleph_call(self):
    with patch('shared.makeRequest', autospec=True) as mockedRequester:
      mockedRequester.return_value = True

      alephNumber = "0"
      shared.getAleph(alephNumber)

      self.assertEqual(mockedRequester.call_count, 1)

      passedUrl = mockedRequester.call_args[0][0].get_full_url()
      matchUrl = self.alephUrl.replace("<<systemNumber>>", alephNumber)
      self.assertEqual(passedUrl, matchUrl)


  def test_updateContentful_data_change(self):
    with patch('shared.makeRequest', autospec=True) as mockedRequester:
      mockedRequester.return_value = True

      entryId = "0"
      version = 0
      shared.updateContentful(entryId, version, self.alephItem, self.cfDifferentItem)

      passedRequest = mockedRequester.call_args[0][0]
      passedData = json.loads(passedRequest.get_data())

      self.assertEqual(self.getField(passedData, "title"), self.alephItem.get("name"))


  def test_updateContentful_keep_system_number(self):
    with patch('shared.makeRequest', autospec=True) as mockedRequester:
      mockedRequester.return_value = True

      entryId = "0"
      version = 0
      shared.updateContentful(entryId, version, self.alephItem, self.cfIdenticalItem)

      passedRequest = mockedRequester.call_args[0][0]
      passedData = json.loads(passedRequest.get_data())

      self.assertEqual(self.getField(passedData, "alephSystemNumber"), self.getField(self.cfIdenticalItem, "alephSystemNumber"))


def Suite():
  return unittest.TestLoader().loadTestsFromTestCase(SharedTestCase)

