# Example / utility scripts for Flickr API

- corectflickrdate:  Correct a bad "date taken" for a group of photos on Flickr (beyond the max 24 hour shift in the Flickr Organizr)
- removetag: remove a tag from photos (seach by tag) because there is a bug sometimes in the Flickr UI where you cannot batch delete tags within the camera roll
- list_albums: list your own albums ordered by creation date

## API Key

Needs a JSON file named `api_key.json` with a key and secret for the API:

```json
{
    "key":"abcdef1235",
    "secret":"12376abcdf"
}
```

## Other

Find NSID By URL (for serching albums for example):

https://www.flickr.com/services/api/flickr.urls.lookupUser.html


## Python version

Needs Python 3.6
