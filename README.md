# Contentful Aleph
This project defines functions that sync aleph information into contentful.

## Overview
The gateway defines
```
POST /hook
```
which is the webhook given to contentful to run on entry updates. This hook
only updates contentful when it is a `resource` type and if it is different than what's in aleph
(meaning it's out of date).

This project also contians a sync function. This function runs each night and attempts to update
all contentful resource records with they're correct aleph data. This function *currently times out*
as there are too many entries for one lambda to get through in 5 minutes - this will need to be changed to be smarter
at some point. It currently doesn't cause issues, as the order it goes through contentful is random, so it may
get through all entries given enough days.

## Deployment
### Requires
- [hesdeploy](https://github.com/ndlib/hesburgh_utilities/blob/master/scripts/HESDEPLOY.md) (pip install hesdeploy)
- Access to corpfs
- AWS Credentials

### To deploy
assume the appropriate role
`source cfis:/DSNS/Library/Departmental/Infrastructure/vars/WSE/secret_[stage]/contentful_aleph/deploy-env`
`hesdeploy --[create|update]`