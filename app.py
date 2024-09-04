import argparse
import collections
import datetime
import os
from pprint import pprint
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession



def main(secret_file):
  creds = None

  if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/photoslibrary.readonly'])

  if not creds or not creds.valid:
    flow = InstalledAppFlow.from_client_secrets_file(
        secret_file,
        scopes=['https://www.googleapis.com/auth/photoslibrary.readonly']
    )

    creds = flow.run_local_server()
    with open('token.json', 'w') as token:
      token.write(creds.to_json())

  session = AuthorizedSession(creds)

  all_photos = []

  if os.path.exists('all_photos.pickle'):
    all_photos = pickle.load( open("all_photos.pickle", "rb" ))
    print('Reloaded {} photos'.format(len(all_photos)))
  else:
    next_page_token = None
    page_number = 0

    while page_number == 0 or next_page_token:
      page_number += 1
      print('Fetching media items from page {}'.format(page_number))

      media_items_request = session.request('GET', 'https://photoslibrary.googleapis.com/v1/mediaItems?{}'.format(
        ('pageToken={}'.format(next_page_token)) if next_page_token else ''
      ))
      media_items_response = media_items_request.json()

      if 'mediaItems'  in media_items_response:
        media_items = media_items_response['mediaItems']
        print('Fetched {} media items'.format(len(media_items)))

        all_photos += media_items

      print('So far {} media items.'.format(len(all_photos)))
      next_page_token = media_items_response.get('nextPageToken', None)

    print('Totally fetched {} photos'.format(len(all_photos)))
    pickle.dump( all_photos, open( 'all_photos.pickle', "wb" ) )


  all_albums = []
  if os.path.exists('albums.pickle'):
    all_albums = pickle.load( open("albums.pickle", "rb" ))
    print('Reloaded {} albums'.format(len(all_albums)))
  else:

    next_page_token = None
    page_number = 0

    while page_number == 0 or next_page_token:
      page_number += 1
      print('Fetching albums from page {}'.format(page_number))

      albums_request = session.request('GET', 'https://photoslibrary.googleapis.com/v1/albums?{}'.format(
        ('pageToken={}'.format(next_page_token)) if next_page_token else ''
      ))
      albums_response = albums_request.json()

      albums = albums_response.get('albums', None)
      if not albums:
        albums = []
      print('Fetched {} albums'.format(len(albums)))

      all_albums += albums

      print('So far {} albums.'.format(len(all_albums)))
      next_page_token = albums_response.get('nextPageToken', None)

    print('Totally fetched {} albums'.format(len(all_albums)))
    pickle.dump( all_albums, open( 'albums.pickle', "wb" ) )

  album_photos = []
  if os.path.exists('album_photos.pickle'):
    album_photos = pickle.load( open("album_photos.pickle", "rb" ))
    print('Reloaded {} photos from albums'.format(len(album_photos)))
  else:
    for album_index, album in enumerate(all_albums):
      print('Processing album {}/{} {}'.format(album_index, len(all_albums), album['title']))

      next_page_token = None
      page_number = 0

      while page_number == 0 or next_page_token:
        page_number += 1
        print('Fetching album photos for album {} from page {}'.format(album['title'], page_number))

        media_items_request = session.request('POST', 'https://photoslibrary.googleapis.com/v1/mediaItems:search', data={
          'albumId': album['id'],
          'pageToken': next_page_token
        })
        media_items_response = media_items_request.json()

        media_items = media_items_response.get('mediaItems', [])
        if not media_items:
          print (media_items_request)

        print('Fetched {} album photos for album {}'.format(len(media_items), album['title']))

        album_photos += media_items

        next_page_token = media_items_response.get('nextPageToken', None)

    print('Totally fetched {} album photos'.format(len(album_photos)))
    pickle.dump( album_photos, open( 'album_photos.pickle', "wb" ) )

  all_photos_ids = {photo['id'] for photo in all_photos}

  album_photos_ids = {photo['id'] for photo in album_photos}

  print(len(all_photos_ids))
  print(len(album_photos_ids))

  photos_without_album_ids = all_photos_ids - album_photos_ids

  print(len(photos_without_album_ids))

  all_photos_mapping = {photo['id']:photo for photo in all_photos}

  photos_by_year = collections.defaultdict(list)
  for photo_id in photos_without_album_ids:
    photo = all_photos_mapping[photo_id]
    # creationTime = datetime.datetime.strptime(photo['mediaMetadata']['creationTime'], '%Y-%m-%dT%H:%M:%S%z')
    # photo['creationTime'] = creationTime
    creation_year = photo['mediaMetadata']['creationTime'][:4]
    photos_by_year[creation_year].append(photo)

  with open('stats.txt', "w") as stats:
    with open('photos_without_albums.html', "w") as file:
      for year, photos in sorted(photos_by_year.items()):
        stats.write('{}: {}\n'.format(year, len(photos)))
        file.write('<h1>{}</h1>'.format(year))
        file.write('<p>Total: {} photos.</p>'.format(len(photos)))
        for i, photo in enumerate(photos):
          file.write('{}. <a href="{}">{}</a><br>\n'.format(i+1, photo['productUrl'], photo['filename']))

  with open('videos.html', "w") as file:
    for photo in all_photos:
      filename, file_extension = os.path.splitext(photo['filename'])
      if file_extension.lower() == '.jpg' or file_extension.lower() == '.jpeg' or file_extension.lower() == '.png' or file_extension.lower() == '.heic' or file_extension.lower() == '.dng':
        continue

      file.write('<a href="{}">{}</a><br>\n'.format(photo['productUrl'], photo['filename']))

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Find Google Photos that do not belong to any photo albums.')
  parser.add_argument('secret_file')
  args = parser.parse_args()
  main(args.secret_file)
