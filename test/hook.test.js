const nock = require('nock')
const hook = require('../src/hook')

const alephNumber = '0995150'
const entryId = '1234'

const mockAlephFetch = (response) => {
  return nock(process.env.ALEPH_GATEWAY_URL)
    .get(`/${alephNumber}`)
    .query(true)
    .reply(200, response)
}

describe('hook', () => {
  describe('valid request', () => {
    const event = {
      body: JSON.stringify({
        sys: {
          id: entryId,
          version: 1,
        },
        fields: {
          alephSystemNumber: {
            'en-US': alephNumber,
          },
          title: {
            'en-US': 'aleph item',
          },
          databaseLetter: {
            'en-US': 'a',
          },
        },
      }),
      headers: {
        'X-Contentful-Topic': 'ContentManagement.Entry.auto_save',
      },
    }

    let alephNock, updateNock

    beforeEach(() => {
      updateNock = nock(process.env.CONTENTFUL_CMA_URL)
        .intercept(`/entries/${entryId}`, 'PUT')
        .query(true)
        .reply(200, {})
    })

    afterEach(() => {
      nock.cleanAll()
      alephNock = undefined
      updateNock = undefined
    })

    it('should NOT call update if nothing has changed', async () => {
      alephNock = mockAlephFetch({
        name: 'aleph item',
      })

      await hook.handler(event, null, () => {
        expect(alephNock.isDone()).toBe(true)
        expect(updateNock.isDone()).toBe(false)
      })
    })

    it('should update if any field is changed', async () => {
      alephNock = mockAlephFetch({
        name: 'aleph item',
        description: 'new desc',
      })

      await hook.handler(event, null, () => {
        expect(alephNock.isDone()).toBe(true)
        expect(updateNock.isDone()).toBe(true)
      })
    })
  })

  describe('invalid request', () => {
    beforeEach(() => {
      console.warn = jest.fn()
      console.error = jest.fn()
    })

    it('should return 422 if no headers', async () => {
      const event = {
        body: JSON.stringify({
          sys: {
            id: entryId,
            version: 1,
          },
          fields: {
            alephSystemNumber: {
              'en-US': alephNumber,
            },
            databaseLetter: {
              'en-US': 'a',
            },
          },
        }),
      }

      await hook.handler(event, null, (ignore, response) => {
        expect(response.statusCode).toEqual(422)
      })
    })

    it('should return 422 if missing X-Contentful-Topic header', async () => {
      const event = {
        body: JSON.stringify({
          sys: {
            id: entryId,
            version: 1,
          },
          fields: {
            alephSystemNumber: {
              'en-US': alephNumber,
            },
            databaseLetter: {
              'en-US': 'a',
            },
          },
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      }

      await hook.handler(event, null, (ignore, response) => {
        expect(response.statusCode).toEqual(422)
      })
    })

    it('should return 422 if X-Contentful-Topic header does not match expected Contentful topic pattern', async () => {
      const event = {
        body: JSON.stringify({
          sys: {
            id: entryId,
            version: 1,
          },
          fields: {
            alephSystemNumber: {
              'en-US': alephNumber,
            },
            databaseLetter: {
              'en-US': 'a',
            },
          },
        }),
        headers: {
          'X-Contentful-Topic': 'ContentfulTopicInvalid',
        },
      }

      await hook.handler(event, null, (ignore, response) => {
        expect(response.statusCode).toEqual(422)
      })
    })

    it('should return 304 if X-Contentful-Topic header is not auto_save', async () => {
      const event = {
        body: JSON.stringify({
          sys: {
            id: entryId,
            version: 1,
          },
          fields: {
            alephSystemNumber: {
              'en-US': alephNumber,
            },
            databaseLetter: {
              'en-US': 'a',
            },
          },
        }),
        headers: {
          'X-Contentful-Topic': 'ContentManagement.Entry.testInvalidValue',
        },
      }

      await hook.handler(event, null, (ignore, response) => {
        expect(response.statusCode).toEqual(304)
      })
    })

    it('should return 422 if body is not a contentful object', async () => {
      const event = {
        body: JSON.stringify({
          foo: 'bar',
        }),
        headers: {
          'X-Contentful-Topic': 'ContentManagement.Entry.auto_save',
        },
      }

      await hook.handler(event, null, (ignore, response) => {
        expect(response.statusCode).toEqual(422)
      })
    })

    it('should return 304 if aleph number is missing', async () => {
      const event = {
        body: JSON.stringify({
          sys: {
            id: entryId,
            version: 1,
          },
          fields: {
            databaseLetter: {
              'en-US': 'a',
            },
          },
        }),
        headers: {
          'X-Contentful-Topic': 'ContentManagement.Entry.auto_save',
        },
      }

      await hook.handler(event, null, (ignore, response) => {
        expect(response.statusCode).toEqual(304)
      })
    })
  })
})
