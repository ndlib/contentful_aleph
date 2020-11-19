const nock = require('nock')
const { getAleph, isDifferent, updateContentful, publishContentful } = require('../../src/shared/helpers')

const makeField = (data) => {
  return {
    'en-US': data,
  }
}

const getField = (data, key) => {
  if (data.fields) {
    return data.fields[key]['en-US']
  } else if (data[key]) {
    return data[key]['en-US']
  }
}

describe('shared/helpers', () => {
  beforeEach(() => {
    jest.useFakeTimers()
    console.warn = jest.fn()
  })

  const alephItem = {
    name: 'test',
    description: 'desc',
    purl: 'test.com',
    urls: [{ url: 'test.com', title: 'test' }, { url: 'google.com', title: 'google' }],
    alephSystemNumber: 2,
  }

  const cfIdenticalItem = {
    title: makeField(alephItem.name),
    databaseLetter: makeField(alephItem.name[0].toLowerCase()),
    description: makeField(alephItem.description),
    purl: makeField(alephItem.purl),
    urls: makeField(alephItem.urls),
    alephSystemNumber: makeField(0),
  }

  const cfDifferentItem = {
    title: makeField('different'),
    description: makeField('this is a different item'),
    purl: makeField('such.wow'),
    urls: makeField([
      { url: 'such.wow', title: null },
    ]),
    alephSystemNumber: makeField(1),
  }

  describe('isDifferent', () => {
    it('should return true for objects with differences', () => {
      const result = isDifferent(alephItem, cfDifferentItem)
      expect(result).toBe(true)
    })

    it('should return false for equivalent objects', () => {
      const result = isDifferent(alephItem, cfIdenticalItem)
      expect(result).toBe(false)
    })
  })

  describe('getAleph', () => {
    it('should fetch from Aleph Gateway API', async () => {
      const alephNumber = '0'
      const fetchNock = nock(process.env.ALEPH_GATEWAY_URL)
        .get(`/${alephNumber}`)
        .query(true)
        .reply(200, {})

      await getAleph(alephNumber)

      expect(fetchNock.isDone()).toBe(true)
    })

    it('should retry if a 504 Gateway Timeout response is received', async () => {
      const alephNumber = '0'
      const timeout = 1234
      const responseHeaders = {
        'X-Contentful-RateLimit-Reset': timeout,
      }

      const fetchNock = nock(process.env.ALEPH_GATEWAY_URL)
        .get(`/${alephNumber}`)
        .query(true)
        .reply(504, null, responseHeaders)

      await getAleph(alephNumber)

      expect(fetchNock.isDone()).toBe(true)
      expect(setTimeout).toHaveBeenLastCalledWith(expect.any(Function), timeout)
    })
  })

  describe('updateContentful', () => {
    const entryId = '1234'
    const version = 3
    let updateNock

    beforeEach(() => {
      updateNock = nock(process.env.CONTENTFUL_CMA_URL)
        .intercept(`/entries/${entryId}`, 'PUT')
        .query(true)
        .reply(200, (uri, requestBody) => requestBody)
    })

    it('should update record fields EXCEPT title', async () => {
      // Ensure the fields are different so we'll know if they change
      expect(getField(cfDifferentItem, 'description')).not.toEqual(alephItem.description)
      expect(getField(cfDifferentItem, 'title')).not.toEqual(alephItem.name)

      const body = await updateContentful(entryId, version, alephItem, cfDifferentItem)

      expect(updateNock.isDone()).toBe(true)

      expect(getField(body, 'description')).toEqual(alephItem.description)
      expect(getField(body, 'title')).not.toEqual(alephItem.name)
      expect(getField(body, 'title')).toEqual(getField(cfDifferentItem, 'title'))
    })
  })

  describe('publishContentful', () => {
    it('should call the Contentful CMA publish endpoint', async () => {
      const entryId = '1234'
      const updateNock = nock(process.env.CONTENTFUL_CMA_URL)
        .intercept(`/entries/${entryId}/published`, 'PUT')
        .query(true)
        .reply(200, {})

      await publishContentful(entryId, '0')

      expect(updateNock.isDone()).toBe(true)
    })
  })
})
